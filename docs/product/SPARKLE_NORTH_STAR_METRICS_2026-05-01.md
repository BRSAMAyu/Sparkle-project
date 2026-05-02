# Sparkle North Star Metrics

> Created: 2026-05-01  
> Owner: C10 closeout  
> Source tables/API: `north_star_metric_events`, `GET /api/v1/analytics/north-star/trends`

## Metric Definitions

| Metric | Key | Unit | Definition | Write path |
|---|---|---:|---|---|
| Exam pass probability | `exam_pass_probability` | ratio 0-1 | Average predicted probability that a learner can pass the target exam from exam sprint intake. | `ExamSprintIntakeService.intake()` records `exam_pass_probability_estimated` after plan creation. |
| Exam pass outcome rate | `exam_pass_outcome_rate` | ratio 0-1 | Post-exam reviews passed divided by post-exam reviews recorded. `exam_passed` is used when supplied; otherwise `result_rating >= 3` is the compatibility proxy. | `ExamSprintReviewService.submit_post_exam_review()` records `exam_outcome_recorded`. |
| 7-day goal completion rate | `seven_day_goal_completion_rate` | ratio 0-1 | Completed 7-day survival sprint goals divided by 7-day survival sprint goals started. | Intake records `seven_day_goal_started` for <=7 day or `seven_day_survival` sprints; completion checks and auto-archive record `seven_day_goal_completed`. |

## Event Contract

Each event is idempotent by `event_key`, so retries update the same logical metric instead of double-counting.

Required fields:
- `user_id`
- `event_type`
- `event_key`
- `source`
- `metric_date`
- `occurred_at`
- `payload`

Optional dimensions:
- `plan_id`
- `task_id`
- `value_float`
- `numerator`
- `denominator`
- `passed`

## Query Surface

`GET /api/v1/analytics/north-star/trends`

Query params:
- `days`: 1-365, default 30
- `start_date`: optional ISO date
- `end_date`: optional ISO date

The response returns metric definitions, a range summary, and daily trend points for dashboard/product analytics use.
