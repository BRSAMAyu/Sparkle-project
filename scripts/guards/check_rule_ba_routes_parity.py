#!/usr/bin/env python3
"""Rule BA-ROUTES: gateway↔engine route parity (full-surface static diff).

Closes the P3 gateway sweep handoff #1 (docs/competition/2026-tmall-hackathon/
系统审查/round2/p3-sweep-gateway.md §6.1): compare the set of routes the gateway
proxies to the Python engine against the engine's actually-registered FastAPI
routes, entirely offline (no engine process, no OpenAPI fetch):

Engine side   — ast-parse backend/app: main.py app-level routes + include_router
                composition (api/v1/router.py prefixes, module APIRouter prefixes,
                experience/*_router.py dynamic mounts). Conditional mounts are
                resolved against config/settings.py defaults.
Gateway side  — parse proxy_routes.go + galaxy_handler.go proxy registrations
                (`h.proxyWithHeaders` / `h.ProxyToBackend`), registerREST groups,
                and the "Missing Proxy Routes" catch-all loop.

Comparison model:
  * Paths normalize: gin `:param` / FastAPI `{param[:conv]}` → `{}`; trailing "/".
  * `/*path` catch-alls count as prefix coverage, not concrete routes; a catch-all
    whose prefix has zero engine routes is itself drift (dead group).
  * Direction A: gateway proxies (METHOD, path) the engine does not serve → drift.
  * Direction B: engine serves (METHOD, path) the gateway neither registers nor
    catch-all covers → drift (the gateway NoRoute fallback only forwards public
    /api/v1/auth/* prefixes, so uncovered engine surfaces are unreachable).
  * Known diffs are挂账 in KNOWN_DIFFS below with a reason; anything outside the
    ledger fails with exit 1.

Known limitations (documented, fail-closed where possible):
  * Non-literal FastAPI route paths cannot be resolved statically → hard failure.
  * Engine `@router.websocket` routes (community ×2, stt ×1) are excluded: the
    gateway terminates them natively (HandleCommunityWS / HandlePersonalWS /
    /ws/stt), not via the REST proxy surface.
  * Method-agnostic ledger matching: a new engine METHOD on an already-ledgered
    path does not re-trip the guard; paths always do.

Evasion hatch: annotate an offending gateway registration with
`rule-ba: ignore <reason>` (mirrors Rule BM).
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "backend" / "app"
GATEWAY_HANDLER_DIR = REPO_ROOT / "backend" / "gateway" / "internal" / "handler"
GATEWAY_FILES = [
    GATEWAY_HANDLER_DIR / "proxy_routes.go",
    GATEWAY_HANDLER_DIR / "galaxy_handler.go",
]
PROXY_MARKERS = ("h.proxyWithHeaders", "h.ProxyToBackend")
GIN_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")

IGNORE_RE = re.compile(r"rule-ba:\s*ignore\s+.+", re.IGNORECASE)


# --------------------------------------------------------------------------
# Shared normalization
# --------------------------------------------------------------------------

def norm_path(p: str) -> str:
    """gin `:name` / FastAPI `{name[:conv]}` → `{}`; strip trailing slash."""
    p = re.sub(r"\{[^}]*\}", "{}", p)  # brace params first (engine `{id:uuid}`)
    p = re.sub(r":\w+", "{}", p)  # then gin params
    return p.rstrip("/") if len(p) > 1 else p


# --------------------------------------------------------------------------
# Engine side (FastAPI, static AST)
# --------------------------------------------------------------------------

def _router_prefixes(tree: ast.AST) -> dict[str, str]:
    """var name → prefix for `x = APIRouter(prefix="...")` assignments."""
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "APIRouter":
                prefix = ""
                for kw in call.keywords:
                    if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                        prefix = kw.value.value
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        out[t.id] = prefix
    return out


def _module_routes(path: Path) -> tuple[dict[str, str], list, list, list]:
    """Return (router prefixes, routes, include_router calls, unresolved paths).

    routes:   (router_var, METHOD, literal_path, lineno); METHOD "WS" for websocket.
    includes: (target_name, prefix, lineno)
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    prefixes = _router_prefixes(tree)
    routes, includes, unresolved = [], [], []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)):
                    continue
                method, recv = dec.func.attr, dec.func.value
                var = recv.id if isinstance(recv, ast.Name) else None
                if method in ("get", "post", "put", "patch", "delete", "head", "options"):
                    if not dec.args:
                        continue
                    if isinstance(dec.args[0], ast.Constant):
                        routes.append((var, method.upper(), dec.args[0].value, dec.lineno))
                    else:
                        unresolved.append(f"{path}: {dec.lineno}: non-literal {method} path")
                elif method == "api_route" and dec.args and isinstance(dec.args[0], ast.Constant):
                    methods = ["GET"]
                    for kw in dec.keywords:
                        if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                            methods = [e.value for e in kw.value.elts if isinstance(e, ast.Constant)]
                    for m in methods:
                        routes.append((var, str(m).upper(), dec.args[0].value, dec.lineno))
                elif method == "websocket" and dec.args and isinstance(dec.args[0], ast.Constant):
                    routes.append((var, "WS", dec.args[0].value, dec.lineno))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "include_router":
            tgt = node.args[0] if node.args else None
            tgt_name = None
            if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name):
                tgt_name = f"{tgt.value.id}.{tgt.attr}"
            elif isinstance(tgt, ast.Name):
                tgt_name = tgt.id
            prefix = ""
            for kw in node.keywords:
                if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                    prefix = kw.value.value
            includes.append((tgt_name, prefix, node.lineno))
    return prefixes, routes, includes, unresolved


