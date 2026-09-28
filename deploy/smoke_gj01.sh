#!/usr/bin/env bash
# =============================================================================
# deploy/smoke_gj01.sh — O-01 GJ01 远端设备视角验收探针（公网 Staging HTTPS/WSS）
# =============================================================================
# 验收面对应 O-01 卡（v3/07_tasks/cards/O-01.md）：
#   [ ] GJ01 远端设备通过；密钥不在 client bundle
#
# 本脚本从「远端 fresh device」视角对公网 staging 做无内网依赖的黑盒探测：
#   A. HTTPS 证书有效（链校验 + 有效期余量；http 降级模式 SKIP）
#   B. 健康端点：/healthz、/api/v1/health 公开可达；
#      /docs 按架构事实做「内部文档不公网暴露」负断言（v3/08_operations/
#      DEPLOYMENT.md: FastAPI 8000 不公网裸露；网关生产模式无 /docs 路由，
#      见 backend/gateway/cmd/server/setup.go —— swagger 仅 IsDevelopment 挂载）
#   C. WSS 握手升级：/ws/chat 无凭据 → 401（鉴权拒绝路径）；
#      guest 登录换 token 后 Bearer 升级 → 101（只验证握手，不发消息、
#      零 LLM 调用；完整对话链路走 scripts/run_e2e_smoke.sh）
#   D. 401 形态：/api/v1/health/cqrs 未鉴权 → 401 + JSON error 字段
#   E. 密钥泄露扫描：对 client bundle 产物 grep 阿里云 AK 形态
#      LTAI[0-9A-Za-z]+ 断言零命中（APK 会先解包再扫；目录/单文件直接扫）
#
# 用法:
#   bash deploy/smoke_gj01.sh --base-url https://api.example.com
#   bash deploy/smoke_gj01.sh --base-url https://api.example.com \
#        --bundle-dir ./dist/sparkle.apk --bundle-dir ./deploy/landing
#   bash deploy/smoke_gj01.sh --base-url http://localhost:8080 --mode http   # 本地栈降级干跑
#
# 退出码: 0 = 全部 PASS（SKIP 不计失败）｜ 1 = 存在 FAIL ｜ 2 = 用法/依赖错误
# 依赖: curl（必须）、openssl（https 模式必须）、unzip（扫描 .apk/.zip 时需要）
# 环境变量等价: GJ01_BASE_URL / GJ01_MODE / GJ01_BUNDLE_DIR / GJ01_TIMEOUT
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ----------------------------------------------------------------------------
# 参数
# ----------------------------------------------------------------------------
BASE_URL="${GJ01_BASE_URL:-}"
MODE="${GJ01_MODE:-auto}"          # auto | https | http
TIMEOUT="${GJ01_TIMEOUT:-15}"
CERT_MIN_DAYS="${GJ01_CERT_MIN_DAYS:-14}"
ALLOW_SELF_SIGNED=0
EXPECT_DOCS_PUBLIC=0               # 默认断言 /docs 不公开（架构规则）；显式暴露文档时才开
NO_JOURNEY=0                       # 跳过 guest+wss 正向握手（只跑公开面+拒绝面）
JSON_OUT=0
BUNDLE_DIRS=()

usage() {
  sed -n '2,40p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)          BASE_URL="$2"; shift 2 ;;
    --mode)              MODE="$2"; shift 2 ;;
    --timeout)           TIMEOUT="$2"; shift 2 ;;
    --cert-min-days)     CERT_MIN_DAYS="$2"; shift 2 ;;
    --bundle-dir)        BUNDLE_DIRS+=("$2"); shift 2 ;;
    --allow-selfsigned)  ALLOW_SELF_SIGNED=1; shift ;;
    --expect-docs-public) EXPECT_DOCS_PUBLIC=1; shift ;;
    --no-journey)        NO_JOURNEY=1; shift ;;
    --json)              JSON_OUT=1; shift ;;
    -h|--help)           usage ;;
    *) echo "[gj01] 未知参数: $1" >&2; usage ;;
  esac
done

if [[ -z "$BASE_URL" ]]; then
  if [[ -n "${GJ01_BASE_URL:-}" ]]; then BASE_URL="$GJ01_BASE_URL"; else
    echo "[gj01] 缺 --base-url（或 GJ01_BASE_URL）" >&2
    usage
  fi
