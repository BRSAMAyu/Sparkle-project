"""Web backend driver：真实 Chrome（headless）+ 原生 CDP（零第三方依赖）。

原理与边界：
- Sparkle Flutter Web 端在 main.dart 中常开语义树（`SemanticsBinding.instance.ensureSemantics()`，
  见 round1 web 走查 W-5/W-6），因此页面 DOM 中存在 `flt-semantics` 无障碍树，
  含 aria-label/role 与真实几何框；
- 元素定位走无障碍树（读屏软件看到什么，simulator 就看到什么）；
- 交互全部是真实输入事件：点击用 CDP Input.dispatchMouseEvent 落在语义节点几何中心，
  输入用 Input.insertText（经 Flutter web 文本输入通道），不直接改 Flutter 状态；
- 证据：每步 Page.captureScreenshot（引擎渲染帧），CDP Network 事件留存 api_log。
- simulator 不得绕过 UI：本 driver 不注入 Dart、不调内部 API 改状态；
  URL 直达仅用于 journey 显式声明的入口（等价于用户手输 URL）。
"""

from __future__ import annotations

import base64
import json
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any
from uuid import uuid4

import websocket

from ..evidence import EvidenceCollector
from .base import BaseDriver, StepFailure

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]

# 从语义树收集可交互/文本节点的 JS：一次性返回全部节点的 role/label/text/rect/value
_COLLECT_JS = """
(() => {
  const nodes = [];
  const all = document.querySelectorAll('flt-semantics');
  for (const el of all) {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 && r.height <= 0) continue;
    // 只有直接子代 input/textarea 才是真实文本框；容器节点的 input 嵌套在
    // 更深的语义子树里，用 :scope > 排除，否则容器会被误认成输入框。
    const input = el.querySelector(':scope > input, :scope > textarea');
    nodes.push({
      role: el.getAttribute('role') || '',
      label: el.getAttribute('aria-label') || '',
      text: (el.textContent || '').trim().slice(0, 200),
      value: input ? (input.value || '') : (el.getAttribute('aria-valuetext') || ''),
      tag: input ? 'direct-input' : el.tagName.toLowerCase(),
      x: Math.round(r.x + r.width / 2),
      y: Math.round(r.y + r.height / 2),
      w: Math.round(r.width),
      h: Math.round(r.height),
      checked: el.getAttribute('aria-checked') || '',
    });
  }
  return JSON.stringify(nodes);
})()
"""


class CdpClient:
    """极简 CDP 客户端（websocket-client 之上）。"""

    def __init__(self, ws_url: str, timeout: float = 30.0) -> None:
        self.ws = websocket.create_connection(ws_url, timeout=timeout, max_size=64 * 1024 * 1024)
        self._id = 0

    def cmd(self, method: str, params: dict[str, Any] | None = None, timeout: float = 30.0) -> dict[str, Any]:
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.ws.settimeout(max(0.5, deadline - time.time()))
            raw = self.ws.recv()
            if not raw:
                continue
            msg = json.loads(raw)
            if msg.get("id") == mid:
                if "error" in msg:
                    raise StepFailure(f"CDP {method} 错误: {msg['error']}")
                return msg.get("result") or {}
            # 其余是事件，交由 on_event 钩子（网络留存）
            evt = self.on_event
            if evt is not None:
                evt(msg)
        raise StepFailure(f"CDP {method} 超时（{timeout}s）")

    # 事件钩子：由 driver 注入用于网络留存
    on_event = None

    def close(self) -> None:
        try:
            self.ws.close()
        except Exception:
            pass


