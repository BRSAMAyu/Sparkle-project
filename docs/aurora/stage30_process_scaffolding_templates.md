# Stage 30 · 过程脚手架与仪表盘语言模板注册表

> 由 `scripts/stage30/render_stage30_templates.py` 从 `backend/app/services/metacognition_registry.py` 自动生成，勿手改。

## 过程脚手架模板（process_scaffolding）

| template_id | dim | direction | i18n key |
| --- | --- | --- | --- |
| `mc_process_time_more_support_factors` | time_estimation_bias | more_support | `metacognition.process_template_time_more_support` |
| `mc_process_time_more_support_pattern` | time_estimation_bias | more_support | `metacognition.process_template_time_more_support_pattern` |
| `mc_process_time_less_support_buffer` | time_estimation_bias | less_support | `metacognition.process_template_time_less_support` |
| `mc_process_completion_more_support` | completion_bias | more_support | `metacognition.process_template_completion_more_support` |
| `mc_process_completion_less_support` | completion_bias | less_support | `metacognition.process_template_completion_less_support` |
| `mc_process_mastery_more_support` | mastery_bias | more_support | `metacognition.process_template_mastery_more_support` |
| `mc_process_mastery_less_support` | mastery_bias | less_support | `metacognition.process_template_mastery_less_support` |
| `mc_process_cross_dim_repeat` | shared | repeat_pattern | `metacognition.process_template_cross_dim_repeat` |

## 仪表盘语言模板（dashboard_language）

| template_id | dim | direction | i18n key |
| --- | --- | --- | --- |
| `mc_dashboard_time_more_support` | time_estimation_bias | more_support | `你过去 {sample_size} 次对完成时间估得偏乐观 {display_value} 小时。` |
| `mc_dashboard_time_less_support` | time_estimation_bias | less_support | `你过去 {sample_size} 次通常比自己的时间预估更早完成 {display_value} 小时。` |
| `mc_dashboard_completion_more_support` | completion_bias | more_support | `你过去 {sample_size} 次对完成比例估得偏乐观 {display_value} 个百分点。` |
| `mc_dashboard_completion_less_support` | completion_bias | less_support | `你过去 {sample_size} 次对完成比例估得偏保守 {display_value} 个百分点。` |
| `mc_dashboard_mastery_more_support` | mastery_bias | more_support | `你过去 {sample_size} 次对掌握度估得偏乐观 {display_value} 个百分点。` |
| `mc_dashboard_mastery_less_support` | mastery_bias | less_support | `你过去 {sample_size} 次对掌握度估得偏保守 {display_value} 个百分点。` |
| `mc_dashboard_insufficient` | shared | insufficient | `样本不足，继续观察中。` |
| `mc_dashboard_trend_improving` | shared | improving | `最近几周正在变稳。` |
| `mc_dashboard_trend_stable` | shared | stable | `最近几周基本稳定。` |
| `mc_dashboard_trend_worsening` | shared | worsening | `最近几周的波动又放大了一些。` |
