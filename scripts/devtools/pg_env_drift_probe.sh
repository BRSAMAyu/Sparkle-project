#!/bin/bash
# pg_env_drift_probe.sh — PG 环境凭据漂移只读探针（FIX-586 R-2，2026-09-30）
#
# 背景：FIX-571/FIX-582 诊断（v4/evidence/FIX-582/diagnosis.md §2.1/§4 R-2）——「轮换 .env」与
# 「数据卷 initdb 烘入 hash」之间无强制同步点，容器 env 只在创建时烘入，三者漂移曾致共享 PG
# host 侧 scram 全败、计费进死信（Q04 三联事故）。本探针把该检测面固化为守卫例行：
#
#   .env POSTGRES 凭据指纹（cosmos/Sparkle-project 两侧四文件）
#     vs 容器 env 指纹（docker inspect sparkle_db）
#     vs 卷内 pg_authid hash（指纹记录 + 经 host 侧 scram 鉴权探针实证一致性——SCRAM 加盐
#        hash 不可与密码指纹直接比对，AUTH_OK 即「hash 与该凭据一致」的实证）
#
# 纪律：全程只读（SELECT 1 鉴权探针 + 目录/catalog 读）；凭据零回显零落盘，一律「长度c sha256:前12位」指纹。
# 用法：pg_env_drift_probe.sh [--quiet]   # --quiet 单行输出（供 disk_swap_guard.sh 每 15 分钟例行）
# 退出码：0=全一致；1=检出漂移；2=环境不完整（docker 缺容器/宿主无 python3/psql，非漂移）
# 依赖：docker（容器 sparkle_db 在跑）、宿主 python3（.env 解析）、psql（PATH 或 /opt/homebrew/opt/postgresql@16/bin）
# 兼容：macOS 自带 bash 3.2（无 declare -A）；launchd com.sparkle.disk-swap-guard 每 900s 经
#       disk_swap_guard.sh 尾部调用 → 日志 /Users/brsama/code/GitHub/Sparkle-project/v3/06_agent_fleet/RESOURCE_GUARD.log（只追加）
set -u
QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

COSMOS="/Users/brsama/code/GitHub/sparkle-cosmos"
SPROJ="/Users/brsama/code/GitHub/Sparkle-project"
ENVS=(
  "cosmos 根 .env|$COSMOS/.env"
  "cosmos backend/.env|$COSMOS/backend/.env"
  "Sparkle-project backend/.env|$SPROJ/backend/.env"
  "Sparkle-project gateway/.env|$SPROJ/backend/gateway/.env"
)
CONTAINER="sparkle_db"
PSQL_BIN="$(command -v psql || true)"
[ -z "$PSQL_BIN" ] && [ -x /opt/homebrew/opt/postgresql@16/bin/psql ] && PSQL_BIN=/opt/homebrew/opt/postgresql@16/bin/psql

FP() { printf '%s' "$1" | shasum -a 256 | cut -c1-12; }  # sha256 前 12 位（无换行，零明文）
GETKEY() {  # $1=file $2=key → 值（剥引号）；零回显
  python3 - "$1" "$2" <<'PYEOF'
import sys
path, key = sys.argv[1], sys.argv[2]
try:
    for line in open(path, encoding="utf-8", errors="replace"):
        s = line.strip()
        if s.startswith(key + "=") and not s.startswith("#"):
            v = s.split("=", 1)[1].strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
                v = v[1:-1]
            print(v)
            break
except OSError:
    pass
PYEOF
}
AUTH() {  # $1=user $2=pw → 0=AUTH_OK 1=FAIL（host 侧 127.0.0.1:5432 → 网桥 → scram 路径）
  PGPASSWORD="$2" "$PSQL_BIN" -h 127.0.0.1 -p 5432 -U "$1" -d sparkle -At -c "SELECT 1" >/dev/null 2>&1
}

if [ -z "$PSQL_BIN" ]; then
  [ "$QUIET" = 1 ] && echo "pg_env_drift_probe: ENV-INCOMPLETE (宿主无 psql)" || echo "环境不完整：宿主无 psql，无法做 host 侧鉴权探针"
  exit 2
fi
CONTAINER_ENV="$(docker inspect "$CONTAINER" --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null)"
RC_INSPECT=$?
if [ "$RC_INSPECT" -ne 0 ] || [ -z "$CONTAINER_ENV" ]; then
  [ "$QUIET" = 1 ] && echo "pg_env_drift_probe: ENV-INCOMPLETE (容器 $CONTAINER 不可达)" || echo "环境不完整：容器 $CONTAINER 不可达（栈未跑？非漂移，退出）"
  exit 2
fi

[ "$QUIET" = 0 ] && echo "=== PG 环境凭据漂移探针（只读；全指纹化零明文）$(date -u '+%Y-%m-%dT%H:%M:%SZ') ==="

DRIFT=0; DETAIL=""
COLLECTED=""   # 每行: label|user|pwfp|file

# --- [.env 源] 指纹 ---
for e in "${ENVS[@]}"; do
  label="${e%%|*}"; f="${e#*|}"
  if [ ! -f "$f" ]; then
    [ "$QUIET" = 0 ] && printf '[.env 源] %-30s 缺席（跳过，WARN）\n' "$label"
    DETAIL="$DETAIL WARN:${label}缺席"
    continue
  fi
  u="$(GETKEY "$f" POSTGRES_USER)"; p="$(GETKEY "$f" POSTGRES_PASSWORD)"
  if [ -z "$p" ]; then
    [ "$QUIET" = 0 ] && printf '[.env 源] %-30s 无 POSTGRES_PASSWORD 键（WARN）\n' "$label"
    DETAIL="$DETAIL WARN:${label}无键"
    continue
  fi
  COLLECTED="${COLLECTED}${label}|${u}|$(FP "$p")|${f}"$'\n'
  [ "$QUIET" = 0 ] && printf '[.env 源] %-30s USER=%s PW=%dc sha256:%s\n' "$label" "$u" "${#p}" "$(FP "$p")"