class WebDriver(BaseDriver):
    name = "web"

    def __init__(self, evidence: EvidenceCollector, config: dict[str, Any]) -> None:
        super().__init__(evidence, config)
        self.app_url: str = self.config.get("app_url", "http://127.0.0.1:8437/")
        self.headless: bool = bool(self.config.get("headless", True))
        self.width: int = int(self.config.get("viewport_width", 1280))
        self.height: int = int(self.config.get("viewport_height", 800))
        self.lang: str = self.config.get("lang", "en-US")
        # --lang 只改浏览器 UI 语言，不影响 navigator.languages（Flutter web 的
        # locale 解析来源）；--accept-lang 才能同时固定 Accept-Language 与 JS 可见
        # locale。否则 App 跟随宿主系统语言渲染（曾致 zh 界面对不上 en 步骤定义）。
        self.accept_lang: str = self.config.get("accept_lang", "en-US")
        self.cdp: CdpClient | None = None
        self.chrome_proc: subprocess.Popen | None = None
        self.debug_port: int = int(self.config.get("cdp_port") or 0)
        self._tmp_profile: Path | None = None
        self._shot_seq = 0

    # ---------- 生命周期 ----------
    def start(self) -> None:
        chrome = self.config.get("chrome_path")
        if not chrome:
            chrome = next((c for c in CHROME_CANDIDATES if Path(c).exists()), None)
        if not chrome:
            raise StepFailure("未找到 Chrome/Chromium 可执行文件，web backend 无法启动")
        if not self.debug_port:
            self.debug_port = _free_port()
        self._tmp_profile = Path(f"/tmp/sparkle-journey-chrome-{uuid4().hex[:8]}")
        self._tmp_profile.mkdir(parents=True, exist_ok=True)
        args = [
            chrome,
            f"--remote-debugging-port={self.debug_port}",
            # Chrome 111+ 默认拒绝带 Origin 头的 CDP WebSocket 握手
            "--remote-allow-origins=*",
            f"--user-data-dir={self._tmp_profile}",
            f"--window-size={self.width},{self.height}",
            f"--lang={self.lang}",
            f"--accept-lang={self.accept_lang}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-sync",
            "--mute-audio",
            "--hide-scrollbars",
            # headless 下 CanvasKit 需要 WebGL：允许 SwiftShader 软件渲染
            "--enable-unsafe-swiftshader",
        ]
        if self.headless:
            args.append("--headless=new")
        args.append("about:blank")
        self.chrome_proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        ws_url = self._wait_page_target()
        self.cdp = CdpClient(ws_url)
        self.cdp.on_event = self._on_cdp_event
        self.cdp.cmd("Page.enable")
        self.cdp.cmd("Network.enable")
        self.cdp.cmd("Runtime.enable")

    def _wait_page_target(self, timeout: float = 30.0) -> str:
        deadline = time.time() + timeout
        last_err = ""
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{self.debug_port}/json/list", timeout=2
                ) as resp:
                    targets = json.loads(resp.read())
                for t in targets:
                    if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                        return t["webSocketDebuggerUrl"]
                last_err = f"targets={targets!r}"
            except Exception as exc:  # chrome 未就绪
                last_err = str(exc)
            time.sleep(0.4)
        raise StepFailure(f"Chrome CDP 未就绪: {last_err}")

    def _on_cdp_event(self, msg: dict[str, Any]) -> None:
        method = msg.get("method")
        params = msg.get("params") or {}
        if method == "Network.requestWillBeSent":
            req = params.get("request") or {}
            self.evidence.log_api(
                "http_request",
                {
                    "via": "cdp",
                    "url": req.get("url"),
                    "method": req.get("method"),
                    "has_auth_header": bool((req.get("headers") or {}).get("Authorization")),
                },
            )
        elif method == "Network.responseReceived":
            resp = params.get("response") or {}
            self.evidence.log_api(
                "http_response",
                {"via": "cdp", "url": resp.get("url"), "status": resp.get("status")},
            )

    def finish(self) -> None:
        # HEAVY 纪律：收工必须关浏览器并清理临时 profile
        if self.cdp:
            self.cdp.close()
            self.cdp = None
        if self.chrome_proc:
            self.chrome_proc.terminate()
            try:
                self.chrome_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.chrome_proc.kill()
            self.chrome_proc = None
        if self._tmp_profile and self._tmp_profile.exists():
            subprocess.run(["rm", "-rf", str(self._tmp_profile)], check=False)

    # ---------- 基础原语 ----------
    def js(self, expr: str, timeout: float = 20.0) -> Any:
        assert self.cdp is not None
        result = self.cdp.cmd(
            "Runtime.evaluate",
            {"expression": expr, "returnByValue": True, "awaitPromise": True},
            timeout=timeout,
        )
        exc = result.get("exceptionDetails")
        if exc:
            raise StepFailure(f"JS 执行异常: {json.dumps(exc, ensure_ascii=False)[:400]}")
        return (result.get("result") or {}).get("value")

    def semantics_nodes(self) -> list[dict[str, Any]]:
        raw = self.js(_COLLECT_JS)
        return json.loads(raw) if raw else []

    def screenshot(self, name: str) -> str:
        assert self.cdp is not None
        self._shot_seq += 1
        safe = f"{self._shot_seq:02d}-{name}".replace("/", "_")
        result = self.cdp.cmd("Page.captureScreenshot", {"format": "png"}, timeout=20)
        data = base64.b64decode(result["data"])
        path = self.evidence.save_screenshot(f"{safe}.png", data)
        return str(path)

    def tap_xy(self, x: int, y: int) -> None:
        assert self.cdp is not None
        common = {"x": x, "y": y, "button": "left", "clickCount": 1}
        self.cdp.cmd("Input.dispatchMouseEvent", {**common, "type": "mousePressed"})
        self.cdp.cmd("Input.dispatchMouseEvent", {**common, "type": "mouseReleased"})

    def tap_semantics_node(self, node: dict[str, Any]) -> tuple[bool, str]:
        """激活语义节点：优先 semantics DOM click（读屏软件的激活路径），
        失败回落到坐标真实鼠标事件。

        2026-09-19 实测：Flutter web 部分按钮（如注册提交）对坐标合成鼠标
        事件只播音效不触发 onPressed，而语义节点 DOM click 稳定触发——这正是
        读屏用户使用的激活通道，属于真实 UI 交互，不绕过体验层。
        """
        x, y = node["x"], node["y"]
        click_js = (
            "(() => { const cx=%d, cy=%d;"
            " const els=document.querySelectorAll('flt-semantics');"
            " let best=null, bestD=1e9;"
            " for (const el of els) { const r=el.getBoundingClientRect();"
            " const d=Math.abs(r.x+r.width/2-cx)+Math.abs(r.y+r.height/2-cy);"
            " if (d<bestD) { bestD=d; best=el; } }"
            " if (best && bestD<24) { best.click(); return 'dom-click'; }"
            " return 'no-match'; })()" % (x, y)
        )
        result = self.js(click_js)
        if result == "dom-click":
            return True, "dom-click"
        self.tap_xy(x, y)
        return True, "mouse-event"

    def ensure_visible(self, node: dict[str, Any]) -> dict[str, Any]:
        """节点在视口外时滚动到可见（等价用户滚屏；不改任何应用状态）。

        语义树 rect 是视口相对坐标：视口外的控件（如登录页底部的注册入口）
        直接点其坐标会落在视口外无效位置。滚完后重取语义树拿新 rect。
        """
        x, y = node["x"], node["y"]
        if 0 <= x <= self.width and 0 <= y <= self.height:
            return node
        scroll_js = (
            "(() => { const cx=%d, cy=%d;"
            " const els=document.querySelectorAll('flt-semantics');"
            " for (const el of els) { const r=el.getBoundingClientRect();"
            " if (Math.abs(r.x+r.width/2-cx)<8 && Math.abs(r.y+r.height/2-cy)<8)"
            " { el.scrollIntoView({block:'center'}); return true; } }"
            " return false; })()" % (x, y)
        )
        self.js(scroll_js)
        time.sleep(0.8)
        return self._refind_node(node)

    def _refind_node(self, node: dict[str, Any]) -> dict[str, Any]:
        """滚动后按文本重找同一节点（语义树 rect 已随滚动刷新）。"""
        hay = f"{node['label']} {node['text']} {node['value']}"
        cur = self.semantics_nodes()
        cur.sort(key=lambda n: n["w"] * n["h"])
        for n in cur:
            if hay.strip().lower().startswith((n["label"] or "").strip().lower()[:20]) and n["label"]:
                return n
            if node["text"] and node["text"][:20].lower() in f"{n['label']} {n['text']}".lower():
                return n
        return node

    def current_url(self) -> str:
        return str(self.js("window.location.href") or "")

    # ---------- 查找辅助 ----------
    @staticmethod
    def _matches(node: dict[str, Any], text: str, roles: list[str] | None) -> bool:
        if roles and node["role"] not in roles:
            return False
        hay = f"{node['label']} {node['text']} {node['value']}".strip().lower()
        return text.lower() in hay

    _INTERACTIVE_ROLES = {"button", "checkbox", "radio", "tab", "switch", "menuitem", "link", "textbox", "searchbox"}

    def find_nodes(
        self,
        text: str,
        roles: list[str] | None = None,
        exact: bool = False,
    ) -> list[dict[str, Any]]:
        nodes = self.semantics_nodes()
        out = []
        for n in nodes:
            if exact:
                hit = text.lower() in {n["label"].strip().lower(), n["text"].strip().lower(), n["value"].strip().lower()}
                if roles and n["role"] not in roles:
                    hit = False
            else:
                hit = self._matches(n, text, roles)
            if hit:
                out.append(n)
        # 排序规则（触达真实控件的关键）：
        # 1) 可交互 role（button/checkbox…）优先——纯文本标题节点（如顶栏「注册」）
        #    面积更小但不可交互，绝不能抢在按钮前面；
        # 2) 面积升序——容器节点会聚合全部后代文本，必须选最小（叶子）节点。
        out.sort(key=lambda n: (0 if n["role"] in self._INTERACTIVE_ROLES else 1, n["w"] * n["h"]))
        return out

    def wait_for_text(self, text: str, timeout: float = 30.0, roles: list[str] | None = None) -> dict[str, Any]:
        deadline = time.time() + timeout
        last_seen = 0
        while time.time() < deadline:
            hits = self.find_nodes(text, roles=roles)
            if hits:
                return hits[0]
            last_seen = len(self.semantics_nodes())
            time.sleep(0.8)
        raise StepFailure(
            f"等待文本超时({timeout:.0f}s): {text!r} 未出现在语义树（当前节点数={last_seen}）"
        )

    def wait_nodes_ready(self, min_nodes: int = 5, timeout: float = 60.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if len(self.semantics_nodes()) >= min_nodes:
                    return
            except Exception:
                pass
            time.sleep(1.0)
        raise StepFailure(f"语义树未就绪（{timeout:.0f}s 内节点数未达到 {min_nodes}）")

    # ---------- step handlers ----------
    def do_open_app(self, wait_text: str = "", timeout: float = 90.0) -> tuple[bool, str, list[str]]:
        """打开 App 入口 URL（等价于用户打开网页），等待首帧语义树。"""
        assert self.cdp is not None
        self.cdp.cmd("Page.navigate", {"url": self.app_url}, timeout=timeout)
        self.wait_nodes_ready(min_nodes=3, timeout=timeout)
        if wait_text:
            self.wait_for_text(wait_text, timeout=timeout)
        shot = self.screenshot("open_app")
        return True, f"opened {self.current_url()}", [shot]

    def do_wait_text(self, text: str, timeout: float = 40.0, screenshot: str = "") -> tuple[bool, str, list[str]]:
        node = self.wait_for_text(text, timeout=timeout)
        shot = self.screenshot(screenshot or f"wait_{_slug(text)}")
        return True, f"找到 {text!r}（role={node['role']}, rect={node['x']},{node['y']}）", [shot]

    def do_assert_no_text(self, text: str) -> tuple[bool, str, list[str]]:
        hits = self.find_nodes(text)
        if hits:
            raise StepFailure(f"断言失败：不应出现但找到了 {text!r}（{len(hits)} 处）")
        return True, f"确认未出现 {text!r}", []

    def do_tap_text(
        self,
        text: str,
        roles: list[str] | None = None,
        exact: bool = False,
        timeout: float = 30.0,
        then_wait: str = "",
        screenshot: str = "",
    ) -> tuple[bool, str, list[str]]:
        """按语义树定位并真实点击；roles 默认任何可见节点。"""
        candidates = self.find_nodes(text, roles=roles, exact=exact)
        if not candidates:
            candidates = self.find_nodes(text, roles=None, exact=exact)
        if not candidates:
            raise StepFailure(f"tap_text: 语义树中找不到 {text!r}（roles={roles}）")
        node = self.ensure_visible(candidates[0])
        _activated, how = self.tap_semantics_node(node)
        detail = f"点击 {text!r} @({node['x']},{node['y']}) role={node['role']} via={how}"
        artifacts = []
        if then_wait:
            w = self.wait_for_text(then_wait, timeout=timeout)
            detail += f" -> 出现 {then_wait!r} @({w['x']},{w['y']})"
        if screenshot:
            artifacts.append(self.screenshot(screenshot))
        return True, detail, artifacts

    def do_type_into(
        self,
        field_hint: str,
        text: str,
        timeout: float = 30.0,
        screenshot: str = "",
        verify_contains: str | None = None,
    ) -> tuple[bool, str, list[str]]:
        """点击聚焦语义文本框并输入（真实输入通道），输入后回读校验。

        verify_contains=None（默认）=> 校验回读含 text 前缀；
        verify_contains="" => 跳过回读校验（密码掩码等场景）；
        verify_contains="xx" => 校验回读含 xx。
        """
        deadline = time.time() + timeout
        typed = False
        last_err = ""
        while time.time() < deadline and not typed:
            # 只认直接持有 <input>/<textarea> 的语义节点（direct-input）；
            # 容器节点内嵌的输入框属于其语义子树，不算独立输入框。
            fields = [
                n for n in self.semantics_nodes()
                if n["tag"] == "direct-input" or n["role"] in ("textbox", "searchbox")
            ]
            target = None
            for n in fields:
                hay = f"{n['label']} {n['text']} {n['value']}".lower()
                if field_hint.lower() in hay:
                    target = n
                    break
            if target is None and len(fields) == 1:
                target = fields[0]  # 页面只有一个输入框时按唯一性定位
            if target is None:
                last_err = f"找不到输入框（hint={field_hint!r}, 现有输入框={len(fields)}）"
                time.sleep(0.8)
                continue
            target = self.ensure_visible(target)
            self.tap_xy(target["x"], target["y"])
            time.sleep(0.5)
            self.cdp.cmd("Input.insertText", {"text": text}, timeout=10)
            time.sleep(0.6)
            # 回读：语义树 input value；verify_contains 为空串 => 跳过回读校验
            # （密码掩码/语义暴露差异场景使用）
            need = text if verify_contains is None else verify_contains
            typed = False
            detail = ""
            if need == "":
                typed = True
                detail = f"输入 {field_hint!r}（跳过回读校验）"
            else:
                after = [
                    n for n in self.semantics_nodes()
                    if n["tag"] == "direct-input"
                ]
                got = ""
                for n in after:
                    if abs(n["x"] - target["x"]) < 8 and abs(n["y"] - target["y"]) < 40:
                        got = n["value"]
                if need[:12].lower() in got.lower():
                    typed = True
                    detail = f"输入 {field_hint!r} OK（value[:24]={got[:24]!r}）"
                else:
                    last_err = f"输入回读不符: 期望含 {need[:12]!r}, 实际 {got[:40]!r}"
                    time.sleep(0.5)
        if not typed:
            raise StepFailure(f"type_into 失败: {last_err}")
        artifacts = [self.screenshot(screenshot)] if screenshot else []
        return True, detail, artifacts

    def do_type_into_nth(
        self,
        index: int,
        text: str,
        timeout: float = 30.0,
        screenshot: str = "",
        verify_contains: str | None = None,
    ) -> tuple[bool, str, list[str]]:
        """按视觉顺序（自上而下）把文本输入第 index 个输入框（0 基）。

        用于占位符/label 未暴露到语义树的表单（如注册页）：等价用户按
        屏幕顺序点第 N 个框输入，不依赖任何内部状态。
        """
        deadline = time.time() + timeout
        typed = False
        last_err = ""
        detail = ""
        while time.time() < deadline and not typed:
            fields = sorted(
                (n for n in self.semantics_nodes() if n["tag"] == "direct-input"),
                key=lambda n: (n["y"], n["x"]),
            )
            if len(fields) <= index:
                last_err = f"输入框不足：需要第 {index + 1} 个，实际 {len(fields)} 个"
                time.sleep(0.8)
                continue
            target = self.ensure_visible(fields[index])
            self.tap_xy(target["x"], target["y"])
            time.sleep(0.5)
            self.cdp.cmd("Input.insertText", {"text": text}, timeout=10)
            time.sleep(0.6)
            need = text if verify_contains is None else verify_contains
            if need == "":
                typed = True
                detail = f"输入第 {index} 框（跳过回读校验）"
            else:
                got = ""
                for n in self.semantics_nodes():
                    if n["tag"] == "direct-input" and abs(n["x"] - target["x"]) < 8 and abs(n["y"] - target["y"]) < 40:
                        got = n["value"]
                if need[:12].lower() in got.lower():
                    typed = True
                    detail = f"输入第 {index} 框 OK（value[:24]={got[:24]!r}）"
                else:
                    last_err = f"第 {index} 框回读不符: 期望含 {need[:12]!r}, 实际 {got[:40]!r}"
                    time.sleep(0.5)
        if not typed:
            raise StepFailure(f"type_into_nth 失败: {last_err}")
        artifacts = [self.screenshot(screenshot)] if screenshot else []
        return True, detail, artifacts

    def do_note_account(self, username: str = "", email: str = "") -> tuple[bool, str, list[str]]:
        """把本次 journey 注册的账号记入运行期上下文，供 journey 级 DB 断言渲染。"""
        acc = self.state.setdefault("accounts", {}).setdefault("default", {})
        if username:
            acc["username"] = username
        if email:
            acc["email"] = email
        return True, f"记录账号 username={username!r} email={email!r}", []

    def do_assert_url_contains(self, fragment: str) -> tuple[bool, str, list[str]]:
        url = self.current_url()
        if fragment.lower() not in url.lower():
            raise StepFailure(f"断言失败：当前 URL {url!r} 不含 {fragment!r}")
        return True, f"URL 含 {fragment!r}: {url}", []

    def do_screenshot(self, name: str) -> tuple[bool, str, list[str]]:
        path = self.screenshot(name)
        return True, f"截图 {path}", [path]

    def do_sleep(self, seconds: float = 1.0) -> tuple[bool, str, list[str]]:
        time.sleep(float(seconds))
        return True, f"等待 {seconds}s", []


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _slug(text: str) -> str:
    keep = [c if c.isalnum() else "_" for c in text[:24]]
    return "".join(keep) or "step"
