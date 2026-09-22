#!/usr/bin/env bash
# =============================================================================
# scripts/deploy/bootstrap.sh — Sparkle 云端一键部署总入口（D-BOOTSTRAP）
# =============================================================================
# 目标：「投资人给钱即可上线」——一台 VPS + 一个域名 + 一组 API Key，
#        从 git clone 到全栈可演示的一条命令编排。
#
# 方案底稿：v3-output/DL-D-R1/CLOUD_DEPLOY.md（§3 全流程草案 + §4 云上 .env 安全默认值）
# 分工边界：本脚本只负责「从零到第一次上线」；日常发版走 scripts/deploy-prod.sh（蓝绿）。
#
# 用法：
#   sudo bash scripts/deploy/bootstrap.sh [--plan] [选项]
#
# 选项：
#   --plan                 干跑模式：只打印将执行的步骤，不做任何变更（无需 docker/.env）
#   --with-demo-seed       部署后灌入参展演示数据（默认关；演示账号密码自动生成并写入 .env）
#   --skip-smoke           跳过端到端 smoke 探针（HTTP health + 一条最小 chat 探测）
#   --lean-observability   8G 单机建议：裁掉 loki/promtail/tempo/cadvisor（--scale 0）
#   --env-file PATH        云上 .env 路径（默认 ./ .env，即仓库根 .env）
#   --image-tag TAG        覆盖镜像 tag（默认读 .env 的 IMAGE_TAG）
#   --domain HOST          对外域名（默认读 .env 的 PRODUCTION_URL host）
#   -h | --help            显示本帮助
#
# 幂等性：每一步都可安全重跑（.env 只装配一次；overlay 追加有标记防重；
#          compose up/迁移/初始化脚本全部幂等语义）。
# 安全门：.env 占位密钥未替换时拒绝继续，并列出缺哪些（见 .env.cloud.example 头注）。
# 兼容性：bash 3.2+（不用 bash4 的 ${var,,}；中文紧邻的变量一律加花括号）。
# =============================================================================
set -euo pipefail

# ----------------------------------------------------------------------------
# 路径与常量
# ----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

BASE_ENV_TEMPLATE=".env.production.example"   # 完整基线（[MUST CHANGE] 三级标注）
CLOUD_ENV_TEMPLATE=".env.cloud.example"       # 云端安全默认值 overlay（本卡交付）
CLOUD_OVERLAY_MARKER="# === sparkle cloud defaults (bootstrap overlay marker; do not remove) ==="
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="$ROOT_DIR/.env"                     # 可被 --env-file 覆盖
IMAGE_TAG_OVERRIDE=""
DOMAIN_OVERRIDE=""
DOMAIN=""
WITH_DEMO_SEED=false
SKIP_SMOKE=false
LEAN_OBS=false
PLAN_MODE=false

MIN_DISK_MB=20480      # 20G（CLOUD_DEPLOY.md §3.0）
MIN_MEM_MB=7168        # 7G
APP_NETWORK="${APP_NETWORK:-sparkle_app}"
SMOKE_CHAT_TIMEOUT="${SMOKE_CHAT_TIMEOUT:-90}"   # chat 探针整体超时（秒）

# ----------------------------------------------------------------------------
# 日志与小工具
# ----------------------------------------------------------------------------
log()  { printf '%s\n' "$*"; }
info() { printf '[bootstrap] %s\n' "$*"; }
ok()   { printf '[bootstrap] ✅ %s\n' "$*"; }
warn() { printf '[bootstrap] ⚠️  %s\n' "$*"; }
err()  { printf '[bootstrap] ❌ %s\n' "$*" >&2; }
die()  { err "$*"; printf '[bootstrap] 修正后重跑: bash scripts/deploy/bootstrap.sh\n' >&2; exit 1; }

plan_emit() { printf '    %s\n' "$*"; }

to_lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

compose() { docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"; }

# 等待 service 容器 healthy（长驻服务；无 healthcheck 时退化为 running 判定）
wait_healthy() { # label service timeout_s
  local label="$1" svc="$2" timeout="$3" waited=0 cid st
  cid="$(compose ps -aq "$svc" 2>/dev/null | tail -n 1 || true)"
  if [[ -z "$cid" ]]; then
    die "${label}：容器不存在（compose ps -aq ${svc} 为空）"
  fi
  while :; do
    st="$(docker inspect -f '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo missing)"
    if [[ "$st" == "healthy" ]]; then
      ok "${label} 健康"
      return 0
    fi
    if [[ "$st" == "<no value>" || "$st" == "missing" ]]; then
      st="$(docker inspect -f '{{.State.Status}}' "$cid" 2>/dev/null || echo missing)"
      if [[ "$st" == "running" ]]; then
        ok "${label} 运行中（无 healthcheck，按 running 判定）"
        return 0
      fi
    fi
    if (( waited >= timeout )); then
      err "${label} 等待健康超时（${timeout}s，最后状态: ${st}）"
      err "排查: docker compose -f ${COMPOSE_FILE} logs --tail 80 ${svc}"
      return 1
    fi
    sleep 5
    waited=$((waited + 5))
  done
}

# 等待 one-shot 容器 exit 0（db_migrate / minio_rbac_init / age_init 等）
wait_exit0() { # label service timeout_s
  local label="$1" svc="$2" timeout="$3" waited=0 cid st
  while :; do
    cid="$(compose ps -aq "$svc" 2>/dev/null | tail -n 1 || true)"
    if [[ -n "$cid" ]]; then
      st="$(docker inspect -f '{{.State.Status}}:{{.State.ExitCode}}' "$cid" 2>/dev/null || echo missing:0)"
      if [[ "$st" == "exited:0" ]]; then
        ok "${label} 完成（exit 0）"
        return 0
      fi
      case "$st" in
        exited:1 | exited:2 | exited:125 | exited:137 | dead)
          err "${label} 失败（状态: ${st}）"
          err "排查: docker compose -f ${COMPOSE_FILE} logs --tail 80 ${svc}"
          return 1
          ;;
      esac
    fi
    if (( waited >= timeout )); then
      err "${label} 等待完成超时（${timeout}s，最后状态: ${st:-未知}）"
      err "排查: docker compose -f ${COMPOSE_FILE} logs --tail 80 ${svc}"
      return 1
    fi
    sleep 5
    waited=$((waited + 5))
  done
}