def _settings_default(flag: str) -> bool | None:
    """Read a bool default from config/settings.py (None if absent)."""
    path = APP_DIR / "config" / "settings.py"
    m = re.search(rf"^\s*{flag}:\s*bool\s*=\s*(True|False)\s*$", path.read_text(encoding="utf-8"), re.M)
    return None if m is None else m.group(1) == "True"


def _module_file(mod: str) -> Path | None:
    """app.api.v1.xxx → backend/app/api/v1/xxx.py (or package __init__.py)."""
    rel = mod[len("app."):] if mod.startswith("app.") else mod
    base = APP_DIR / rel.replace(".", "/")
    for cand in (base.with_suffix(".py"), base / "__init__.py"):
        if cand.exists():
            return cand
    return None


def collect_engine_routes() -> tuple[dict[tuple[str, str], str], list[str]]:
    """Full engine surface as {(METHOD, norm path): source loc}; WS excluded."""
    problems: list[str] = []
    engine: dict[tuple[str, str], str] = {}

    def mount(path: Path, prefix: str, var_filter: str | None = None) -> None:
        prefixes, routes, _, unresolved = _module_routes(path)
        problems.extend(unresolved)
        rel = path.relative_to(REPO_ROOT)
        for var, method, lit, lineno in routes:
            if method == "WS" or (var_filter and var != var_filter):
                continue
            engine.setdefault(
                (method, norm_path(prefix + prefixes.get(var, "") + lit)),
                f"{rel}:{lineno}",
            )

    # api/v1/router.py — module composition + its own @api_router routes.
    router_py = APP_DIR / "api" / "v1" / "router.py"
    graphrag_on = _settings_default("ENABLE_GRAPHRAG_MONITOR_API")
    _, _, includes, unresolved = _module_routes(router_py)
    problems.extend(unresolved)
    mod_prefixes: dict[str, set[str]] = {}
    for target, prefix, lineno in includes:
        if not target or "." not in target:
            continue
        mod = target.split(".")[0]
        if not graphrag_on and mod in ("graph_monitor", "graphrag_trace"):
            continue  # mounted only under settings-gated include (default off)
        mod_prefixes.setdefault(mod, set()).add(prefix)
    mount(router_py, "/api/v1", var_filter="api_router")
    for mod, prefixes in sorted(mod_prefixes.items()):
        f = _module_file(f"app.api.v1.{mod}")
        if f is None:
            problems.append(f"router.py includes unresolvable module: app.api.v1.{mod}")
            continue
        for prefix in sorted(prefixes):
            mount(f, "/api/v1" + prefix)
    for f in sorted((APP_DIR / "api" / "v1" / "experience").glob("*_router.py")):
        mount(f, "/api/v1")  # dynamically loaded by _include_experience_routers()

    # main.py — app-level routes, probes, /api/internal, v2 agent (placeholder).
    main_py = APP_DIR / "main.py"
    agent_v2_on = _settings_default("ENABLE_AGENT_GRAPH_V2")
    prefixes, routes, main_includes, unresolved = _module_routes(main_py)
    problems.extend(unresolved)
    for var, method, lit, lineno in routes:
        if method == "WS":
            continue
        if var == "app":
            engine.setdefault((method, norm_path(lit)), f"backend/app/main.py:{lineno}")
        elif var == "placeholder_router":
            engine.setdefault(
                (method, norm_path("/api/v2/agent" + lit)), f"backend/app/main.py:{lineno}"
            )
    for target, prefix, _lineno in main_includes:
        if not target or target == "placeholder_router":
            continue
        if not agent_v2_on and target == "agent_graph_router":
            continue  # v2 agent graph disabled by default; placeholder above stands
        f = _module_file(target.split(".")[0]) if "." in target else _alias_module(main_py, target)
        if f is None:
            problems.append(f"main.py include unresolvable: {target}")
            continue
        mount(f, prefix)
    return engine, problems


