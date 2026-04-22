# Stage 30 Process Scaffolding Templates

Process scaffolding is template-only. Free-form LLM-authored metacognitive prompts are forbidden.

## Registered Templates

1. `mc_process_time_more_support_factors`
   你之前预估用 {predicted_value} 小时完成，实际用了 {actual_value} 小时。你预估时主要考虑了哪些因素？
2. `mc_process_time_more_support_pattern`
   这是最近第 {repeat_count} 次类似任务比预估更久。你注意到自己在估时上漏掉了哪类成本吗？
3. `mc_process_time_less_support_buffer`
   你最近通常会比预估更早完成。你是在哪一步留了更稳的缓冲，还是把任务拆得更清楚了？
4. `mc_process_completion_more_support`
   你最近对完成比例的预估常常高于结果。你判断“已经能完成”时，最看重的依据是什么？
5. `mc_process_completion_less_support`
   你最近的完成比例经常高于自己原先的预估。下次设目标时，哪些证据能帮助你更敢于按真实能力估计？
6. `mc_process_mastery_more_support`
   你最近对掌握度的预估偏高一些。你通常用什么信号判断“我已经掌握了”？
7. `mc_process_mastery_less_support`
   你最近对掌握度常常估得偏保守。回头看时，哪些证据说明你其实已经比自己想得更稳了？
8. `mc_process_cross_dim_repeat`
   这已经是本周第 {repeat_count} 次出现相似判断偏差。你觉得自己当时用了哪套固定判断模式？

## Contract

- Trigger only when `sample_size >= 20`.
- Trigger only when `abs(bias_mean) >= 0.3`.
- Same user and dimension: at most once every 72 hours.
- Templates may ask about evidence, factors, buffers, or judgment patterns.
- Templates may not infer personality, diagnosis, or fixed identity.
