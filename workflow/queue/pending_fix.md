# Pending Fix Queue (FIFO, P0 → P1 → P2)

- ISSUE-20260424-064 P1 NotificationPushService bypasses user preferences (notification_push_service.py:33-75)
- ISSUE-20260424-065 P1 calendar reminder_minutes stored but never consumed (calendar.py:146)
- ISSUE-20260424-058 P1 after_commit fire-and-forget (achievement_engine.py:68)
- ISSUE-20260424-059 P1 WEEKEND_WARRIOR unbounded queries (achievement_engine.py:699-733)
- ISSUE-20260424-060 P1 get_close_to_unlock N+1 evaluation (achievement_engine.py:2047-2131)
- ISSUE-20260424-046 P1 AnalyzeError gRPC fire-and-forget
- ISSUE-20260424-061 P2 AchievementEventConsumer consumer_name timestamp
- ISSUE-20260424-062 P2 ContractService.update_daily_progress no day guard
- ISSUE-20260424-063 P2 check_daily_first TOCTOU race
- ISSUE-20260424-066 P2 _get_trends N+1 daily queries (notification_analytics_service.py:365-472)
- ISSUE-20260424-067 P2 _get_hourly_distribution no time filter (notification_analytics_service.py:486-489)
- ISSUE-20260424-068 P2 _find_notification_for_record full table scan (notification_center_service.py:1115-1132)
- ISSUE-20260424-069 P2 batch_operations no EventBus events (calendar.py:298-387)
- ISSUE-20260424-047 P2 ErrorReplanBridge unbounded query
- ISSUE-20260424-048 P2 list_errors LIKE wildcards not escaped
- ISSUE-20260424-049 P2 delete_error missing is_deleted filter
- ISSUE-20260424-050 P2 submit_review read-modify-write race
- ISSUE-20260424-051 P2 _get_cohort_profile bare except
