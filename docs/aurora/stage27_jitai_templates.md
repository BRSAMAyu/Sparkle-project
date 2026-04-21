# Stage 27 JITAI Template Registry

Rule AL requires all Stage 27 JITAI hint copy to come from a registered template. The live registry below mirrors `backend/app/services/jitai_trigger_service.py`.

| Template ID | Dimension | Direction | Message |
| --- | --- | --- | --- |
| `study_pace_below` | `study_pace` | `below` | 你最近学习节奏低于常态，先把目标缩成 15 分钟再启动。 |
| `study_pace_above` | `study_pace` | `above` | 你最近学习强度高于常态，今晚记得留一段缓冲收尾。 |
| `completion_rate_below` | `completion_rate` | `below` | 你最近完成率在下滑，先只收掉一个最小闭环。 |
| `completion_rate_above` | `completion_rate` | `above` | 你最近完成率高于常态，适合趁热补一段复盘巩固。 |
| `engagement_level_below` | `engagement_level` | `below` | 你最近互动投入偏低，先做一次很短的主动提问或记录。 |
| `engagement_level_above` | `engagement_level` | `above` | 你最近投入很深，别忘了留一点空间做轻量总结。 |
| `mood_valence_below` | `mood_valence` | `below` | 你最近情绪倾向偏低，先选一个最稳的小动作找回节奏。 |
| `mood_valence_above` | `mood_valence` | `above` | 你最近状态比平时更亮，适合承接一件需要推进感的任务。 |
| `plan_adherence_below` | `plan_adherence` | `below` | 你最近有些偏离原计划，先把今天的主线重新钉住。 |
| `plan_adherence_above` | `plan_adherence` | `above` | 你最近跟计划很稳，可以顺手把下一步准备动作补齐。 |

## Constraints

- Copy must remain rule-based and non-LLM.
- Single emitted hint stays within 80 characters.
- New templates must be added here and to `TEMPLATE_REGISTRY` in the same change.
