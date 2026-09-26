# RUNBOOK：LLM 模型健康双源复位（V3-FIX-81）

> **目标**：故障演练 / 上游排障后，让「已恢复的 provider」立即回到候选面，**无需重启引擎**。
> 背景：模型健康有两套并行生效的状态源——`llm_router` 进程内三相状态机
>（healthy/probation/unhealthy）与 redis `llm:*` 三相状态键（`llm:fail:` /
> `llm:last_fail:` / `llm:circuit:`）。**只清一个源，另一个源会把已恢复的
> provider 挡在门外**（Q-06 chaos S3a 实锤：清 redis 后生成仍持续避开目标
> 模型，重启引擎才恢复）。复位必须走双源单出口。

## 前置条件

- 引擎在运行（FastAPI :8000，任意副本）。
- 操作者持有 admin（superuser）账号，可登录获取 JWT。
- `curl` 可用。

## 复位步骤

### 1. 全量复位（推荐，排障默认）

```bash
curl -sS -X POST "http://localhost:8000/api/v1/admin/llm-health/reset" \
  -H "Authorization: Bearer ${ADMIN_JWT}" \
  -H "Content-Type: application/json" -d '{}'
```

响应回执（示例）：

```json
{
  "memory_reset_keys": ["dashscope_chat", "zhipu_coding", "..."],
  "redis_cleared_keys": 12,
  "model_key": null
}
```

核对：`memory_reset_keys` 非空（内存相复位为 healthy）、`redis_cleared_keys`
与残键数量一致。两字段由同一请求原子产生，不存在「清一源漏一源」。

### 2. 定点复位（只恢复某个 provider）

```bash
curl -sS -X POST "http://localhost:8000/api/v1/admin/llm-health/reset" \
  -H "Authorization: Bearer ${ADMIN_JWT}" \
  -H "Content-Type: application/json" \
  -d '{"model_key": "dashscope_chat"}'
```

`model_key` 必须是 router 已注册键（未注册键返回空复位列表，不造死键）。

### 3. 复位后验证

- `sparkle_llm_health_transitions_total`（ Prometheus）应出现
  `unhealthy->healthy` 相变增量；
- 发一次真实 chat 请求，观察网关日志不再出现
  `All candidates unhealthy ... failing fast`（V3-FIX-78 预检拒绝）。

## 语义边界（运维必读）

- 复位**只清状态，不改判定**：复位后若 provider 仍在故障，下一次调用失败
  会照常重新计数并按既有阈值再次熔断（这就是预期行为，不是复位失效）。
- 复位是高风险管理动作（审计 category=`llm_health_reset`，risk=high），全部
  调用进 admin 审计留痕。
- redis 侧复位失败时返回 503，内存侧可能已复位——**直接重试同一请求**即可
  （复位是幂等收敛操作，残留 redis 键随 TTL 自然衰减）。

## 关联

- 判定语义：`backend/app/core/llm_router.py`（三相滞回状态机）、
  `backend/app/services/llm/fallback.py`（redis tracker + fallback 预检）。
- 快速失败/背压语义（V3-FIX-78/79，wt448）：全候选不健康预检与本复位的
  关系是「复位恢复可试性」，不改变预检逻辑。
- 登记：v3/06_agent_fleet/DYNAMIC_ISSUES.md V3-FIX-81。
