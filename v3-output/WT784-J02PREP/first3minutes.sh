#!/usr/bin/env bash
# first3minutes.sh — J-02 simulator 证据驱动脚本（骨架）
#
# 预备卡 wt784 J-02PREP 产物：只保证语法与结构，**预制阶段绝不执行**。
# 门后（day7 终门 2026-09-28 08:00 之后）由持设备会话按 runbook.md 执行。
#
# 安全设计：DRYRUN 默认 1 —— 只打印将执行的步骤计划即退出（exit 0）。
# 真跑需显式：J02_DRYRUN=0 bash v3-output/WT784-J02PREP/first3minutes.sh --lane macos
#
# 前置（runbook §1）：
#   * gateway :8080 / engine :8000 healthy；docker sparkle_db/redis/minio up
#   * dart 驱动 mobile/integration_test/j02_fastpath_journey_test.dart
#     （当前不存在，执行会话按 runbook §3 编写；本脚本只引用不代写）
#   * worktree 一次性 setup：make proto-gen + macos xcconfig shims（runbook §1.2）
#
# 用法：bash first3minutes.sh --lane <macos|ios|android> [--pass <0..4|all>] [--skip-build]
set -euo pipefail

# ────────────────────────── 配置 ──────────────────────────
REPO="${REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
SIM_ROOT="$REPO/v3-output/WT784-J02-SIM"
RUN_ID="j02sim_lane_$(date '+%Y%m%d_%H%M%S')_$(printf '%04x' $((RANDOM * RANDOM % 65536)))"
EVID="$SIM_ROOT/evidence/$RUN_ID"
LANE="macos"
PASS="all"
SKIP_BUILD=0
J02_DRYRUN="${J02_DRYRUN:-1}"
DART_DRIVER="mobile/integration_test/j02_fastpath_journey_test.dart"
GATEWAY="http://localhost:8080"
ENGINE="http://localhost:8000"
DB_CONTAINER="sparkle_db"
DB_USER="postgres"
DB_NAME="sparkle"
BUDGET_MS=180000   # J-02 acceptance：fresh user ≤3min

log()  { echo "[$(date '+%H:%M:%S')] [j02sim] $*"; }
die()  { echo "[j02sim] FATAL: $*" >&2; exit 1; }
mark() { echo "J02_MARK $*"; }

# ────────────────────────── 参数 ──────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --lane)       LANE="$2"; shift 2 ;;
    --pass)       PASS="$2"; shift 2 ;;
    --skip-build) SKIP_BUILD=1; shift ;;
    *)            die "未知参数 $1（支持 --lane/--pass/--skip-build）" ;;
  esac
done

# ────────────────────────── DRYRUN 门 ──────────────────────────
if [[ "$J02_DRYRUN" == "1" ]]; then
  log "DRYRUN（默认安全模式）——以下为将执行的步骤计划，未触碰任何设备/栈："
  log "  run_id=$RUN_ID"
  log "  1 preflight        : curl $GATEWAY/health, $ENGINE/health, docker $DB_CONTAINER"
  log "  2 fresh_install    : lane=${LANE}（wipe 语义见 runbook §2.1）"
  log "  3 build_and_install: lane=$LANE, skip=$SKIP_BUILD"
  log "  4 run_journey      : flutter test -d <lane> $DART_DRIVER --dart-define=J02_PASS=$PASS"
  log "  5 db_probes        : psql 双 0 行探针（guest 种子隔离）"
  log "  6 verdict          : 秒表 ≤ ${BUDGET_MS}ms 判定 + manifest 落盘"
  log "真跑：J02_DRYRUN=0 bash $0 --lane $LANE --pass $PASS"
  exit 0
fi

# ────────────────────────── 1. preflight ──────────────────────────
preflight() {
  log "== preflight =="
  command -v flutter >/dev/null || die "flutter 不在 PATH"
  curl -s -o /dev/null --max-time 5 "$GATEWAY/health" || die "gateway :8080 不健康——先 make dev-up + make gateway-dev（runbook §1.2）"
  curl -s -o /dev/null --max-time 5 "$ENGINE/health" || die "engine :8000 不健康——先 make grpc-server"
  docker inspect "$DB_CONTAINER" >/dev/null 2>&1 || die "$DB_CONTAINER 容器不在运行——先 make dev-up"
  git -C "$REPO" rev-parse HEAD > "$EVID/../.head_probe" 2>/dev/null || true
  log "preflight OK"
}

