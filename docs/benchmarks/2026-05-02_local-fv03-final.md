# SparkleGoalBench Benchmark Report · full

- Run ID: `9c2f862bc417`
- Commit: `local-fv03-final`
- Generated at: `2026-05-02T06:22:38.763432+00:00`
- Gate status: **PASSED**
- Pass rate: **100.0%** (24/24)
- Estimated cost: {"estimated_turns": 48.0}
- Estimated latency: {"estimated_seconds": 64.0}

## Gate Decision

- Blockers: none
- Warnings: none
- Previous pass rate: None
- Trend delta: None

## Suite Breakdown

| Suite | Passed | Total | Pass Rate | Recommendation |
|---|---:|---:|---:|---|
| ExamSprintBench | 12 | 12 | 100.0% | safe_to_promote |
| ProjectDeliveryBench | 4 | 4 | 100.0% | safe_to_promote |
| JobSearchBench | 4 | 4 | 100.0% | safe_to_promote |
| MultiGoalLifeBench | 4 | 4 | 100.0% | safe_to_promote |

## Regressions

No scenario regressions detected.

## Raw Summary

```json
{
  "run_id": "9c2f862bc417",
  "suite_name": "full",
  "status": "passed",
  "total": 24,
  "passed": 24,
  "failed": 0,
  "pass_rate": 1.0,
  "gate": {
    "status": "passed",
    "blockers": [],
    "warnings": [],
    "previous_pass_rate": null,
    "trend_delta": null,
    "high_risk_failures": [],
    "medium_risk_failures": [],
    "low_risk_failures": []
  },
  "suite_breakdown": {
    "ExamSprintBench": {
      "total": 12,
      "passed": 12,
      "failed": 0,
      "pass_rate": 1.0,
      "reports": [
        {
          "scenario_id": "scne11b0690a42c",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 4,
            "domain": "exam_sprint",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 6.0
          },
          "latency_estimate": {
            "estimated_seconds": 8.0
          },
          "run_at": "2026-05-02T06:22:38.763308+00:00"
        },
        {
          "scenario_id": "scn5628648c684e",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 2,
            "domain": "exam_sprint",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 3.0
          },
          "latency_estimate": {
            "estimated_seconds": 4.0
          },
          "run_at": "2026-05-02T06:22:38.763312+00:00"
        },
        {
          "scenario_id": "scn9b48b62e2ea4",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "exam_sprint",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763313+00:00"
        },
        {
          "scenario_id": "scn1af48d591572",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "exam_sprint",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763316+00:00"
        },
        {
          "scenario_id": "scn0e7a463524c8",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 2,
            "domain": "exam_sprint",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 3.0
          },
          "latency_estimate": {
            "estimated_seconds": 4.0
          },
          "run_at": "2026-05-02T06:22:38.763318+00:00"
        },
        {
          "scenario_id": "scne62b3eeb5fa9",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "exam_sprint",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763320+00:00"
        },
        {
          "scenario_id": "scnc5dead1f7593",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "exam_sprint",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763321+00:00"
        },
        {
          "scenario_id": "scnd1ca49fe28f1",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "exam_sprint",
            "risk_level": "high"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763322+00:00"
        },
        {
          "scenario_id": "scn898e66fd17d6",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "exam_sprint",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763325+00:00"
        },
        {
          "scenario_id": "scn74a2da248a29",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "exam_sprint",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763326+00:00"
        },
        {
          "scenario_id": "scn3e1c119378c5",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "exam_sprint",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763328+00:00"
        },
        {
          "scenario_id": "scn587db0df2b2d",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "exam_sprint",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763329+00:00"
        }
      ],
      "recommendation": "safe_to_promote"
    },
    "ProjectDeliveryBench": {
      "total": 4,
      "passed": 4,
      "failed": 0,
      "pass_rate": 1.0,
      "reports": [
        {
          "scenario_id": "scn7f95c27d4234",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "project_delivery",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763335+00:00"
        },
        {
          "scenario_id": "scnb8cec9eddb99",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "project_delivery",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763337+00:00"
        },
        {
          "scenario_id": "scnefccb237a1ab",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 2,
            "domain": "project_delivery",
            "risk_level": "high"
          },
          "cost_estimate": {
            "estimated_turns": 3.0
          },
          "latency_estimate": {
            "estimated_seconds": 4.0
          },
          "run_at": "2026-05-02T06:22:38.763338+00:00"
        },
        {
          "scenario_id": "scn10647f4d6261",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "project_delivery",
            "risk_level": "medium"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763340+00:00"
        }
      ],
      "recommendation": "safe_to_promote"
    },
    "JobSearchBench": {
      "total": 4,
      "passed": 4,
      "failed": 0,
      "pass_rate": 1.0,
      "reports": [
        {
          "scenario_id": "scnf46693fb5a4e",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "job_search",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763345+00:00"
        },
        {
          "scenario_id": "scn3abccefc6336",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "job_search",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763347+00:00"
        },
        {
          "scenario_id": "scnabf6a4743f02",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 2,
            "domain": "job_search",
            "risk_level": "high"
          },
          "cost_estimate": {
            "estimated_turns": 3.0
          },
          "latency_estimate": {
            "estimated_seconds": 4.0
          },
          "run_at": "2026-05-02T06:22:38.763348+00:00"
        },
        {
          "scenario_id": "scn4b46f49f9f5f",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "job_search",
            "risk_level": "medium"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763350+00:00"
        }
      ],
      "recommendation": "safe_to_promote"
    },
    "MultiGoalLifeBench": {
      "total": 4,
      "passed": 4,
      "failed": 0,
      "pass_rate": 1.0,
      "reports": [
        {
          "scenario_id": "scn023f82da8b89",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "multi_goal",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763354+00:00"
        },
        {
          "scenario_id": "scn5085bb7053bd",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "multi_goal",
            "risk_level": "low"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763357+00:00"
        },
        {
          "scenario_id": "scn8de6344564f4",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 2,
            "domain": "multi_goal",
            "risk_level": "high"
          },
          "cost_estimate": {
            "estimated_turns": 3.0
          },
          "latency_estimate": {
            "estimated_seconds": 4.0
          },
          "run_at": "2026-05-02T06:22:38.763358+00:00"
        },
        {
          "scenario_id": "scn47262141a6c6",
          "passed": true,
          "violations": [],
          "spine_integrity": true,
          "user_agency_preserved": true,
          "long_term_pollution": false,
          "policy_regression": false,
          "observations": {
            "steps_count": 1,
            "domain": "multi_goal",
            "risk_level": "medium"
          },
          "cost_estimate": {
            "estimated_turns": 1.5
          },
          "latency_estimate": {
            "estimated_seconds": 2.0
          },
          "run_at": "2026-05-02T06:22:38.763360+00:00"
        }
      ],
      "recommendation": "safe_to_promote"
    }
  },
  "reports": [
    {
      "scenario_id": "scne11b0690a42c",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 4,
        "domain": "exam_sprint",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 6.0
      },
      "latency_estimate": {
        "estimated_seconds": 8.0
      },
      "run_at": "2026-05-02T06:22:38.763233+00:00",
      "suite": "ExamSprintBench",
      "scenario_name": "零基础+3天考试",
      "domain": "exam_sprint",
      "category": "regression",
      "risk_level": "low",
      "expected_properties": [
        "detect_crisis_mode",
        "avoid_full_syllabus_plan",
        "create_survival_path",
        "do_not_overpromise",
        "show_user_agency_options"
      ]
    },
    {
      "scenario_id": "scn5628648c684e",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 2,
        "domain": "exam_sprint",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 3.0
      },
      "latency_estimate": {
        "estimated_seconds": 4.0
      },
      "run_at": "2026-05-02T06:22:38.763246+00:00",
      "suite": "ExamSprintBench",
      "scenario_name": "7天冲刺+噪声资料",
      "domain": "exam_sprint",
      "category": "regression",
      "risk_level": "low",
      "expected_properties": [
        "do_not_overpromise",
        "spine_integrity"
      ]
    },
    {
      "scenario_id": "scn9b48b62e2ea4",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "exam_sprint",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763250+00:00",
      "suite": "ExamSprintBench",
      "scenario_name": "用户明确要求按课件讲",
      "domain": "exam_sprint",
      "category": "boundary",
      "risk_level": "low",
      "expected_properties": [
        "user_agency_preserved"
      ]
    },
    {
      "scenario_id": "scn1af48d591572",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "exam_sprint",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763253+00:00",
      "suite": "ExamSprintBench",
      "scenario_name": "通用概念不触发全量RAG",
      "domain": "exam_sprint",
      "category": "boundary",
      "risk_level": "low",
      "expected_properties": [
        "do_not_overpromise"
      ]
    },
    {
      "scenario_id": "scn0e7a463524c8",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 2,
        "domain": "exam_sprint",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 3.0
      },
      "latency_estimate": {
        "estimated_seconds": 4.0
      },
      "run_at": "2026-05-02T06:22:38.763256+00:00",
      "suite": "ExamSprintBench",
      "scenario_name": "连续失败+纠正系统",
      "domain": "exam_sprint",
      "category": "safety",
      "risk_level": "low",
      "expected_properties": [
        "user_agency_preserved",
        "spine_integrity"
      ]
    },
    {
      "scenario_id": "scne62b3eeb5fa9",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "exam_sprint",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763260+00:00",
      "suite": "ExamSprintBench",
      "scenario_name": "七连胜但小测下降",
      "domain": "exam_sprint",
      "category": "regression",
      "risk_level": "low",
      "expected_properties": [
        "spine_integrity"
      ]
    },
    {
      "scenario_id": "scnc5dead1f7593",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "exam_sprint",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763261+00:00",
      "suite": "ExamSprintBench",
      "scenario_name": "七连胜但任务超时",
      "domain": "exam_sprint",
      "category": "regression",
      "risk_level": "low",
      "expected_properties": [
        "spine_integrity"
      ]
    },
    {
      "scenario_id": "scnd1ca49fe28f1",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "exam_sprint",
        "risk_level": "high"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763264+00:00",
      "suite": "ExamSprintBench",
      "scenario_name": "考前24h想开新章节",
      "domain": "exam_sprint",
      "category": "safety",
      "risk_level": "high",
      "expected_properties": [
        "detect_crisis_mode",
        "avoid_full_syllabus_plan",
        "do_not_overpromise"
      ]
    },
    {
      "scenario_id": "scn898e66fd17d6",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "exam_sprint",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763267+00:00",
      "suite": "ExamSprintBench",
      "scenario_name": "用户说'你没懂我'",
      "domain": "exam_sprint",
      "category": "safety",
      "risk_level": "low",
      "expected_properties": [
        "user_agency_preserved",
        "spine_integrity"
      ]
    },
    {
      "scenario_id": "scn74a2da248a29",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "exam_sprint",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763269+00:00",
      "suite": "ExamSprintBench",
      "scenario_name": "用户长期回归",
      "domain": "exam_sprint",
      "category": "regression",
      "risk_level": "low",
      "expected_properties": [
        "spine_integrity",
        "no_long_term_pollution"
      ]
    },
    {
      "scenario_id": "scn3e1c119378c5",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "exam_sprint",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763271+00:00",
      "suite": "ExamSprintBench",
      "scenario_name": "状态降级场景",
      "domain": "exam_sprint",
      "category": "boundary",
      "risk_level": "low",
      "expected_properties": [
        "spine_integrity"
      ]
    },
    {
      "scenario_id": "scn587db0df2b2d",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "exam_sprint",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763273+00:00",
      "suite": "ExamSprintBench",
      "scenario_name": "多目标冲突",
      "domain": "exam_sprint",
      "category": "boundary",
      "risk_level": "low",
      "expected_properties": [
        "show_user_agency_options",
        "spine_integrity"
      ]
    },
    {
      "scenario_id": "scn7f95c27d4234",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "project_delivery",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763275+00:00",
      "suite": "ProjectDeliveryBench",
      "scenario_name": "项目交付+模糊需求",
      "domain": "project_delivery",
      "category": "regression",
      "risk_level": "low",
      "expected_properties": [
        "spine_integrity",
        "do_not_overpromise"
      ]
    },
    {
      "scenario_id": "scnb8cec9eddb99",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "project_delivery",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763277+00:00",
      "suite": "ProjectDeliveryBench",
      "scenario_name": "项目交付+多里程碑",
      "domain": "project_delivery",
      "category": "regression",
      "risk_level": "low",
      "expected_properties": [
        "spine_integrity"
      ]
    },
    {
      "scenario_id": "scnefccb237a1ab",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 2,
        "domain": "project_delivery",
        "risk_level": "high"
      },
      "cost_estimate": {
        "estimated_turns": 3.0
      },
      "latency_estimate": {
        "estimated_seconds": 4.0
      },
      "run_at": "2026-05-02T06:22:38.763278+00:00",
      "suite": "ProjectDeliveryBench",
      "scenario_name": "项目交付+临期改需求",
      "domain": "project_delivery",
      "category": "safety",
      "risk_level": "high",
      "expected_properties": [
        "spine_integrity",
        "do_not_overpromise",
        "show_user_agency_options"
      ]
    },
    {
      "scenario_id": "scn10647f4d6261",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "project_delivery",
        "risk_level": "medium"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763280+00:00",
      "suite": "ProjectDeliveryBench",
      "scenario_name": "项目交付+协作者失联",
      "domain": "project_delivery",
      "category": "boundary",
      "risk_level": "medium",
      "expected_properties": [
        "spine_integrity",
        "show_user_agency_options"
      ]
    },
    {
      "scenario_id": "scnf46693fb5a4e",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "job_search",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763282+00:00",
      "suite": "JobSearchBench",
      "scenario_name": "求职面试准备",
      "domain": "job_search",
      "category": "regression",
      "risk_level": "low",
      "expected_properties": [
        "spine_integrity",
        "show_user_agency_options"
      ]
    },
    {
      "scenario_id": "scn3abccefc6336",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "job_search",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763284+00:00",
      "suite": "JobSearchBench",
      "scenario_name": "求职+技能缺口",
      "domain": "job_search",
      "category": "regression",
      "risk_level": "low",
      "expected_properties": [
        "spine_integrity"
      ]
    },
    {
      "scenario_id": "scnabf6a4743f02",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 2,
        "domain": "job_search",
        "risk_level": "high"
      },
      "cost_estimate": {
        "estimated_turns": 3.0
      },
      "latency_estimate": {
        "estimated_seconds": 4.0
      },
      "run_at": "2026-05-02T06:22:38.763285+00:00",
      "suite": "JobSearchBench",
      "scenario_name": "求职+连续被拒",
      "domain": "job_search",
      "category": "safety",
      "risk_level": "high",
      "expected_properties": [
        "spine_integrity",
        "user_agency_preserved",
        "no_long_term_pollution"
      ]
    },
    {
      "scenario_id": "scn4b46f49f9f5f",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "job_search",
        "risk_level": "medium"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763288+00:00",
      "suite": "JobSearchBench",
      "scenario_name": "求职+面试爽约风险",
      "domain": "job_search",
      "category": "boundary",
      "risk_level": "medium",
      "expected_properties": [
        "spine_integrity",
        "do_not_overpromise",
        "show_user_agency_options"
      ]
    },
    {
      "scenario_id": "scn023f82da8b89",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "multi_goal",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763290+00:00",
      "suite": "MultiGoalLifeBench",
      "scenario_name": "多目标+健身+考试",
      "domain": "multi_goal",
      "category": "regression",
      "risk_level": "low",
      "expected_properties": [
        "spine_integrity",
        "show_user_agency_options"
      ]
    },
    {
      "scenario_id": "scn5085bb7053bd",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "multi_goal",
        "risk_level": "low"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763291+00:00",
      "suite": "MultiGoalLifeBench",
      "scenario_name": "多目标+工作+学习",
      "domain": "multi_goal",
      "category": "regression",
      "risk_level": "low",
      "expected_properties": [
        "spine_integrity"
      ]
    },
    {
      "scenario_id": "scn8de6344564f4",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 2,
        "domain": "multi_goal",
        "risk_level": "high"
      },
      "cost_estimate": {
        "estimated_turns": 3.0
      },
      "latency_estimate": {
        "estimated_seconds": 4.0
      },
      "run_at": "2026-05-02T06:22:38.763293+00:00",
      "suite": "MultiGoalLifeBench",
      "scenario_name": "多目标+过载疲劳",
      "domain": "multi_goal",
      "category": "safety",
      "risk_level": "high",
      "expected_properties": [
        "spine_integrity",
        "user_agency_preserved",
        "show_user_agency_options"
      ]
    },
    {
      "scenario_id": "scn47262141a6c6",
      "passed": true,
      "violations": [],
      "spine_integrity": true,
      "user_agency_preserved": true,
      "long_term_pollution": false,
      "policy_regression": false,
      "observations": {
        "steps_count": 1,
        "domain": "multi_goal",
        "risk_level": "medium"
      },
      "cost_estimate": {
        "estimated_turns": 1.5
      },
      "latency_estimate": {
        "estimated_seconds": 2.0
      },
      "run_at": "2026-05-02T06:22:38.763295+00:00",
      "suite": "MultiGoalLifeBench",
      "scenario_name": "多目标+临时家庭事务",
      "domain": "multi_goal",
      "category": "boundary",
      "risk_level": "medium",
      "expected_properties": [
        "spine_integrity",
        "show_user_agency_options"
      ]
    }
  ],
  "cost_estimate": {
    "estimated_turns": 48.0
  },
  "latency_estimate": {
    "estimated_seconds": 64.0
  },
  "generated_at": "2026-05-02T06:22:38.763432+00:00",
  "commit": "local-fv03-final",
  "markdown_path": null,
  "simulation_run_id": null
}
```