# ----------------------------------------------------------------------------
# .env 读取与校验
# ----------------------------------------------------------------------------
env_get() { # KEY -> 打印 .env 中最后一次出现的值（与 compose 重复键 last-wins 语义一致）
  local key="$1" line val=""
  if [[ ! -f "$ENV_FILE" ]]; then
    printf ''
    return 0
  fi
  line="$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 || true)"
  if [[ -n "$line" ]]; then
    val="${line#*=}"
    val="${val%$'\r'}"
    if [[ ${#val} -ge 2 ]]; then
      if [[ "${val:0:1}" == '"' && "${val: -1}" == '"' ]]; then val="${val:1:${#val}-2}"; fi
      if [[ "${val:0:1}" == "'" && "${val: -1}" == "'" ]]; then val="${val:1:${#val}-2}"; fi
    fi
  fi
  printf '%s' "$val"
}

is_placeholder() { # 值为空或命中占位形态 → 真（前缀面与 scripts/check_production_secrets.py 对齐 + 模板 <...> 形态）
  local v="$1"
  [[ -z "$v" ]] && return 0
  case "$v" in
    __CHANGE_ME__* | CHANGE_ME* | '<'*'>' | your_* | replace_with* | changeme* | placeholder* | example_* | dummy_*)
      return 0
      ;;
  esac
  return 1
}

validate_env() {
  local -a required missing wrong_pin llm_ok_keys
  local key val k m w
  required=(
    SECRET_KEY JWT_SECRET ADMIN_SECRET INTERNAL_API_KEY
    POSTGRES_PASSWORD REDIS_PASSWORD
    MINIO_ACCESS_KEY MINIO_SECRET_KEY
    IMAGE_TAG TRUSTED_PROXIES ALLOWED_ORIGINS
    MINIO_ROOT_USER MINIO_ROOT_PASSWORD
    GRAFANA_ADMIN_USER GRAFANA_ADMIN_PASSWORD
    ALERTMANAGER_DEFAULT_WEBHOOK_URL ALERTMANAGER_CRITICAL_WEBHOOK_URL ALERTMANAGER_WARNING_WEBHOOK_URL
  )
  missing=()
  wrong_pin=()
  llm_ok_keys=()
  for key in "${required[@]}"; do
    val="$(env_get "$key")"
    if is_placeholder "$val"; then
      missing+=("$key")
    fi
  done
  # 至少一个 LLM key（多 provider 故障切换面：主 + 备建议都填）
  for k in LLM_API_KEY DASHSCOPE_API_KEY DEEPSEEK_API_KEY ZHIPU_API_KEY SILICONFLOW_API_KEY XIAOMI_MIMO_API_KEY; do
    val="$(env_get "$k")"
    if [[ -n "$val" ]] && ! is_placeholder "$val"; then
      llm_ok_keys+=("$k")
    fi
  done
  if (( ${#llm_ok_keys[@]} == 0 )); then
    missing+=("LLM_API_KEY(或任一 provider key: DASHSCOPE/DEEPSEEK/ZHIPU/SILICONFLOW/XIAOMI_MIMO)")
  fi
  # 安全钉死项（值反了 = 拒绝，云上成本/安全底线）
  val="$(env_get ENVIRONMENT)"
  [[ "$val" == "production" ]] || wrong_pin+=("ENVIRONMENT=$val (须为 production)")
  val="$(env_get DEBUG)"
  [[ "$(to_lower "$val")" == "false" ]] || wrong_pin+=("DEBUG=$val (须为 False)")
  val="$(env_get LLM_QUOTA_ENABLED)"
  [[ "$(to_lower "$val")" == "true" ]] || wrong_pin+=("LLM_QUOTA_ENABLED=$val (须为 true——云上成本底线，见 .env.cloud.example)")
  val="$(env_get GLM_BATCH_ENABLED)"
  [[ "$(to_lower "$val")" == "false" ]] || wrong_pin+=("GLM_BATCH_ENABLED=$val (须为 false——停车道云上默认熄火，见 .env.cloud.example)")

  if (( ${#missing[@]} > 0 || ${#wrong_pin[@]} > 0 )); then
    err ".env 门禁未通过（${ENV_FILE}）："
    if (( ${#missing[@]} > 0 )); then
      err "  以下 ${#missing[@]} 个变量缺失或仍是占位符，必须替换为真实值："
      for m in "${missing[@]}"; do
        err "    - ${m}"
      done
    fi
    if (( ${#wrong_pin[@]} > 0 )); then
      err "  以下安全钉死项取值不对："
      for w in "${wrong_pin[@]}"; do
        err "    - ${w}"
      done
    fi
    die "请编辑 ${ENV_FILE} 后重跑。生成强密钥: openssl rand -hex 32"
  fi
  ok ".env 门禁通过（${#required[@]} 个必填项 + LLM key: ${llm_ok_keys[*]} + 4 个安全钉死项）"
}

assemble_env() {
  local overlay_applied
  if [[ -f "$ENV_FILE" ]]; then
    overlay_applied="$(grep -cF "$CLOUD_OVERLAY_MARKER" "$ENV_FILE" 2>/dev/null || true)"
    if [[ "$overlay_applied" -gt 0 ]]; then
      info ".env 已存在且云上 overlay 已装配，跳过装配（幂等）"
      return 0
    fi
    cp "$ENV_FILE" "$ENV_FILE.bak.$(date +%Y%m%d%H%M%S)"
    warn "已存在 ${ENV_FILE}（备份为 ${ENV_FILE}.bak.*）；追加云上安全默认值 overlay（重复键以后者为准）"
    {
      printf '\n'
      cat "$CLOUD_ENV_TEMPLATE"
    } >> "$ENV_FILE"
  else
    if [[ ! -f "$BASE_ENV_TEMPLATE" || ! -f "$CLOUD_ENV_TEMPLATE" ]]; then
      die "缺少模板: ${BASE_ENV_TEMPLATE} / ${CLOUD_ENV_TEMPLATE}（请在仓库根目录运行）"
    fi
    cat "$BASE_ENV_TEMPLATE" "$CLOUD_ENV_TEMPLATE" > "$ENV_FILE"
    info "已从模板装配 ${ENV_FILE}（基线 ${BASE_ENV_TEMPLATE} + 云上 overlay ${CLOUD_ENV_TEMPLATE}）"
  fi
  chmod 600 "$ENV_FILE"
  ok ".env 权限 600"
}

# ----------------------------------------------------------------------------
# 各类检查
# ----------------------------------------------------------------------------
port_in_use() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE ":${port}$" && return 0
  elif command -v netstat >/dev/null 2>&1; then
    netstat -an 2>/dev/null | grep -E "[:.]${port}[[:space:]]" | grep -qiE "listen" && return 0
  elif command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1 && return 0
  else
    warn "系统无 ss/netstat/lsof，跳过端口 ${port} 占用检查"
  fi
  return 1
}

disk_free_mb() { df -m "$1" 2>/dev/null | awk 'NR==2 {print $4}'; }

total_mem_mb() {
  if command -v free >/dev/null 2>&1; then
    free -m 2>/dev/null | awk '/^Mem:/ {print $2}'
  elif command -v sysctl >/dev/null 2>&1; then
    echo $(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1024 / 1024 ))
  else
    echo 0
  fi
}

public_ip() {
  if command -v dig >/dev/null 2>&1; then
    dig +short myip.opendns.com @resolver1.opendns.com 2>/dev/null | tail -n 1
  else
    printf ''
  fi
}

# ----------------------------------------------------------------------------
# 步骤 0：preflight
# ----------------------------------------------------------------------------
step0_preflight() {
  info "[0/9] preflight：系统 / docker / 磁盘 / 内存 / 端口 / 证书检查"
  if [[ "$PLAN_MODE" == "true" ]]; then
    plan_emit "检查 docker 与 compose v2 可用、daemon 可达"
    plan_emit "磁盘: 仓库目录与 docker 数据根目录剩余 >= ${MIN_DISK_MB}MB"
    plan_emit "内存: 物理内存 >= ${MIN_MEM_MB}MB"
    plan_emit "端口: 80/443 未被栈外进程占用"
    plan_emit "TLS: ./ssl/fullchain.pem + ./ssl/privkey.pem 存在（缺失则中止并提示 scripts/ssl/setup_certs.sh）"
    plan_emit "防火墙: 打印 ufw 建议命令（只放行 22/80/443，不自动改防火墙）"
    plan_emit "DNS: --domain 提供时校验解析（warning-only）"
    return 0
  fi

  command -v docker >/dev/null 2>&1 || die "未安装 docker。Ubuntu/Debian: curl -fsSL https://get.docker.com | bash"
  docker compose version >/dev/null 2>&1 || die "缺少 docker compose v2 插件"
  docker info >/dev/null 2>&1 || die "docker daemon 不可达（服务未起或无权限；试试 sudo 或 usermod -aG docker \$USER 后重新登录）"

  local docker_root free_repo free_docker
  docker_root="$(docker info -f '{{.DockerRootDir}}' 2>/dev/null || echo /var/lib/docker)"
  free_repo="$(disk_free_mb "$ROOT_DIR")"
  free_docker="$(disk_free_mb "$docker_root")"
  (( free_repo >= MIN_DISK_MB )) || die "仓库目录磁盘剩余 ${free_repo}MB < ${MIN_DISK_MB}MB，先清理磁盘（镜像/构建缓存/旧 worktree）"
  (( free_docker >= MIN_DISK_MB )) || die "docker 数据目录(${docker_root})磁盘剩余 ${free_docker}MB < ${MIN_DISK_MB}MB，先 docker system prune"
  ok "磁盘: 仓库 ${free_repo}MB / docker ${free_docker}MB 可用"

  local mem
  mem="$(total_mem_mb)"
  if (( mem > 0 && mem < MIN_MEM_MB )); then
    die "物理内存 ${mem}MB < ${MIN_MEM_MB}MB（全栈 + 可观测最低需求；或用 --lean-observability 裁掉 4 个重观测容器后重试）"
  fi
  ok "内存: ${mem}MB"

  local p
  for p in 80 443; do
    if port_in_use "$p"; then
      if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^sparkle_nginx$'; then
        ok "端口 ${p} 被占用 —— 占用者是 sparkle_nginx（本栈自身，重跑场景，放行）"
      else
        die "端口 ${p} 已被非本栈进程占用：sudo lsof -iTCP:${p} -sTCP:LISTEN 溯源后停掉它"
      fi
    else
      ok "端口 ${p} 空闲"
    fi
  done

  if [[ -f ssl/fullchain.pem && -f ssl/privkey.pem ]]; then
    ok "TLS 证书就绪（./ssl/fullchain.pem + privkey.pem）"
  else
    err "缺少 TLS 证书: ./ssl/fullchain.pem / ./ssl/privkey.pem（nginx 挂载硬依赖，缺了起不来）"
    err "  正式域名: bash scripts/ssl/setup_certs.sh api.<你的域名> ./ssl   （Let's Encrypt 路径）"
    err "  临时自签: bash scripts/ssl/generate_dev_certs.sh   （仅内网演示）"
    die "证书就绪后重跑"
  fi

  warn "防火墙建议（不自动改动，人工执行）: sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw enable"
  warn "  数据面端口 5432/6379/9000/8000/50051/3000/9090 保持不对公网开放（compose 内已 internal:true）"

  if [[ -n "$DOMAIN_OVERRIDE" ]] && command -v dig >/dev/null 2>&1; then
    local resolved myip
    resolved="$(dig +short "$DOMAIN_OVERRIDE" 2>/dev/null | grep -E '^[0-9.]+$' | tail -n 1 || true)"
    myip="$(public_ip)"
    if [[ -z "$resolved" ]]; then
      warn "DNS: ${DOMAIN_OVERRIDE} 尚无 A 记录解析（可能还在传播），继续但不保证外部可达"
    elif [[ -n "$myip" && "$resolved" != "$myip" ]]; then
      warn "DNS: ${DOMAIN_OVERRIDE} → ${resolved}，但本机出口 IP 检测为 ${myip}（若机器在 NAT 后属正常，warning-only）"
    else
      ok "DNS: ${DOMAIN_OVERRIDE} → ${resolved}"
    fi
  fi
}

# ----------------------------------------------------------------------------
# 步骤 1：.env 云端装配 + 门禁
# ----------------------------------------------------------------------------
step1_env() {
  info "[1/9] .env 云端装配（基线 + 云上安全 overlay）与占位符门禁"
  if [[ "$PLAN_MODE" == "true" ]]; then
    if [[ -f "$ENV_FILE" ]]; then
      plan_emit "${ENV_FILE} 已存在: 无 overlay 标记则先备份再追加 overlay；有则跳过（幂等）"
    else
      plan_emit "cat ${BASE_ENV_TEMPLATE} ${CLOUD_ENV_TEMPLATE} > ${ENV_FILE} && chmod 600 ${ENV_FILE}"
    fi
    plan_emit "门禁: 18 个必填变量非占位 + 至少 1 个 LLM key + 4 个安全钉死项(ENVIRONMENT/DEBUG/LLM_QUOTA_ENABLED/GLM_BATCH_ENABLED)"
    plan_emit "门禁: docker compose config -q 语法校验（:? 硬失败变量兜底）"
    return 0
  fi
  assemble_env
  validate_env
  if ! compose config -q 2>/tmp/bootstrap_compose_config.err; then
    err "compose 配置校验失败（docker compose config -q）："
    sed 's/^/    /' /tmp/bootstrap_compose_config.err >&2 || true
    rm -f /tmp/bootstrap_compose_config.err
    die "修复 .env 后重跑"
  fi
  rm -f /tmp/bootstrap_compose_config.err
  ok "compose 配置校验通过（config -q）"
}

# ----------------------------------------------------------------------------
# 步骤 2：镜像
# ----------------------------------------------------------------------------
step2_images() {
  info "[2/9] 镜像拉取（IMAGE_TAG=${IMAGE_TAG_OVERRIDE:-$(env_get IMAGE_TAG)}）"
  if [[ "$PLAN_MODE" == "true" ]]; then
    plan_emit "docker compose -f ${COMPOSE_FILE} --env-file <env> pull   （ghcr.io CI 产物：gateway/backend 及全部第三方镜像）"
    plan_emit "失败兜底提示: 无 ghcr 拉取权限时，用 CI 推送的私有 registry 或设置 GATEWAY_IMAGE/BACKEND_IMAGE 指向可拉取的镜像"
    return 0
  fi
  if [[ -n "$IMAGE_TAG_OVERRIDE" ]]; then
    export IMAGE_TAG="$IMAGE_TAG_OVERRIDE"
  fi
  if ! compose pull; then
    err "镜像拉取失败。两种可能："
    err "  1) ghcr.io 仓库为 private：先 docker login ghcr.io，或把 GATEWAY_IMAGE/BACKEND_IMAGE 指到你自己的 registry"
    err "  2) 无 CI 产物：在 CI（.github/workflows/ci.yml）跑一次镜像发布，或在本机 docker build 后 docker push"
    die "镜像就绪后重跑（已完成步骤会自动跳过）"
  fi
  ok "镜像就绪"
}

# ----------------------------------------------------------------------------
# 步骤 3：DB 起稳
# ----------------------------------------------------------------------------
step3_db() {
  info "[3/9] 数据库与 Redis 起稳"
  if [[ "$PLAN_MODE" == "true" ]]; then
    plan_emit "docker compose up -d db redis → 轮询 sparkle_db 健康(pg_isready) 与 sparkle_redis 健康"
    return 0
  fi
  compose up -d db redis
  wait_healthy "PostgreSQL" db 300
  wait_healthy "Redis" redis 300
}

# ----------------------------------------------------------------------------
# 步骤 4：迁移（Alembic）
# ----------------------------------------------------------------------------
step4_migrate() {
  info "[4/9] 数据库迁移（db_migrate one-shot: alembic upgrade head）"
  if [[ "$PLAN_MODE" == "true" ]]; then
    plan_emit "docker compose up -d db_migrate → 轮询容器退出码（exit 0 通过；非 0 打日志并中止）"
    plan_emit "幂等: 已迁移过的库重跑 = alembic 无操作；schema 唯一入口是 Alembic（仓库硬规则）"
    return 0
  fi
  compose up -d db_migrate
  wait_exit0 "数据库迁移" db_migrate 600
}

# ----------------------------------------------------------------------------
# 步骤 5：扩展初始化（AGE/pgvector + RAG 索引）
# ----------------------------------------------------------------------------
step5_extensions() {
  info "[5/9] 扩展初始化（pgvector/Apache AGE + RAG 向量索引）"
  if [[ "$PLAN_MODE" == "true" ]]; then
    plan_emit "优先路径: 若 compose 已定义 age_init 类 one-shot 服务（D-AGE 卡合入后）→ up + 等 exit 0"
    plan_emit "当前路径: up backend（running 即可）→ exec: python scripts/init_age_extension.py（ensure vector+age，幂等）"
    plan_emit "          exec: python scripts/init_redis_index.py（RAG 向量索引）"
    plan_emit "现状提示: prod db 镜像暂未内置 AGE（缺口#1，D-AGE 卡并行修复中）——AGE 段失败按 WARN 处理不阻塞上线，TODO 钩子见脚本内注释"
    return 0
  fi
  # D-AGE 撞面规避钩子：若 prod compose 未来合入 age_init one-shot（与 dev compose 同名语义），
  # 自动走 compose 路径；否则 exec 既有脚本。不硬编码任何新路径，两形态互不冲突。
  local age_svc
  age_svc="$(compose config --services 2>/dev/null | grep -xE '(sparkle_)?age_init' | head -n 1 || true)"
  if [[ -n "$age_svc" ]]; then
    info "检测到 compose 内 AGE 初始化服务: ${age_svc}（D-AGE 已合入形态），走 compose 路径"
    compose up -d "$age_svc"
    wait_exit0 "AGE 扩展初始化(${age_svc})" "$age_svc" 300
  else
    # TODO(D-AGE): prod compose db 镜像切 pgvector-age + age_init 接线后，本分支自然退役。
    compose up -d backend
    local cid st waited=0
    cid="$(compose ps -aq backend | tail -n 1)"
    while :; do
      st="$(docker inspect -f '{{.State.Status}}' "$cid" 2>/dev/null || echo missing)"
      if [[ "$st" == "running" ]]; then
        break
      fi
      if (( waited >= 180 )); then
        err "backend 容器未进入 running（状态: ${st}）"
        compose logs --tail 50 backend || true
        die "backend 起不来，先排障再重跑"
      fi
      sleep 5
      waited=$((waited + 5))
    done
    if compose exec -T backend python scripts/init_age_extension.py; then
      ok "AGE/pgvector 扩展初始化完成"
    else
      warn "AGE 扩展初始化失败——大概率是当前 prod db 镜像(pgvector/pgvector:pg16)未内置 Apache AGE（仓库缺口#1）"
      warn "  影响: 星图/知识图谱（AGE 面）暂不可用，其余功能不受阻"
      warn "  修复: 等 D-AGE 卡合入（db 镜像换 docker/pgvector-age.Dockerfile 产物 + age_init 接进 prod compose），重跑本脚本即自动走 compose 路径"
    fi
  fi
  if compose exec -T backend python scripts/init_redis_index.py; then
    ok "RAG 向量索引就绪"
  else
    warn "RAG 向量索引初始化失败（不阻塞上线；RAG 检索面降级，后可手动重跑 scripts/init_redis_index.py）"
  fi
}

# ----------------------------------------------------------------------------
# 步骤 6：MinIO 桶
# ----------------------------------------------------------------------------
step6_minio() {
  info "[6/9] MinIO 与桶初始化（minio_rbac_init one-shot）"
  if [[ "$PLAN_MODE" == "true" ]]; then
    plan_emit "docker compose up -d minio minio_rbac_init → 等 one-shot exit 0（uploads/exports/backups 三桶 + 三组专属凭据）"
    return 0
  fi
  compose up -d minio minio_rbac_init
  wait_healthy "MinIO" minio 300
  wait_exit0 "MinIO 桶/RBAC 初始化" minio_rbac_init 300
}

# ----------------------------------------------------------------------------
# 步骤 7：全栈拉起（网关蓝绿 + 引擎 + celery + nginx + 可观测）
# ----------------------------------------------------------------------------
step7_up() {
  info "[7/9] 全栈拉起（蓝绿网关/backend/agent/celery/nginx/可观测）"
  if [[ "$PLAN_MODE" == "true" ]]; then
    plan_emit "docker compose up -d  （依赖链: db healthy → db_migrate 完成 → backend/agent/celery；nginx 最后）"
    local glm_plan
    glm_plan="$(env_get GLM_BATCH_ENABLED)"
    if [[ "$(to_lower "$glm_plan")" != "true" ]]; then
      plan_emit "  附加 --scale celery_glm_batch_worker=0（GLM_BATCH_ENABLED!=true：停车道云上不起专用 worker，双保险）"
    fi
    if [[ "$LEAN_OBS" == "true" ]]; then
      plan_emit "  附加 --scale loki=0 --scale promtail=0 --scale tempo=0 --scale cadvisor=0（--lean-observability）"
    fi
    return 0
  fi
  local -a scale_args=()
  local glm
  glm="$(env_get GLM_BATCH_ENABLED)"
  if [[ "$(to_lower "$glm")" != "true" ]]; then
    scale_args+=(--scale celery_glm_batch_worker=0)
    info "GLM_BATCH_ENABLED!=true → celery_glm_batch_worker 以 0 副本启动（成本双保险之一，另一层是 .env 的 GLM_BATCH_ENABLED=false）"
  fi
  if [[ "$LEAN_OBS" == "true" ]]; then
    scale_args+=(--scale loki=0 --scale promtail=0 --scale tempo=0 --scale cadvisor=0)
    info "lean 观测模式: loki/promtail/tempo/cadvisor 不启动（8G 单机建议）"
  fi
  compose up -d ${scale_args[@]+"${scale_args[@]}"}
  wait_healthy "gateway_blue" gateway_blue 420
  wait_healthy "nginx(边缘)" nginx 300
}

# ----------------------------------------------------------------------------
# 步骤 7.5：演示数据种子（--with-demo-seed，默认跳过）
# ----------------------------------------------------------------------------
step_seed() {
  if [[ "$WITH_DEMO_SEED" != "true" ]]; then
    info "[7.5] 演示数据种子：未启用（--with-demo-seed 开启；游客扫码体验链路 /api/v1/auth/guest 不依赖本步）"
    return 0
  fi
  info "[7.5] 演示数据种子（seed_demo_user_enhanced：演示账号+计划+会话+成就+星图皮肤）"
  if [[ "$PLAN_MODE" == "true" ]]; then
    plan_emit "LOCAL_SMOKE_PASSWORD 未设置时自动生成一次并写回 .env"
    plan_emit "docker compose exec -T -e LOCAL_SMOKE_PASSWORD=*** backend python scripts/seed_demo_user_enhanced.py（幂等 select-then-insert）"
    return 0
  fi
  local seed_pw
  seed_pw="$(env_get LOCAL_SMOKE_PASSWORD)"
  if [[ -z "$seed_pw" ]]; then
    seed_pw="$(openssl rand -base64 18 2>/dev/null || head -c 18 /dev/urandom | base64)"
    {
      printf '\n# added by bootstrap: demo account password (generated)\nLOCAL_SMOKE_PASSWORD=%s\n' "$seed_pw"
    } >> "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    info "已生成演示账号密码并写入 ${ENV_FILE}（LOCAL_SMOKE_PASSWORD）"
  fi
  if compose exec -T -e LOCAL_SMOKE_PASSWORD="$seed_pw" backend python scripts/seed_demo_user_enhanced.py; then
    ok "演示数据就绪：账号 chat_test（密码在 ${ENV_FILE} 的 LOCAL_SMOKE_PASSWORD；演示账号不上二维码，观众走 /guest 游客链路）"
    info "展后清场: docker compose -f ${COMPOSE_FILE} exec backend python scripts/clean_demo_data.py"
  else
    warn "演示数据种子失败（不阻塞上线；可后补: compose exec backend python scripts/seed_demo_user_enhanced.py）"
  fi
}

# ----------------------------------------------------------------------------
# 步骤 8：readiness
# ----------------------------------------------------------------------------
gw_internal_check() { # path -> 经 app 内网对 gateway_blue 探活（与 deploy-prod.sh 同款机制）
  docker run --rm --network "$APP_NETWORK" curlimages/curl:8.7.1 -fsS --max-time 10 "http://gateway_blue:8080$1" >/dev/null 2>&1
}

step8_readiness() {
  info "[8/9] readiness（网关 /api/v1/health 与 /api/v1/health/cqrs）"
  if [[ "$PLAN_MODE" == "true" ]]; then
    plan_emit "内网探活: docker run --rm --network ${APP_NETWORK} curlimages/curl … http://gateway_blue:8080/api/v1/health 与 /api/v1/health/cqrs"
    plan_emit "公网探活(--domain 提供): curl -fsS https://<域名>/api/v1/health"
    return 0
  fi
  info "（首次探活会拉取 curlimages/curl 小镜像）"
  local waited=0
  until gw_internal_check /api/v1/health && gw_internal_check /api/v1/health/cqrs; do
    if (( waited >= 240 )); then
      err "网关 readiness 超时"
      err "排查: docker compose -f ${COMPOSE_FILE} logs --tail 80 gateway_blue backend agent"
      die "readiness 未通过"
    fi
    sleep 5
    waited=$((waited + 5))
  done
  ok "网关内网 readiness 通过（/api/v1/health + /api/v1/health/cqrs）"
  if [[ -n "$DOMAIN" ]]; then
    if curl -fsS --max-time 15 "https://${DOMAIN}/api/v1/health" >/dev/null 2>&1; then
      ok "公网 readiness 通过: https://${DOMAIN}/api/v1/health"
    else
      warn "公网探活未通过（https://${DOMAIN}）——检查 DNS A 记录/防火墙 443/证书；内网已通过则服务本身是好的"
    fi
  fi
}

# ----------------------------------------------------------------------------
# 步骤 9：smoke（--skip-smoke 跳过）
# ----------------------------------------------------------------------------
step9_smoke() {
  if [[ "$SKIP_SMOKE" == "true" ]]; then
    info "[9/9] smoke：已按 --skip-smoke 跳过"
    return 0
  fi
  info "[9/9] smoke 探针（HTTP health + 一条最小 chat 端到端探测）"
  if [[ "$PLAN_MODE" == "true" ]]; then
    plan_emit "HTTP: /api/v1/health 与 /api/v1/health/cqrs（公网或内网）"
    plan_emit "chat 探针（在 backend 容器内执行，免宿主机依赖）:"
    plan_emit "  1) POST gateway_blue:8080/api/v1/auth/guest → access_token"
    plan_emit "  2) websockets 连 ws://gateway_blue:8080/ws/chat（Authorization: Bearer；prod 走 jwt_header）"
    plan_emit "  3) 发一条 {type:message,message:...} → 断言收到任意流式帧（产生 1 次 LLM 调用，量级 < 0.1 元）"
    plan_emit "  探针失败仅 WARN 不阻塞（上线判定以 readiness 为准）；完整 E2E: bash scripts/run_e2e_smoke.sh"
    return 0
  fi
  if ! gw_internal_check /api/v1/health; then
    die "smoke HTTP 健康检查失败（readiness 刚过又失败 → 查 gateway_blue 日志）"
  fi
  ok "smoke HTTP health 通过"
  info "chat 端到端探针运行中（最长 ${SMOKE_CHAT_TIMEOUT}s，会产生一次最小 LLM 调用）…"
  if compose exec -T backend python - <<'PYEOF'
import asyncio
import json
import urllib.request
import uuid

GATEWAY = "http://gateway_blue:8080"

try:
    from websockets.asyncio.client import connect as ws_connect  # websockets >= 12 新 API
    WS_HEADERS_KWARG = "additional_headers"
except ImportError:  # 旧版兜底
    from websockets import connect as ws_connect
    WS_HEADERS_KWARG = "extra_headers"


def guest_token() -> str:
    req = urllib.request.Request(
        GATEWAY + "/api/v1/auth/guest",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode())
    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"guest 响应无 access_token: keys={sorted(payload.keys())}")
    return token


async def chat_probe(token: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    async with ws_connect(
        GATEWAY + "/ws/chat", **{WS_HEADERS_KWARG: headers}, open_timeout=30, close_timeout=5
    ) as ws:
        await ws.send(
            json.dumps(
                {
                    "type": "message",
                    "message": "你好，请用一句话介绍你自己（部署探针）",
                    "request_id": "bootstrap-smoke-" + uuid.uuid4().hex[:8],
                },
                ensure_ascii=False,
            )
        )
        frame = await asyncio.wait_for(ws.recv(), timeout=75)
        data = json.loads(frame) if isinstance(frame, str) else {}
        return str(data.get("type", frame[:80]))


def main() -> int:
    token = guest_token()
    frame_type = asyncio.run(chat_probe(token))
    print(f"[probe] OK: ws chat 首帧 type={frame_type}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PYEOF
  then
    ok "chat 端到端探针通过（guest 登录 → WS 鉴权 → 收到流式回复帧）"
  else
    warn "chat 端到端探针未通过（不阻塞上线；常见原因：LLM key 未配好/上游超时/WS 鉴权策略变化）"
    warn "  完整 E2E 验证: bash scripts/run_e2e_smoke.sh ；网关日志: docker compose -f ${COMPOSE_FILE} logs gateway_blue"
  fi
}

# ----------------------------------------------------------------------------
# 摘要（含回滚提示）
# ----------------------------------------------------------------------------
step_summary() {
  local plan_prefix=""
  local entry="内部网关 gateway_blue:8080（app 内网）"
  if [[ "$PLAN_MODE" == "true" ]]; then
    plan_prefix="[PLAN] "
    info "[PLAN] 摘要（以下为部署完成后将打印的内容样例）"
  else
    info "[9/9] 部署摘要"
  fi
  if [[ -n "$DOMAIN" ]]; then
    entry="https://${DOMAIN}（对外） + 内部网关 gateway_blue:8080（app 内网）"
  fi
  log "──────────────────────────────────────────────────────────"
  log " ${plan_prefix}Sparkle 星火 — 云端部署概要"
  log "──────────────────────────────────────────────────────────"
  log " 服务入口   : ${entry}"
  log " 健康探针   : /api/v1/health ・ /api/v1/health/cqrs ・ backend /health"
  log " 配置与密钥 : ${ENV_FILE}（600 权限；.env.bak.* 为装配前备份）"
  log " 观测       : Grafana/Prometheus 仅内网，SSH 隧道: ssh -L 3000:127.0.0.1:3000 <user>@<vps>"
  log ""
  log " 日常发版   : IMAGE_TAG=<新tag> bash scripts/deploy-prod.sh   （蓝绿切换+健康门）"
  log " 回滚·应用  : IMAGE_TAG=<旧tag> 重跑 deploy-prod.sh，蓝绿自动回切"
  log " 回滚·数据  : bash scripts/backup_prod_data.sh（建议 cron 化）→ bash scripts/restore_prod_data.sh <备份包>"
  log " 停止全栈   : docker compose -f ${COMPOSE_FILE} down （注意：不加 -v；数据在 ./postgres_data 等 bind mount）"
  log ""
  log " 备份 cron  : 15 3 * * * cd ${ROOT_DIR} && bash scripts/backup_prod_data.sh >> /var/log/sparkle-backup.log 2>&1"
  log " 移动端出包 : cd mobile && flutter build apk --release \\"
  log "              --dart-define=API_BASE_URL=https://${DOMAIN:-api.example.com} \\"
  log "              --dart-define=WS_BASE_URL=wss://${DOMAIN:-api.example.com} \\"
  log "              --dart-define=ENABLE_GOOGLE_SERVICES=false --dart-define=FCM_ENABLED=false"
  if [[ "$WITH_DEMO_SEED" == "true" && "$PLAN_MODE" != "true" ]]; then
    log " 演示账号   : chat_test（密码在 ${ENV_FILE}；展后清场 scripts/clean_demo_data.py）"
  fi
  log "──────────────────────────────────────────────────────────"
}

# ----------------------------------------------------------------------------
# 参数解析
# ----------------------------------------------------------------------------
usage() {
  grep -E '^#   ' "$BASH_SOURCE" | head -20 | sed 's/^#   //'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plan)                 PLAN_MODE=true ;;
    --with-demo-seed)       WITH_DEMO_SEED=true ;;
    --skip-smoke)           SKIP_SMOKE=true ;;
    --lean-observability)   LEAN_OBS=true ;;
    --env-file)             ENV_FILE="$2"; shift ;;
    --image-tag)            IMAGE_TAG_OVERRIDE="$2"; shift ;;
    --domain)               DOMAIN_OVERRIDE="$2"; shift ;;
    -h | --help)            usage; exit 0 ;;
    *)                      err "未知参数: $1"; usage; exit 1 ;;
  esac
  shift
done

# 域名：--domain 优先，否则读 .env PRODUCTION_URL 的 host 部分（.env 不存在则为空）
DOMAIN="$DOMAIN_OVERRIDE"
if [[ -z "$DOMAIN" && -f "$ENV_FILE" ]]; then
  DOMAIN="$(env_get PRODUCTION_URL | sed -E 's#^https?://##; s#/.*$##; s/:.*$##')"
fi

# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------
info "Sparkle 云端 bootstrap 开始（root=${ROOT_DIR}${PLAN_MODE:+，PLAN 干跑模式}）"
step0_preflight
step1_env
step2_images
step3_db
step4_migrate
step5_extensions
step6_minio
step7_up
step_seed
step8_readiness
step9_smoke
step_summary
if [[ "$PLAN_MODE" != "true" ]]; then
  ok "全部完成 —— 系统已可演示"
else
  info "PLAN 干跑结束（未做任何变更）"
fi