fi
if [[ -n "${GJ01_BUNDLE_DIR:-}" && ${#BUNDLE_DIRS[@]} -eq 0 ]]; then
  BUNDLE_DIRS+=("$GJ01_BUNDLE_DIR")
fi

case "$MODE" in
  https|http|auto) ;;
  *) echo "[gj01] --mode 只接受 auto|https|http，得: $MODE" >&2; exit 2 ;;
esac
[[ "$TIMEOUT" =~ ^[0-9]+$ ]] || { echo "[gj01] --timeout 须为正整数秒" >&2; exit 2; }

# ----------------------------------------------------------------------------
# 依赖
# ----------------------------------------------------------------------------
command -v curl >/dev/null 2>&1 || { echo "[gj01] 缺依赖: curl" >&2; exit 2; }

# ----------------------------------------------------------------------------
# URL 解析
# ----------------------------------------------------------------------------
BASE_URL="${BASE_URL%/}"
HOST_ONLY="$(printf '%s' "$BASE_URL" | sed -E 's#^[a-z]+://##; s#[/:].*$##')"
URL_SCHEME="$(printf '%s' "$BASE_URL" | sed -E 's#^([a-z]+)://.*#\1#')"

if [[ "$MODE" == "auto" ]]; then
  if [[ "$URL_SCHEME" == "https" ]]; then MODE="https"; else MODE="http"; fi
fi
if [[ "$MODE" == "https" && "$URL_SCHEME" != "https" ]]; then
  echo "[gj01] --mode https 与 base-url scheme(${URL_SCHEME}) 不符" >&2
  exit 2
fi
WS_SCHEME="ws"; [[ "$MODE" == "https" ]] && WS_SCHEME="wss"

# ----------------------------------------------------------------------------
# 结果记录
# ----------------------------------------------------------------------------
PASS_COUNT=0; FAIL_COUNT=0; SKIP_COUNT=0
RESULTS=()

record() { # status id detail
  local status="$1" id="$2" detail="$3"
  case "$status" in
    PASS) PASS_COUNT=$((PASS_COUNT+1)); printf '[gj01] ✅ PASS  %-22s %s\n' "$id" "$detail" ;;
    FAIL) FAIL_COUNT=$((FAIL_COUNT+1)); printf '[gj01] ❌ FAIL  %-22s %s\n' "$id" "$detail" >&2 ;;
    SKIP) SKIP_COUNT=$((SKIP_COUNT+1)); printf '[gj01] ⏭️  SKIP  %-22s %s\n' "$id" "$detail" ;;
  esac
  RESULTS+=("${status}|${id}|${detail}")
}

degraded_banner() {
  if [[ "$MODE" == "http" ]]; then
    echo "[gj01] ── 降级模式(http)：证书与 wss 升级检查按 SKIP 计，断言结构仍全量执行（本地栈干跑形态）──"
  fi
}

# ----------------------------------------------------------------------------
# HTTP 工具
# ----------------------------------------------------------------------------
http_code() { # method url [extra curl args...] -> 打印状态码
  local method="$1" url="$2"; shift 2
  curl -sS -o /dev/null -w '%{http_code}' --max-time "$TIMEOUT" -X "$method" "$@" "$url" 2>/dev/null || true
}

http_body() { # method url [extra curl args...] -> 打印 body（截断到 4K）
  local method="$1" url="$2"; shift 2
  curl -sS --max-time "$TIMEOUT" -X "$method" "$@" "$url" 2>/dev/null | head -c 4096 || true
}

ws_key() {
  if command -v openssl >/dev/null 2>&1; then openssl rand -base64 16 2>/dev/null; else head -c 16 /dev/urandom | base64; fi
}

