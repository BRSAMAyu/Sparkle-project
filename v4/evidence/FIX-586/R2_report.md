# FIX-586 R-2 — PG 环境凭据漂移只读探针报告

- 执行：FIX-586 fleet 修复 agent（worktree `wtF586`，分支 `agent/v4/f586`）
- 时刻：2026-09-29 12:43–12:46 UTC（本机 +0800 20:4x）
- 修法依据：`v4/evidence/FIX-582/diagnosis.md` §4 R-2 ①「env↔卷 hash 漂移探针进守卫」；根因面 §2.1（.env 轮换与数据面无强制同步点、容器 env 只在创建时烘入、心跳只查容器内 trust 路径不探 host 侧 scram——571 事故的检测盲区）

## 1. 交付物

| 文件 | 说明 |
|---|---|
| `scripts/devtools/pg_env_drift_probe.sh` | 只读探针（可执行）。cosmos/Sparkle-project 两侧四 `.env` 的 POSTGRES 凭据指纹 vs 容器 env（docker inspect sparkle_db）vs 卷内 pg_authid hash。**全指纹化零明文**（「长度c sha256:前12位」）；SCRAM 加盐 hash 不可与密码指纹直接比对，hash↔凭据一致性经 host 侧 scram 鉴权探针实证（`SELECT 1`，PGPASSWORD 仅经环境变量传入子进程）。判定：V1=cosmos 根 .env↔容器 env 指纹一致；V2=各 .env (user,pw) 对卷内 hash AUTH_OK；V3=sparkle_gateway + gateway/.env AUTH_OK（FIX-586 R-1 对齐面保持监视）。exit 0=全一致 / 1=漂移 / 2=环境不完整。兼容 macOS bash 3.2（无 declare -A；`$var` 后随全角字符一律 brace 形——实跑踩过 `SUMMARY（` 被当作标识符字节的坑） |
| `scripts/devtools/disk_swap_guard.sh` 尾部 | 追加探针调用（`--quiet` 单行 → `log()` 入 RESOURCE_GUARD.log；探针失败**不阻塞**守卫主流程，exit 码入日志） |
| `scripts/devtools/README.md` | 探针登记行（仓库整洁规则 5） |
| Sparkle-project 同名两文件 | live 副本原子同步（cp→chmod→mv；`diff -q` 双文件 IDENTICAL）——launchd `com.sparkle.disk-swap-guard.plist`（每 900s）实际执行的是 Sparkle-project 侧脚本，只提交 repo 副本不构成「接入例行」 |

## 2. 本机实跑证据（raw/R2_probe_run.txt，12:44Z，EXIT=0）

```
[.env 源] cosmos 根 .env                USER=postgres PW=19c sha256:3601f490715a
[.env 源] cosmos backend/.env            USER=postgres PW=19c sha256:3601f490715a
[.env 源] Sparkle-project backend/.env   USER=brsama PW=9c sha256:e2186dbdb1bb
[.env 源] Sparkle-project gateway/.env   USER=brsama PW=9c sha256:e2186dbdb1bb
[容器env] sparkle_db                     USER=postgres PW=19c sha256:3601f490715a
[卷内hash] role=brsama           133c sha256:85005bcd1f04
[卷内hash] role=postgres         133c sha256:2f6e743f26cf
[卷内hash] role=sparkle_gateway  133c sha256:3ab7ba2145b1
[鉴权探针] 四源 AUTH_OK ×4 + sparkle_gateway 对齐 AUTH_OK
RESULT: CONSISTENT — V1:PASS V2:PASS(4源) V3:PASS
```

与 F582 诊断 §1.3 四方指纹表逐值一致（3601f4/e2186 双 superuser 格局如实呈现——双身份收敛属 R-2③ 债，未超本卡范围）。

## 3. 守卫例行端到端验证

- 手动执行 live 守卫一次（20:45:38 +0800）：`guard-ok free=39G swap=0MB` + 日志新行
  `[2026-09-29 20:45:38] pg_env_drift_probe: CONSISTENT V1:PASS V2:PASS(4源) V3:PASS (exit=0)`
  → launchd 每 15 分钟起，571 形态漂移（.env 轮换未同步容器重建/卷 hash）最迟 15 分钟内现形于 RESOURCE_GUARD.log。
- DRIFT 分支可证伪性：以 /tmp 副本注入错误凭据实测（不动真实文件）——AUTH_FAIL 正确报出、`RESULT: DRIFT`、exit=1；quiet 模式单行输出正常。

## 4. 边界与遗留

- 探针依赖宿主 psql（PATH 或 homebrew postgresql@16）与容器在跑；缺失时 exit 2 并注明 ENV-INCOMPLETE（守卫日志可见，不算漂移）。
- 未覆盖 REDIS/MINIO 凭据（F582 已证四方一致；如需扩展按同型加键即可）。
- 双 superuser 身份收敛（R-2③）与「轮换 .env 必须同步 ALTER ROLE 或重建卷」操作对文档化属债面：前者留 leader 裁决（涉及两仓 .env 属主），后者操作规程已由本探针 V1/V2 判定语义固化（轮换后探针即红，按 571 同款 ALTER ROLE 对齐或重建卷）。