# ────────────────────────── 2. fresh install（按通道） ──────────────────────────
# 语义权威：runbook §2.1。所有 wipe 只触碰本 run 新建的账号与本地 app 态。
fresh_install_macos() {
  # macOS 通道的 wipe 内建于 dart 驱动进程起点（secure storage + prefs clear，
  # first3_measurement_test.dart wipeLocalState() 同款）——此处仅记录语义。
  echo '{"fresh_install":"dart-driver wipeLocalState (per-process cold start)"}' >> "$EVID/run_manifest.jsonl"
  log "macOS：fresh install = 每 pass 独立进程 + 驱动内 wipe（无需外部操作）"
}

fresh_install_ios() {
  command -v xcrun >/dev/null || die "xcrun 不在 PATH（需 Xcode）"
  local udid bundle
  udid="$(xcrun simctl list devices booted -j | python3 -c '
import sys, json
d = json.load(sys.stdin)
for runtime, devs in d.get("devices", {}).items():
    for dev in devs:
        if dev.get("state") == "Booted":
            print(dev["udid"]); sys.exit(0)
print("")')" || true
  [[ -n "$udid" ]] || die "无已启动 iOS 模拟器——先 bash scripts/mobile/ios_boot.sh"
  # bundle id 从构建产物 Info.plist 读取，不猜（runbook §2.1）
  local app="$REPO/mobile/build/ios/iphonesimulator/Runner.app"
  [[ -d "$app" ]] || die "iOS app 未构建（先 flutter build ios --simulator）"
  bundle="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$app/Info.plist")"
  log "simctl uninstall $udid ${bundle}（fresh install）"
  xcrun simctl uninstall "$udid" "$bundle"
  echo "{\"fresh_install\":\"simctl uninstall $bundle\",\"udid\":\"$udid\"}" >> "$EVID/run_manifest.jsonl"
}

fresh_install_android() {
  command -v adb >/dev/null || die "adb 不在 PATH"
  local apk pkg
  apk="$(ls "$REPO"/mobile/build/app/outputs/flutter-apk/app-release.apk 2>/dev/null || true)"
  [[ -n "$apk" ]] || die "APK 未构建"
  # B-03 教训：包名从 APK 本体解析，不猜（gradle 默认 com.example.sparkle，实跑曾见 com.sparkle.app）
  pkg="$($ANDROID_HOME/build-tools/*/aapt2 dump badging "$apk" 2>/dev/null | head -1 | sed -E 's/.*package=.name=.([^.]+.[^.]+.[^.]+).*/\1/' || true)"
  [[ -n "$pkg" ]] || die "aapt2 解析包名失败——确认 ANDROID_HOME/build-tools"
  log "adb uninstall ${pkg}（fresh install）"
  adb uninstall "$pkg" || true
  echo "{\"fresh_install\":\"adb uninstall $pkg\"}" >> "$EVID/run_manifest.jsonl"
}

fresh_install() {
  log "== fresh install（lane=${LANE}）=="
  case "$LANE" in
    macos)   fresh_install_macos ;;
    ios)     fresh_install_ios ;;
    android) fresh_install_android ;;
    *)       die "未知 lane：$LANE" ;;
  esac
}

# ────────────────────────── 3. build & install（占位形制） ──────────────────────────
build_and_install() {
  log "== build & install（lane=${LANE}, skip=${SKIP_BUILD}）=="
  [[ "$SKIP_BUILD" == "1" ]] && { log "跳过构建"; return 0; }
  case "$LANE" in
    macos)
      # macOS 通道无独立构建步：flutter test -d macos 直接编译运行（J-01 同法）。
      # 一次性 xcconfig shims 若缺，按 runbook §1.2 补（gitignored，不入 patch）。
      log "macOS：无独立构建步"
      ;;
    ios)
      # TODO(门后执行)：flutter build ios --simulator && bash scripts/mobile/ios_boot.sh && bash scripts/mobile/ios_install.sh
      # 构建命令真实可用（scripts/mobile 三件套已入库），设备交互的 UI 步进依赖同一份 dart 驱动 + -d <UDID>。
      die "iOS 通道构建/安装为占位——执行会话按 runbook §2.2 补齐后放行"
      ;;
    android)
      # TODO(门后执行)：flutter build apk && adb install -r；boot 见 scripts/mobile/android_boot.sh
      die "Android 通道构建/安装为占位——执行会话按 runbook §2.2 补齐后放行"
      ;;
  esac
}

# ────────────────────────── 4. 旅程驱动 ──────────────────────────
run_journey() {
  log "== run journey（driver=$DART_DRIVER, pass=${PASS}）=="
  [[ -f "$REPO/$DART_DRIVER" ]] || die "dart 驱动不存在：$DART_DRIVER
执行会话第一步：按 runbook §3 编写（J-01 first3_measurement_test.dart 同构：
textAny/waitUntil/safeSettle/shot 辅助直搬，J01_MARK→J02_MARK，产品代码零改动）"
  local dest="$EVID/screenshots"
  mkdir -p "$dest" "$EVID/logs"
  local target
  case "$LANE" in
    macos)   target="macos" ;;
    ios)     target="$(xcrun simctl list devices booted -j | python3 -c '