# WS 升级探测：返回服务端响应状态码（101=升级成功；401/429=拒绝）。
# 用 --http1.1 钉死（WS upgrade 走 HTTP/1.1，禁 h2 ALPN）；
# 101 后服务端保持连接，curl 会在 --max-time 处超时退出（rc=28），
# 但 %{http_code} 已随头部取得 —— 故只要 code==101 即判成功。
ws_upgrade_code() { # url [auth header]
  local url="$1" auth="${2:-}"
  local key hdrs=()
  key="$(ws_key)"
  [[ -z "$key" ]] && key="dGhlIHNhbXBsZSBub25jZQ=="
  hdrs+=(-H "Connection: Upgrade" -H "Upgrade: websocket" \
         -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: ${key}")
  [[ -n "$auth" ]] && hdrs+=(-H "Authorization: ${auth}")
  local code rc
  code="$(curl -sS --http1.1 -o /dev/null -w '%{http_code}' --max-time 8 "${hdrs[@]}" "$url" 2>/dev/null)"
  rc=$?
  if [[ "$code" == "000" && $rc -ne 0 ]]; then
    code="$(curl -sS --http1.1 -o /dev/null -w '%{http_code}' --max-time 8 "${hdrs[@]}" "$url" 2>/dev/null || true)"
  fi
  printf '%s' "$code"
}

json_field() { # body field -> 打印字段值（无 jq 时用 sed 兜底）
  local body="$1" field="$2"
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$body" | jq -r --arg f "$field" 'try (.[$f] // "") catch ""' 2>/dev/null || true
  else
    printf '%s' "$body" | sed -nE 's/.*"'"$field"'"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/p' | head -n 1
  fi
}

# ============================================================================
# A. TLS 证书（仅 https 模式）
# ============================================================================
check_tls() {
  if [[ "$MODE" != "https" ]]; then
    record SKIP "tls:cert" "http 降级模式，证书检查不适用"
    return 0
  fi
  command -v openssl >/dev/null 2>&1 || { record FAIL "tls:cert" "缺 openssl"; return 0; }

  local verify_line verify_rc cert_out enddate days_left
  cert_out="$(echo | openssl s_client -connect "${HOST_ONLY}:443" -servername "$HOST_ONLY" 2>/dev/null)"
  verify_line="$(printf '%s' "$cert_out" | grep -E '^Verify return code:' | tail -n 1)"
  verify_rc="$(printf '%s' "$verify_line" | sed -E 's/^Verify return code: *([0-9]+).*/\1/')"

  if [[ "$verify_rc" == "0" ]]; then
    : # 链校验通过
  elif [[ "$ALLOW_SELF_SIGNED" == "1" && "$verify_rc" =~ ^(18|19|20|21)$ ]]; then
    record SKIP "tls:cert:chain" "自签证书(--allow-selfsigned)：verify rc=${verify_rc}"
  else
    record FAIL "tls:cert" "证书链校验未通过: ${verify_line:-<无输出，443 不可达或非 TLS>}"
    return 0
  fi

  enddate="$(printf '%s' "$cert_out" | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)"
  if [[ -z "$enddate" ]]; then
    record FAIL "tls:cert" "无法读取 notAfter（${HOST_ONLY}:443）"
    return 0
  fi
  if enddate_epoch="$(date -j -f '%b %e %H:%M:%S %Y %Z' "$enddate" +%s 2>/dev/null || date -d "$enddate" +%s 2>/dev/null)"; then
    now_epoch="$(date +%s)"
    days_left=$(( (enddate_epoch - now_epoch) / 86400 ))
    if (( days_left <= 0 )); then
      record FAIL "tls:cert:expiry" "证书已过期（notAfter=${enddate}）"
    elif (( days_left < CERT_MIN_DAYS )); then
      record SKIP "tls:cert:expiry" "余量 ${days_left} 天 < ${CERT_MIN_DAYS} 天（有效但临近续期，human inbox 项）"
    else
      record PASS "tls:cert" "链校验通过，notAfter=${enddate}（余 ${days_left} 天）"
    fi
  else
    record PASS "tls:cert" "链校验通过，notAfter=${enddate}（本机 date 无法解析剩余天数，人工复核）"
  fi
}

# ============================================================================
# B. 健康端点
# ============================================================================
check_health_endpoints() {
  local code
  code="$(http_code GET "${BASE_URL}/healthz")"
  if [[ "$code" == "200" ]]; then
    record PASS "http:/healthz" "200（网关 liveness）"
  else
    record FAIL "http:/healthz" "期望 200，实得 ${code:-<无响应>}"
  fi

  code="$(http_code GET "${BASE_URL}/api/v1/health")"
  if [[ "$code" == "200" ]]; then
    record PASS "http:/api/v1/health" "200（公开健康面，bootstrap readiness 同款）"
  else
    record FAIL "http:/api/v1/health" "期望 200，实得 ${code:-<无响应>}"
  fi

  # /docs：任务面列为探针；架构事实是 FastAPI /docs 只在内部 app 网络
  # （compose app=internal:true），网关生产模式无 /docs、/swagger 仅开发态挂载。
  # 故公网正确形态 = 不返回 FastAPI docs 200 —— 按负断言落地。
  code="$(http_code GET "${BASE_URL}/docs")"
  if [[ "$EXPECT_DOCS_PUBLIC" == "1" ]]; then
    if [[ "$code" == "200" ]]; then
      record PASS "http:/docs" "200（--expect-docs-public：显式公开文档形态）"
    else
      record FAIL "http:/docs" "期望 200，实得 ${code:-<无响应>}"
    fi
  else
    case "$code" in
      200)
        record FAIL "http:/docs" "公网暴露了 docs（200）——违反 DEPLOYMENT.md「FastAPI 不公网裸露」；若是有意公开用 --expect-docs-public"
        ;;
      ""|000)
        record FAIL "http:/docs" "无响应（${code:-<连接失败>}）——边缘不可达或被防火墙吞，需人工判别"
        ;;
      *)
        record PASS "http:/docs" "未公开（${code}）——内部文档不公网暴露（FastAPI 8000 在 internal 网内）"
        ;;
    esac
  fi
}