def _alias_module(main_py: Path, alias: str) -> Path | None:
    """Resolve `from app.x.y import router as <alias>` to the module file."""
    for node in ast.walk(ast.parse(main_py.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            for a in node.names:
                if (a.asname or a.name) == alias:
                    return _module_file(node.module)
    return None


# --------------------------------------------------------------------------
# Gateway side (gin registrations in Go source)
# --------------------------------------------------------------------------

def _group_paths(text: str) -> dict[str, str]:
    """Resolve `x := <parent>.Group("/path")` chains to full group paths."""
    groups: dict[str, str] = {}
    pattern = re.compile(r'(\w+)\s*:?=\s*(\w+)\.Group\("([^"]*)"\)')
    for _ in range(4):  # fixpoint for chained groups
        grew = False
        for m in pattern.finditer(text):
            var, parent, frag = m.groups()
            if var in groups:
                continue
            if parent in ("api", "r"):
                groups[var] = frag
                grew = True
            elif parent in groups:
                groups[var] = groups[parent] + frag
                grew = True
        if not grew:
            break
    return groups


def _catchall_loop_prefixes(text: str) -> tuple[set[str], bool]:
    """Prefixes of the `for _, r := range []struct{prefix, name}{...}` loop."""
    m = re.search(
        r"\[\]struct \{\s*prefix string\s*name\s+string\s*\}\s*\{(.*?)\}\s*\{", text, re.S
    )
    if not m:
        return set(), False
    return set(re.findall(r'\{"([^"]+)",\s*"[^"]*"\}', m.group(1))), True


def collect_gateway_routes() -> tuple[set[tuple[str, str]], set[str], list[str]]:
    """Concrete proxied routes, catch-all prefixes, and parse problems."""
    problems: list[str] = []
    concrete: set[tuple[str, str]] = set()
    catchalls: set[str] = set()
    for path in GATEWAY_FILES:
        text = path.read_text(encoding="utf-8")
        groups = _group_paths(text)
        loop_prefixes, loop_found = _catchall_loop_prefixes(text)
        if "registerREST(rg," in text and not loop_found:
            problems.append(f"{path.name}: catch-all loop present but not parseable")
        for p in loop_prefixes:
            catchalls.add("/api/v1" + p + "/*path")
        for lineno, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            if IGNORE_RE.search(line):
                continue
            m = re.match(r'(\w+)\.(GET|POST|PUT|PATCH|DELETE|Any)\("([^"]*)",', line)
            if not m:
                continue
            grp, method, route = m.groups()
            if not any(marker in line for marker in PROXY_MARKERS):
                continue  # served locally (gRPC/CQRS) — not the proxy surface
            base = groups.get(grp)
            if base is None:
                if grp == "rg" and loop_found:
                    continue  # loop body registrations already expanded above
                problems.append(f"{path.name}:{lineno}: unresolvable group var {grp!r}")
                continue
            full = "/api/v1" + base + route
            if route.endswith("/*path"):
                catchalls.add(full)
                continue
            for meth in GIN_METHODS if method == "Any" else (method,):
                concrete.add((meth, full))
        for m in re.finditer(r'registerREST\((\w+),\s*"([^"]*)"\)', text):
            grp, route = m.groups()
            base = groups.get(grp)
            if base is None:
                if grp == "rg" and loop_found:
                    continue
                problems.append(f"{path.name}: registerREST on unresolvable group {grp!r}")
                continue
            full = "/api/v1" + base + route
            if route == "/*path":
                catchalls.add(full)
            else:
                for meth in GIN_METHODS:
                    concrete.add((meth, full))
    return concrete, catchalls, problems


# --------------------------------------------------------------------------
# Known-diff ledger (挂账) — exact normalized paths, method-agnostic.
# Each entry: normalized path → reason. Extend when a diff is consciously accepted.
# --------------------------------------------------------------------------

ENGINE_ONLY: dict[str, str] = {
    "/": "engine root index; gateway has no proxy and clients do not call it",
    "/health": "direct-engine simple health check (gateway /api/v1/health is local)",
    "/live": "k8s liveness probe, direct to engine",
    "/ready": "k8s readiness probe, direct to engine",
    "/api/v1": "engine api v1 root index (router.py api_root)",
    "/api/v2/agent/status": "agent graph v2 placeholder (ENABLE_AGENT_GRAPH_V2=false)",
    "/api/v1/auth/guest": "public auth — NoRoute fallback proxies auth prefixes",
    "/api/v1/auth/login": "public auth — NoRoute fallback",
    "/api/v1/auth/register": "public auth — NoRoute fallback",
    "/api/v1/auth/social-login": "public auth — NoRoute fallback",
    "/api/v1/auth/refresh": "public auth — NoRoute fallback",
    "/api/v1/auth/forgot-password": "public auth — NoRoute fallback",
    "/api/v1/auth/reset-password": "public auth — NoRoute fallback",
    "/api/v1/auth/send-verification": "public auth — NoRoute fallback",
    "/api/v1/auth/verify-email": "public auth — NoRoute fallback",
    "/api/v1/auth/logout": "privileged auth — NoRoute fallback (isPrivilegedNoRoutePath)",
    "/api/v1/auth/upgrade-guest": "privileged auth — NoRoute fallback",
    "/api/v1/auth/upgrade-guest/social": "auth adjacency — NoRoute auth family",
    "/api/v1/errors": "gateway serves /errors natively via gRPC ErrorBookHandler",
    "/api/v1/errors/{}": "gateway serves /errors natively via gRPC ErrorBookHandler",
    "/api/v1/errors/stats": "gateway serves /errors natively via gRPC ErrorBookHandler",
    "/api/v1/errors/today-review": "gateway serves /errors natively via gRPC ErrorBookHandler",
    "/api/v1/errors/{}/semantic": "gateway serves /errors natively via gRPC ErrorBookHandler",
    "/api/v1/errors/review-cards": "gateway serves /errors natively via gRPC ErrorBookHandler",
    "/api/v1/chat/sessions": "gateway serves chat history natively (ChatHistoryService)",
    "/api/v1/chat/history/{}": "gateway serves chat history natively (ChatHistoryService)",
    "/api/v1/files/process": "gateway serves /files natively (FileHandler + MinIO)",
    "/api/v1/files/{}/status": "gateway serves /files natively (FileHandler + MinIO)",
    "/api/v1/galaxy/graph": "GalaxyHandler serves locally (GetGraph gRPC)",
    "/api/v1/galaxy/node/{}": "GalaxyHandler serves locally (GetNodeDetailGPRC)",
    "/api/v1/galaxy/nodes/{}": "GalaxyHandler serves locally (GetNodeDetailGPRC)",
    "/api/v1/galaxy/stats": "GalaxyHandler serves locally (GetGalaxyStatsGPRC)",
    "/api/v1/galaxy/search": "GalaxyHandler serves locally (SearchNodesGPRC)",
    "/api/v1/galaxy/node/{}/spark": "GalaxyHandler serves locally (SparkNode CQRS)",
    "/api/v1/galaxy/nodes/{}/spark": "GalaxyHandler serves locally (SparkNode CQRS)",
    "/api/v1/galaxy/node/{}/mastery": "GalaxyHandler serves locally (UpdateMastery CQRS)",
    "/api/v1/galaxy/nodes/{}/mastery": "GalaxyHandler serves locally (UpdateMastery CQRS)",
    "/api/v1/galaxy/node/{}/update-mastery": "GalaxyHandler serves locally (UpdateMastery CQRS)",
    "/api/v1/galaxy/nodes/{}/update-mastery": "GalaxyHandler serves locally (UpdateMastery CQRS)",
    "/api/v1/galaxy/node/{}/documents": "GalaxyHandler dual registers node(s) proxy — engine single form",
    "/api/v1/galaxy/nodes/{}/documents": "GalaxyHandler dual registers node(s) proxy — engine single form",
    "/api/v1/galaxy/community/aggregate-errors": "galaxy long tail — unreachable via gateway (P3 handoff §6.2)",
    "/api/v1/galaxy/context-plan/timeline": "galaxy long tail — unreachable via gateway (P3 handoff §6.2)",
    "/api/v1/goals/arbitrate": "goals tail — unreachable via gateway (P3 handoff §6.2)",
    "/api/v1/goals/analyze-intent": "goal_intent — unreachable via gateway (P3 handoff §6.2)",
    "/api/v1/health/health": "engine-side double prefix /health/health (P3 §6.2 dedup pending)",
    "/api/v1/health/health/capacity": "engine-side double prefix /health/health (P3 §6.2 dedup pending)",
    "/api/v1/health/health/detailed": "engine-side double prefix /health/health (P3 §6.2 dedup pending)",
    "/api/v1/health/health/live": "engine-side double prefix /health/health (P3 §6.2 dedup pending)",
    "/api/v1/health/health/metrics": "engine-side double prefix /health/health (P3 §6.2 dedup pending)",
    "/api/v1/health/health/ready": "engine-side double prefix /health/health (P3 §6.2 dedup pending)",
    "/api/v1/health/health/user-alerts": "engine-side double prefix /health/health (P3 §6.2 dedup pending)",
    "/api/v1/health/health/user-capacity": "engine-side double prefix /health/health (P3 §6.2 dedup pending)",
    "/api/v1/health/health/prometheus/alerts": "engine-side double prefix /health/health (P3 §6.2 dedup pending)",
    "/api/v1/health/health/queue/status": "engine-side double prefix /health/health (P3 §6.2 dedup pending)",
    "/api/v1/achievements/achievements/{}": "engine-side double prefix (P3 §6.2 dedup pending)",
    "/api/v1/achievements/achievements/{}/pin": "engine-side double prefix (P3 §6.2 dedup pending)",
    "/api/v1/achievements/achievements/{}/share": "engine-side double prefix (P3 §6.2 dedup pending)",
    "/api/v1/achievements/events/process": "achievements tail — no gateway registration (P3 §6.2)",
    "/api/v1/exam-sprint/dashboard": "engine exam-sprint not registered in gateway (P3 §6.2)",
    "/api/v1/exam-sprint/sprint-summary": "engine exam-sprint not registered in gateway (P3 §6.2)",
    "/api/v1/exam-sprint/diagnose/generate": "engine exam-sprint not registered in gateway (P3 §6.2)",
    "/api/v1/exam-sprint/diagnose/grade": "engine exam-sprint not registered in gateway (P3 §6.2)",
    "/api/v1/marketplace/admin/packs": "marketplace admin face — engine-side (P3 §6.2)",
    "/api/v1/marketplace/admin/packs/{}/rollback": "marketplace admin face — engine-side (P3 §6.2)",
    "/api/v1/marketplace/admin/skills": "marketplace admin face — engine-side (P3 §6.2)",
    "/api/v1/marketplace/admin/skills/{}/rollback": "marketplace admin face — engine-side (P3 §6.2)",
    "/api/v1/seed-libraries/admin/{}/promote": "seed-libraries admin face — engine-side (P3 §6.2)",
    "/api/v1/seed-libraries/items/{}": "seed-libraries admin face — engine-side (P3 §6.2)",
    "/api/v1/seed-libraries/{}/rating": "seed-libraries tail — engine-side (P3 §6.2)",
    "/api/v1/seed-libraries/{}/subscription": "seed-libraries tail — engine-side (P3 §6.2)",
    "/api/v1/community/admin/reports": "community long tail (P3 §6.2)",
    "/api/v1/community/admin/reports/{}/resolve": "community long tail (P3 §6.2)",
    "/api/v1/community/aggregates": "community long tail (P3 §6.2)",
    "/api/v1/community/aggregates/analyze": "community long tail (P3 §6.2)",
    "/api/v1/community/aggregates/budget-ledger": "community long tail (P3 §6.2)",
    "/api/v1/community/aggregates/insights": "community long tail (P3 §6.2)",
    "/api/v1/community/goals/{}/similar-pursuers": "community long tail (P3 §6.2)",
    "/api/v1/community/groups/{}/galaxy": "community long tail (P3 §6.2)",
    "/api/v1/community/groups/{}/knowledge-base": "community long tail (P3 §6.2)",
    "/api/v1/community/groups/{}/knowledge-base/documents": "community long tail (P3 §6.2)",
    "/api/v1/community/groups/{}/moderation": "community long tail (P3 §6.2)",
    "/api/v1/community/groups/{}/files": "community long tail (P3 §6.2)",
    "/api/v1/community/groups/{}/files/{}/copy-to-library": "community long tail (P3 §6.2)",
    "/api/v1/community/recommended-resources": "community long tail (P3 §6.2)",
    "/api/v1/community/resources": "community long tail (P3 §6.2)",
    "/api/v1/community/strategy-outcomes": "community long tail (P3 §6.2)",
    "/api/v1/community/strategy-outcomes/{}": "community long tail (P3 §6.2)",
    "/api/v1/community/shared-resources/{}/flag-misleading": "community long tail (P3 §6.2)",
    "/api/v1/community/shared-resources/{}/reject": "community long tail (P3 §6.2)",
    "/api/v1/community/tasks/{}/complete": "community long tail (P3 §6.2)",
    "/api/v1/community/users/{}/share-file": "community long tail (P3 §6.2)",
    "/api/v1/ws/devices": "engine WS monitoring face — no gateway proxy (P3 §6.2)",
    "/api/v1/ws/devices/{}": "engine WS monitoring face — no gateway proxy (P3 §6.2)",
    "/api/v1/ws/devices/register": "engine WS monitoring face — no gateway proxy (P3 §6.2)",
    "/api/v1/ws/online/{}": "engine WS monitoring face — no gateway proxy (P3 §6.2)",
    "/api/v1/ws/ws/ack/{}": "engine WS monitoring face — no gateway proxy (P3 §6.2)",
    "/api/v1/push/interaction": "push interaction tail — no gateway registration",
    "/api/v1/calendar/{}/restore": "calendar tail — no gateway registration",
    "/api/v1/tasks/{}/subtasks": "subtasks mounted under /tasks on engine; gateway /tasks/:id/resources only",
    "/api/internal/auto-degrade/status": "FV-24 internal SLO API — internal network only, never proxied",
    "/api/internal/auto-degrade/webhook": "FV-24 internal SLO API — internal network only, never proxied",
    "/api/v1/background-tasks/stream/events": "SSE stream — engine-side, no gateway registration",
    "/api/v1/errors/{}/analyze": "gateway serves /errors natively via gRPC ErrorBookHandler",
    "/api/v1/errors/{}/review": "gateway serves /errors natively via gRPC ErrorBookHandler",
    "/api/v1/galaxy/documents/{}/nodes": "galaxy long tail — unreachable via gateway (P3 handoff §6.2)",
    "/api/v1/plans/{}/today": "method drift: engine serves GET /plans/{id}/today, gateway registers POST (BM-sweep candidate)",
}

GATEWAY_ONLY: dict[str, str] = {
    "/api/v1/executions": "bare group artifact — engine serves sub-paths only",
    "/api/v1/experiments": "bare group artifact — engine serves sub-paths only",
    "/api/v1/notification-center": "bare group artifact — engine serves sub-paths only",
    "/api/v1/notifications": "bare group artifact — engine serves sub-paths only",
    "/api/v1/subjects": "bare group artifact — engine serves sub-paths only",
    "/api/v1/visual-elements": "bare group artifact — engine serves sub-paths only",
    "/api/v1/goals/{}": "gateway GET /goals/:id — engine has no GET-by-id (candidate for BM-style sweep)",
    "/api/v1/plans/{}/today": "method drift: engine serves GET /plans/{id}/today, gateway POST /plans/:id/today proxies to 404 (BM-sweep candidate)",
}


def main() -> int:
    engine, problems = collect_engine_routes()
    concrete, catchalls, gw_problems = collect_gateway_routes()
    problems += gw_problems
    if problems:
        print("RULE BA-ROUTES FAILED: static parse incomplete (fail-closed)")
        for p in sorted(set(problems)):
            print(f"  - {p}")
        return 1

    gw_norm = {(m, norm_path(p)) for m, p in concrete}
    failures: list[str] = []

    # Direction A: gateway proxies something the engine does not serve.
    for method, path in sorted(gw_norm - set(engine)):
        if path in GATEWAY_ONLY:
            continue
        failures.append(f"gateway-only proxy route: {method} {path}")

    # Dead catch-all groups: wildcard prefix with zero engine routes beneath.
    for ca in sorted(catchalls):
        base = ca[: -len("/*path")]
        if not any(p == base or p.startswith(base + "/") for _, p in engine):
            failures.append(f"dead catch-all group: {base}/*path (no engine route beneath)")

    # Direction B: engine route the gateway neither registers nor catch-all covers.
    covered = set(gw_norm)
    for ca in catchalls:
        base = ca[: -len("/*path")]
        for _, p in engine:
            if p == base or p.startswith(base + "/"):
                covered.add(("*", p))
    for (method, path) in sorted(set(engine)):
        if ("*", path) in covered or (method, path) in gw_norm:
            continue
        if path in ENGINE_ONLY:
            continue
        failures.append(f"engine route not proxied by gateway: {method} {path} ({engine[(method, path)]})")

    if failures:
        print("RULE BA-ROUTES FAILED: gateway↔engine route parity drift")
        for f in failures:
            print(f"  - {f}")
        print(
            "fix: register/remove the gateway route, adjust the engine, or ledger "
            "the accepted diff in the guard's ENGINE_ONLY/GATEWAY_ONLY tables"
        )
        return 1
    print(
        f"RULE BA-ROUTES OK: {len(gw_norm)} gateway proxy routes ↔ {len(engine)} engine "
        f"routes, {len(catchalls)} catch-all groups, {len(ENGINE_ONLY) + len(GATEWAY_ONLY)} ledgered diffs"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