import sys, json
d = json.load(sys.stdin)
for runtime, devs in d.get("devices", {}).items():
    for dev in devs:
        if dev.get("state") == "Booted":
            print(dev["udid"]); sys.exit(0)')" ;;
    android) target="emulator-5554" ;;   # manifest 记实况 serial（B-03 教训），多设备时执行者改
  esac
  # 逐步骤语义/预期画面/截图时点：runbook §3 三表（R0-R9 / G1-G4 / U1-U3）。
  ( cd "$REPO/mobile" && flutter test integration_test/"$(basename "$DART_DRIVER")" -d "$target" \
      --dart-define=J02_PASS="$PASS" \
      --dart-define=J02_SHOT_DEST="$dest" \
      --reporter expanded 2>&1 | tee "$EVID/logs/run_$LANE.log" )
  grep -c 'J02_MARK' "$EVID/logs/run_$LANE.log" >/dev/null || die "日志无 J02_MARK 打点——驱动未按 runbook §4 打点"
  log "旅程日志与打点已落盘"
}

# ────────────────────────── 5. DB 探针（只读） ──────────────────────────
# join 列名（user_id）执行时先 \d memory_goals 校准（runbook §5.2 模板口径）。
db_probe() {
  local label="$1" sql="$2" username="$3"
  local result
  result="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc "${sql//<USERNAME>/$username}")"
  printf '{"label":"%s","username":"%s","result":"%s","ts":"%s"}\n' \
    "$label" "$username" "$result" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$EVID/db_probes.jsonl"
  log "probe $label -> $result"
}

db_probes() {
  log "== db probes =="
  local guest_user="${J02_GUEST_USER:-}"
  [[ -n "$guest_user" ]] || die "设 J02_GUEST_USER=<本 run guest 用户名> 后重试（runbook §5）"
  : > "$EVID/db_probes.jsonl"
  db_probe "guest_memory_goals_zero" \
    "SELECT count(*) FROM memory_goals mg JOIN users u ON mg.user_id=u.id WHERE u.username='<USERNAME>';" \
    "$guest_user"
  db_probe "guest_episodic_memories_zero" \
    "SELECT count(*) FROM episodic_memories em JOIN users u ON em.user_id=u.id WHERE u.username='<USERNAME>';" \
    "$guest_user"
  db_probe "guest_registration_source" \
    "SELECT registration_source FROM users WHERE username='<USERNAME>';" \
    "$guest_user"
}

# ────────────────────────── 6. verdict ──────────────────────────
verdict() {
  log "== verdict（budget=${BUDGET_MS}ms）=="
  python3 - "$EVID" "$BUDGET_MS" <<'PYEOF'
import json, re, sys
from pathlib import Path

evid, budget = Path(sys.argv[1]), int(sys.argv[2])
log_path = evid / "logs"
marks: dict[str, list[int]] = {}
for f in log_path.glob("run_*.log"):
    for line in f.read_text(errors="replace").splitlines():
        m = re.search(r"ms_since_pass_t0=(\d+)", line)
        if m:
            pid = re.search(r"pass=(\S+)", line)
            marks.setdefault(pid.group(1) if pid else "?", []).append(int(m.group(1)))
summary = {}
for pid, times in sorted(marks.items()):
    summary[pid] = {"max_mark_ms": max(times), "within_3min": max(times) <= budget}
(evid / "verdict.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
ok = bool(summary) and all(v["within_3min"] for v in summary.values())
print(json.dumps(summary, indent=2, ensure_ascii=False))
sys.exit(0 if ok else 1)
PYEOF
  # 注意：verdict 只判秒表维度；acceptance 全量判据见 runbook §7 映射表，
  # 由执行会话在 REPORT.md 逐条回填，不得以本脚本 exit 0 冒充验收通过。
}

# ────────────────────────── main ──────────────────────────
main() {
  mkdir -p "$EVID/screenshots" "$EVID/logs"
  printf '{"run_id":"%s","lane":"%s","pass":"%s","started_at":"%s"}\n' \
    "$RUN_ID" "$LANE" "$PASS" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" > "$EVID/run_manifest.jsonl"
  preflight
  fresh_install
  build_and_install
  run_journey
  db_probes
  if verdict; then
    log "verdict PASS（秒表维度）——全量判据回填 REPORT.md 后交独立审查"
  else
    log "verdict FAIL（秒表维度）——按 runbook §6 留证，不删 run"
    exit 1
  fi
}

main "$@"