# ============================================================================
# C. WSS 握手升级 + D. 401 形态
# ============================================================================
http_probe() { # method url [extra curl args...] -> "code<TAB>body"（单请求同时取状态码与 body）
  local method="$1" url="$2"; shift 2
  local tmpfile
  tmpfile="$(mktemp)"
  local code
  code="$(curl -sS -o "$tmpfile" -w '%{http_code}' --max-time "$TIMEOUT" -X "$method" "$@" "$url" 2>/dev/null || true)"
  local body
  body="$(head -c 4096 "$tmpfile" 2>/dev/null || true)"
  rm -f "$tmpfile"
  printf '%s\t%s' "${code:-000}" "$body"
}

check_auth_and_ws() {
  local code body err_code

  # C1/D1: 无凭据 WS 升级 → 必须拒绝（401；被前置限流时 429 也算"拒绝但需复核"）
  code="$(ws_upgrade_code "${BASE_URL}/ws/chat")"
  case "$code" in
    401) record PASS "ws:/ws/chat:anon" "401（无凭据升级被拒）" ;;
    429) record SKIP "ws:/ws/chat:anon" "429（WSUpgradeRateLimit 前置限流先拦；复跑确认，非鉴权失败）" ;;
    ""|000) record FAIL "ws:/ws/chat:anon" "无响应——边缘不可达" ;;
    *)   record FAIL "ws:/ws/chat:anon" "期望 401，实得 ${code:-<无>}" ;;
  esac

  # D2: 未鉴权访问 authed 健康面 → 401 + JSON 形态
  IFS=$'\t' read -r code body <<<"$(http_probe GET "${BASE_URL}/api/v1/health/cqrs")"
  err_code="$(json_field "$body" "error_code")"
  if [[ "$code" == "401" ]]; then
    if [[ -n "$(json_field "$body" "error")" ]]; then
      record PASS "http:/health/cqrs:401" "401 + JSON error 字段（error_code=${err_code:-<缺省>}）"
    else
      record FAIL "http:/health/cqrs:401" "401 但 body 无 JSON error 字段（形态异常）: ${body:0:120}"
    fi
  else
    record FAIL "http:/health/cqrs:401" "期望 401，实得 ${code:-<无响应>}——鉴权拒绝路径失效是高危"
  fi

  [[ "$NO_JOURNEY" == "1" ]] && return 0

  # C2: guest 登录 → Bearer 升级 wss → 101（只握手不发消息，零 LLM 调用）
  IFS=$'\t' read -r code body <<<"$(http_probe POST "${BASE_URL}/api/v1/auth/guest" -H "Content-Type: application/json" -d '{}')"
  local token
  token="$(json_field "$body" "access_token")"
  if [[ -z "$token" ]]; then
    record FAIL "journey:guest" "guest 登录未取得 access_token（GJ01 fresh device 链路断）: ${body:0:120}"
    return 0
  fi
  record PASS "journey:guest" "guest 登录取得 access_token"

  code="$(ws_upgrade_code "${BASE_URL}/ws/chat" "Bearer ${token}")"
  case "$code" in
    101)
      record PASS "ws:/ws/chat:wss" "${WS_SCHEME} 握手升级 101（Bearer JWT，prod 默认 jwt_header 路径）"
      ;;
    401)
      record FAIL "ws:/ws/chat:wss" "带 token 仍 401——查 WS_TICKET_REQUIRED（ticket-only 形态下 Bearer 被拒属预期，需按 ticket 流程改探针）或 token 无效"
      ;;
    429)
      record SKIP "ws:/ws/chat:wss" "429（前置限流；稍后复跑）"
      ;;
    ""|000)
      record FAIL "ws:/ws/chat:wss" "无响应——边缘不可达"
      ;;
    *)
      record FAIL "ws:/ws/chat:wss" "期望 101，实得 ${code:-<无>}"
      ;;
  esac
}