done

# --- [容器 env] 指纹 ---
CU="$(printf '%s\n' "$CONTAINER_ENV" | awk -F= '$1=="POSTGRES_USER"{print $2}')"
CP="$(printf '%s\n' "$CONTAINER_ENV" | awk -F= '$1=="POSTGRES_PASSWORD"{print $2}')"
CPF="$(FP "$CP")"
[ "$QUIET" = 0 ] && printf '[容器env] %-30s USER=%s PW=%dc sha256:%s\n' "$CONTAINER" "$CU" "${#CP}" "$CPF"

# --- [卷内 hash] pg_authid 指纹（只读 catalog）---
ROLE_HASHES="$(docker exec "$CONTAINER" psql -U postgres -d sparkle -At -v ON_ERROR_STOP=1 -c \
  "SELECT rolname||'|'||CASE WHEN rolpassword IS NULL THEN 'NULL' ELSE length(rolpassword)::text||'c sha256:'||substr(encode(sha256(convert_to(rolpassword,'UTF8')),'hex'),1,12) END FROM pg_authid WHERE rolname IN ('postgres','brsama','sparkle_gateway') ORDER BY rolname;" 2>/dev/null)"
if [ $? -ne 0 ]; then
  DETAIL="$DETAIL V4:pg_authid读失败"; DRIFT=1
fi
if [ "$QUIET" = 0 ]; then
  printf '%s\n' "$ROLE_HASHES" | while IFS='|' read -r rn rh; do
    [ -n "$rn" ] && printf '[卷内hash] role=%-16s %s\n' "$rn" "$rh"
  done
  echo "（SCRAM 加盐 hash 不可与密码指纹直接比对；hash↔凭据一致性由下方鉴权探针实证）"
fi

# --- V1: cosmos 根 .env == 容器 env（compose 属主面）---
V1="SKIP"
ROOT_LINE="$(printf '%s' "$COLLECTED" | grep '^cosmos 根 .env|')"
if [ -n "$ROOT_LINE" ]; then
  ru="$(printf '%s' "$ROOT_LINE" | cut -d'|' -f2)"; rf="$(printf '%s' "$ROOT_LINE" | cut -d'|' -f3)"
  if [ "$ru" = "$CU" ] && [ "$rf" = "$CPF" ]; then
    V1="PASS"
  else
    V1="FAIL"; DRIFT=1
    [ "$QUIET" = 0 ] && echo "[判定 V1] DRIFT：cosmos 根 .env 与容器 env POSTGRES 凭据指纹不一致（.env 轮换未随容器重建——571 事故形态）"
  fi
fi

# --- V2: 各 .env (user,pw) 对卷内 hash 的鉴权实证 ---
V2="PASS"; V2_N=0; V2_F=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  label="$(printf '%s' "$line" | cut -d'|' -f1)"
  u="$(printf '%s' "$line" | cut -d'|' -f2)"
  f="$(printf '%s' "$line" | cut -d'|' -f4)"
  p="$(GETKEY "$f" POSTGRES_PASSWORD)"
  V2_N=$((V2_N+1))
  if AUTH "$u" "$p"; then
    [ "$QUIET" = 0 ] && printf '[鉴权探针] %-30s → %s@127.0.0.1:5432 AUTH_OK（卷内 hash 与该凭据一致）\n' "$label" "$u"
  else
    V2="FAIL"; V2_F=$((V2_F+1)); DRIFT=1
    [ "$QUIET" = 0 ] && printf '[鉴权探针] %-30s → %s@127.0.0.1:5432 AUTH_FAIL（DRIFT：.env 凭据与卷内 hash 不匹配——Q04 三联形态复现）\n' "$label" "$u"
  fi
done <<EOF2
$COLLECTED
EOF2
[ "$V2_N" -eq 0 ] && V2="SKIP"

# --- V3: sparkle_gateway 对齐保持（FIX-586 R-1 对齐面）---
V3="SKIP"
GW_PW="$(GETKEY "$SPROJ/backend/gateway/.env" POSTGRES_PASSWORD)"
if printf '%s' "$ROLE_HASHES" | grep -q '^sparkle_gateway|' && [ -n "$GW_PW" ]; then
  if AUTH sparkle_gateway "$GW_PW"; then
    V3="PASS"
    [ "$QUIET" = 0 ] && echo '[鉴权探针] sparkle_gateway + gateway/.env 凭据    → AUTH_OK（FIX-586 对齐保持）'
  else
    V3="FAIL"; DRIFT=1
    [ "$QUIET" = 0 ] && echo '[鉴权探针] sparkle_gateway + gateway/.env 凭据    → AUTH_FAIL（DRIFT：586 对齐面被破坏——gateway/.env 轮换未同步 ALTER ROLE）'
  fi
fi

# --- 汇总 ---
SUMMARY="V1:$V1 V2:$V2(${V2_N}源) V3:$V3${DETAIL:+ $DETAIL}"
if [ "$DRIFT" -eq 1 ]; then
  if [ "$QUIET" = 1 ]; then echo "pg_env_drift_probe: DRIFT $SUMMARY"; else echo "RESULT: DRIFT — $SUMMARY"; fi
  exit 1
fi
if [ "$QUIET" = 1 ]; then echo "pg_env_drift_probe: CONSISTENT $SUMMARY"; else echo "RESULT: CONSISTENT — $SUMMARY (.env↔容器env↔卷内hash 全一致)"; fi
exit 0