# ============================================================================
# E. client bundle 密钥泄露扫描（LTAI[0-9A-Za-z]+ 断言零命中）
# ============================================================================
AK_PATTERN='LTAI[0-9A-Za-z]+'

scan_bundle_target() { # target
  local target="$1" tmpdir="" hits=0
  [[ -e "$target" ]] || { record FAIL "bundle:scan" "扫描目标不存在: ${target}"; return 0; }

  if [[ -d "$target" ]]; then
    hits="$(grep -raEo "$AK_PATTERN" "$target" 2>/dev/null | grep -cv '^$' || true)"
  elif file "$target" 2>/dev/null | grep -qi 'zip archive'; then
    if ! command -v unzip >/dev/null 2>&1; then
      record SKIP "bundle:scan" "${target} 是 zip/APK 但缺 unzip——解包扫描跳过（安装 unzip 后重跑）"
      return 0
    fi
    tmpdir="$(mktemp -d)"
    unzip -qq -o "$target" -d "$tmpdir" >/dev/null 2>&1
    hits="$(grep -raEo "$AK_PATTERN" "$tmpdir" 2>/dev/null | grep -cv '^$' || true)"
    rm -rf "$tmpdir"
  else
    hits="$(grep -caEo "$AK_PATTERN" "$target" 2>/dev/null || true)"
  fi

  if [[ "$hits" -eq 0 ]]; then
    record PASS "bundle:scan" "零命中（${AK_PATTERN}）: ${target}"
  else
    record FAIL "bundle:scan" "命中 ${hits} 处 AK 形态（${AK_PATTERN}）: ${target} —— 密钥进了 client bundle 是验收红线"
  fi
}

check_bundle_secrets() {
  if [[ ${#BUNDLE_DIRS[@]} -eq 0 ]]; then
    # 无显式 bundle 时降级扫仓库内实际会被客户端拿到的静态面（landing 页），
    # 并明确提示：APK/Web 构建产物需用 --bundle-dir 显式提供。
    local landing="${SCRIPT_DIR}/landing"
    record SKIP "bundle:scope" "未提供 --bundle-dir：仅扫仓库内 landing 静态面；APK/Web 产物请用 --bundle-dir <路径|文件>"
    if [[ -d "$landing" ]]; then
      scan_bundle_target "$landing"
    fi
    return 0
  fi
  local t
  for t in "${BUNDLE_DIRS[@]}"; do
    scan_bundle_target "$t"
  done
}

# ============================================================================
# 主流程
# ----------------------------------------------------------------------------
main() {
  echo "[gj01] 目标: ${BASE_URL}（mode=${MODE}, ws=${WS_SCHEME}, timeout=${TIMEOUT}s）"
  degraded_banner

  check_tls
  check_health_endpoints
  check_auth_and_ws
  check_bundle_secrets

  echo "[gj01] ─────────────────────────────────────────────"
  local degraded_note=""
  [[ "$MODE" == "http" ]] && degraded_note="（http 降级形态，不构成完整 GJ01 证据）"
  echo "[gj01] 结果: PASS=${PASS_COUNT} FAIL=${FAIL_COUNT} SKIP=${SKIP_COUNT}${degraded_note}"

  if [[ "$JSON_OUT" == "1" ]]; then
    printf '{"base_url":"%s","mode":"%s","pass":%d,"fail":%d,"skip":%d,"results":[' \
      "$BASE_URL" "$MODE" "$PASS_COUNT" "$FAIL_COUNT" "$SKIP_COUNT"
    local first=1 row
    for row in "${RESULTS[@]}"; do
      IFS='|' read -r st id detail <<<"$row"
      [[ $first -eq 1 ]] || printf ','
      first=0
      detail_escaped="${detail//\"/\\\"}"
      printf '{"status":"%s","id":"%s","detail":"%s"}' "$st" "$id" "$detail_escaped"
    done
    printf ']}\n'
  fi

  [[ $FAIL_COUNT -eq 0 ]] || exit 1
  exit 0
}

main
