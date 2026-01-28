import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/chat/data/services/review_grpc_service.dart';

/// Arbitration priority options
enum ArbitrationPriority {
  low('low', '低', Colors.grey),
  normal('normal', '正常', Colors.blue),
  high('high', '高', Colors.orange),
  urgent('urgent', '紧急', Colors.red);

  const ArbitrationPriority(this.value, this.label, this.color);
  final String value;
  final String label;
  final Color color;

  static ArbitrationPriority fromString(String value) => values.firstWhere(
      (p) => p.value == value,
      orElse: () => normal,
    );
}

/// Escalation reason options
enum EscalationReason {
  scoreDiscrepancy('score_discrepancy', '分数差异大'),
  lowConfidence('low_confidence', '置信度低'),
  userEscalation('user_escalation', '用户请求'),
  repeatAppeal('repeat_appeal', '重复申诉'),
  sensitiveContent('sensitive_content', '敏感内容'),
  policyViolation('policy_violation', '政策违规'),
  systemError('system_error', '系统错误');

  const EscalationReason(this.value, this.label);
  final String value;
  final String label;

  static EscalationReason fromString(String value) => values.firstWhere(
      (r) => r.value == value,
      orElse: () => lowConfidence,
    );
}

/// Appeal decision options
enum AppealDecision {
  approved('approved', '通过申诉', Colors.green),
  rejected('rejected', '拒绝申诉', Colors.red),
  partiallyApproved('partially_approved', '部分通过', Colors.orange),
  escalated('escalated', '进一步升级', Colors.purple);

  const AppealDecision(this.value, this.label, this.color);
  final String value;
  final String label;
  final Color color;
}

/// Arbitration case data model
class ArbitrationCase {
  const ArbitrationCase({
    required this.caseId,
    required this.appealId,
    required this.reviewId,
    required this.userId,
    required this.escalationReason,
    required this.priority,
    required this.createdAt,
    this.status = 'pending',
    this.assignedTo,
    this.assignedAt,
    this.originalReviewScore = 0.0,
    this.secondaryReviewScore,
    this.scoreDiscrepancy = 0.0,
    this.resolution,
    this.finalDecision,
    this.resolvedAt,
    this.resolvedBy,
    this.notes = const [],
    this.evidence = const {},
  });

  factory ArbitrationCase.fromJson(Map<String, dynamic> json) => ArbitrationCase(
      caseId: json['case_id'] as String? ?? '',
      appealId: json['appeal_id'] as String? ?? '',
      reviewId: json['review_id'] as String? ?? '',
      userId: json['user_id'] as String? ?? '',
      escalationReason: EscalationReason.fromString(
        json['escalation_reason'] as String? ?? 'low_confidence',
      ),
      priority: ArbitrationPriority.fromString(
        json['priority'] as String? ?? 'normal',
      ),
      createdAt: json['created_at'] as String? ?? '',
      status: json['status'] as String? ?? 'pending',
      assignedTo: json['assigned_to'] as String?,
      assignedAt: json['assigned_at'] as String?,
      originalReviewScore:
          (json['original_review_score'] as num?)?.toDouble() ?? 0.0,
      secondaryReviewScore: (json['secondary_review_score'] as num?)?.toDouble(),
      scoreDiscrepancy:
          (json['score_discrepancy'] as num?)?.toDouble() ?? 0.0,
      resolution: json['resolution'] as String?,
      finalDecision: json['final_decision'] as String?,
      resolvedAt: json['resolved_at'] as String?,
      resolvedBy: json['resolved_by'] as String?,
      notes: (json['notes'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      evidence: json['evidence'] as Map<String, dynamic>? ?? {},
    );

  final String caseId;
  final String appealId;
  final String reviewId;
  final String userId;
  final EscalationReason escalationReason;
  final ArbitrationPriority priority;
  final String createdAt;
  final String status;
  final String? assignedTo;
  final String? assignedAt;
  final double originalReviewScore;
  final double? secondaryReviewScore;
  final double scoreDiscrepancy;
  final String? resolution;
  final String? finalDecision;
  final String? resolvedAt;
  final String? resolvedBy;
  final List<String> notes;
  final Map<String, dynamic> evidence;

  bool get isPending => status == 'pending';
  bool get isAssigned => status == 'assigned';
  bool get isInReview => status == 'in_review';
  bool get isResolved => status == 'resolved';
}

/// Arbitration queue statistics
class ArbitrationQueueStats {
  const ArbitrationQueueStats({
    required this.totalPending,
    required this.totalAssigned,
    required this.totalInReview,
    required this.totalResolvedToday,
    required this.avgResolutionTimeHours,
    this.byPriority = const {},
    this.byReason = const {},
  });

  factory ArbitrationQueueStats.fromJson(Map<String, dynamic> json) => ArbitrationQueueStats(
      totalPending: json['total_pending'] as int? ?? 0,
      totalAssigned: json['total_assigned'] as int? ?? 0,
      totalInReview: json['total_in_review'] as int? ?? 0,
      totalResolvedToday: json['total_resolved_today'] as int? ?? 0,
      avgResolutionTimeHours:
          (json['avg_resolution_time_hours'] as num?)?.toDouble() ?? 0.0,
      byPriority: (json['by_priority'] as Map<String, dynamic>?)
              ?.map((k, v) => MapEntry(k, v as int)) ??
          {},
      byReason: (json['by_reason'] as Map<String, dynamic>?)
              ?.map((k, v) => MapEntry(k, v as int)) ??
          {},
    );

  final int totalPending;
  final int totalAssigned;
  final int totalInReview;
  final int totalResolvedToday;
  final double avgResolutionTimeHours;
  final Map<String, int> byPriority;
  final Map<String, int> byReason;
}

/// Appeal Dashboard - Admin interface for managing appeals
class AppealDashboard extends ConsumerStatefulWidget {
  const AppealDashboard({super.key});

  @override
  ConsumerState<AppealDashboard> createState() => _AppealDashboardState();
}

class _AppealDashboardState extends ConsumerState<AppealDashboard> {
  // State
  ArbitrationQueueStats? _stats;
  List<ArbitrationCase> _cases = [];
  bool _isLoading = true;
  String? _error;
  ArbitrationCase? _selectedCase;

  // Filters
  ArbitrationPriority? _priorityFilter;
  String _statusFilter = 'pending'; // pending, assigned, in_review, resolved

  // Refresh
  Timer? _refreshTimer;

  // gRPC service
  ReviewGrpcService? _reviewService;

  /// Get current admin ID from auth state
  String get _currentAdminId {
    final authState = ref.read(authProvider);
    final user = authState.user;
    if (user?.id != null && user!.id.isNotEmpty) {
      return user.id;
    }
    // Fallback to a default admin ID if user not authenticated
    return 'admin_system';
  }

  @override
  void initState() {
    super.initState();
    _loadData();
    // Auto-refresh every 30 seconds
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _loadStats(),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadData() async {
    await Future.wait([
      _loadStats(),
      _loadCases(),
    ]);
  }

  Future<void> _loadStats() async {
    try {
      _reviewService ??= ReviewGrpcService();

      final result = await _reviewService!.getArbitrationQueueStats();

      setState(() {
        if (result.success) {
          _stats = ArbitrationQueueStats(
            totalPending: result.totalPending,
            totalAssigned: result.totalAssigned,
            totalInReview: result.totalInReview,
            totalResolvedToday: result.totalResolvedToday,
            avgResolutionTimeHours: result.avgResolutionTimeHours,
            byPriority: result.byPriority,
            byReason: result.byReason,
          );
        }
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _loadCases() async {
    try {
      _reviewService ??= ReviewGrpcService();

      final result = await _reviewService!.getArbitrationQueue(
        priorityFilter: _priorityFilter?.value,
        statusFilter: _statusFilter == 'pending'
            ? 'pending'
            : _statusFilter == 'assigned'
                ? 'assigned'
                : _statusFilter == 'resolved'
                    ? 'resolved'
                    : null,
      );

      if (result.success && result.cases.isNotEmpty) {
        setState(() {
          _cases = result.cases.map((info) => ArbitrationCase(
              caseId: info.caseId,
              appealId: info.appealId,
              reviewId: info.reviewId,
              userId: info.userId,
              escalationReason: EscalationReason.fromString(info.escalationReason),
              priority: ArbitrationPriority.fromString(info.priority),
              createdAt: info.createdAt,
              status: info.status,
              assignedTo: info.assignedTo,
              assignedAt: info.assignedAt,
              originalReviewScore: info.originalReviewScore,
              secondaryReviewScore: info.secondaryReviewScore,
              scoreDiscrepancy: info.scoreDiscrepancy,
              resolution: info.resolution,
              finalDecision: info.finalDecision,
              resolvedAt: info.resolvedAt,
              resolvedBy: info.resolvedBy,
              notes: info.notes,
            ),).toList();
        });
      } else {
        // Fallback to empty list when no cases available
        setState(() {
          _cases = [];
        });
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
      });
    }
  }

  Future<void> _assignCase(String caseId) async {
    try {
      _reviewService ??= ReviewGrpcService();

      final result = await _reviewService!.assignArbitrationCase(
        caseId: caseId,
        arbitratorId: _currentAdminId,
        arbitratorRole: 'admin',
      );

      if (result.success) {
        // Refresh cases after assignment
        await _loadCases();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(result.message ?? '案件已分配'),
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(result.message ?? '分配失败'),
              backgroundColor: Colors.red,
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('分配失败: $e'),
            backgroundColor: Colors.red,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  Future<void> _submitDecision(
    String caseId,
    AppealDecision decision,
    String explanation,
  ) async {
    try {
      _reviewService ??= ReviewGrpcService();

      final result = await _reviewService!.submitArbitrationDecision(
        caseId: caseId,
        decision: decision.value,
        explanation: explanation,
        arbitratorId: _currentAdminId,
        arbitratorRole: 'admin',
      );

      if (result.success) {
        setState(() {
          _selectedCase = null;
        });
        // Refresh data after submission
        await _loadCases();
        await _loadStats();

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(result.message ?? '决策已提交: ${decision.label}'),
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(result.message ?? '提交失败'),
              backgroundColor: Colors.red,
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('提交失败: $e'),
            backgroundColor: Colors.red,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  List<ArbitrationCase> get _filteredCases => _cases.where((c) {
      if (_priorityFilter != null && c.priority != _priorityFilter) {
        return false;
      }
      if (_statusFilter == 'pending' && !c.isPending) return false;
      if (_statusFilter == 'assigned' && !c.isAssigned && !c.isInReview) {
        return false;
      }
      if (_statusFilter == 'resolved' && !c.isResolved) return false;
      return true;
    }).toList();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (_isLoading) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    if (_error != null) {
      return Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 48, color: Colors.red),
              const SizedBox(height: 16),
              Text('加载失败: $_error'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _loadData,
                child: const Text('重试'),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('申诉仲裁管理'),
        actions: [
          IconButton(
            onPressed: _loadData,
            icon: const Icon(Icons.refresh),
            tooltip: '刷新',
          ),
        ],
      ),
      body: Row(
        children: [
          // Sidebar with stats
          _buildStatsSidebar(theme),
          const VerticalDivider(width: 1),
          // Main content
          Expanded(
            child: _selectedCase != null
                ? _buildCaseDetail(theme)
                : _buildCasesList(theme),
          ),
        ],
      ),
    );
  }

  Widget _buildStatsSidebar(ThemeData theme) {
    final stats = _stats;
    if (stats == null) return const SizedBox.shrink();

    return Container(
      width: 280,
      color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.3),
      child: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '队列统计',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  '今日已解决: ${stats.totalResolvedToday}',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
          const Divider(height: 1),

          // Stats cards
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _buildStatCard(
                  theme: theme,
                  label: '待分配',
                  value: stats.totalPending.toString(),
                  color: Colors.orange,
                  icon: Icons.inbox,
                ),
                const SizedBox(height: 12),
                _buildStatCard(
                  theme: theme,
                  label: '处理中',
                  value: (stats.totalAssigned + stats.totalInReview).toString(),
                  color: Colors.blue,
                  icon: Icons.pending,
                ),
                const SizedBox(height: 12),
                _buildStatCard(
                  theme: theme,
                  label: '平均处理时间',
                  value: '${stats.avgResolutionTimeHours.toStringAsFixed(1)}h',
                  color: Colors.green,
                  icon: Icons.schedule,
                ),

                const SizedBox(height: 24),

                // By priority breakdown
                Text(
                  '按优先级',
                  style: theme.textTheme.labelMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 8),
                ...ArbitrationPriority.values.map((p) {
                  final count = stats.byPriority[p.value] ?? 0;
                  if (count == 0) return const SizedBox.shrink();
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Row(
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            color: p.color,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(child: Text(p.label)),
                        Text(count.toString()),
                      ],
                    ),
                  );
                }),

                const SizedBox(height: 16),

                // By reason breakdown
                Text(
                  '按原因',
                  style: theme.textTheme.labelMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 8),
                ...stats.byReason.entries.map((entry) {
                  final reason = EscalationReason.fromString(entry.key);
                  final count = entry.value;
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Row(
                      children: [
                        const SizedBox(width: 8),
                        Expanded(child: Text(reason.label)),
                        Text(count.toString()),
                      ],
                    ),
                  );
                }),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatCard({
    required ThemeData theme,
    required String label,
    required String value,
    required Color color,
    required IconData icon,
  }) => Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: color.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                Text(
                  value,
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );

  Widget _buildCasesList(ThemeData theme) {
    final cases = _filteredCases;

    return Column(
      children: [
        // Filters
        Container(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              // Status filter
              SegmentedButton<String>(
                segments: const [
                  ButtonSegment(
                    value: 'pending',
                    label: Text('待分配'),
                  ),
                  ButtonSegment(
                    value: 'assigned',
                    label: Text('处理中'),
                  ),
                  ButtonSegment(
                    value: 'resolved',
                    label: Text('已解决'),
                  ),
                ],
                selected: {_statusFilter},
                onSelectionChanged: (Set<String> selected) {
                  setState(() {
                    _statusFilter = selected.first;
                  });
                },
              ),
              const SizedBox(width: 16),
              // Priority filter
              FilterChip(
                label: const Text('优先级'),
                selected: _priorityFilter != null,
                onSelected: (selected) {
                  // Show priority menu
                  _showPriorityMenu(context);
                },
              ),
            ],
          ),
        ),

        const Divider(height: 1),

        // Cases list
        Expanded(
          child: cases.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.inbox,
                        size: 48,
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        '没有案件',
                        style: theme.textTheme.bodyLarge?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                )
              : ListView.builder(
                  itemCount: cases.length,
                  itemBuilder: (context, index) {
                    final caseData = cases[index];
                    return _buildCaseCard(theme, caseData);
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildCaseCard(ThemeData theme, ArbitrationCase caseData) => Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: InkWell(
        onTap: () {
          setState(() {
            _selectedCase = caseData;
          });
        },
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              // Priority indicator
              Container(
                width: 4,
                height: 60,
                decoration: BoxDecoration(
                  color: caseData.priority.color,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const SizedBox(width: 12),

              // Case info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          '案件 #${caseData.caseId}',
                          style: theme.textTheme.labelLarge?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(width: 8),
                        _buildStatusChip(theme, caseData),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      caseData.escalationReason.label,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Icon(
                          Icons.star_border,
                          size: 14,
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          '原评分: ${(caseData.originalReviewScore * 100).toInt()}%',
                          style: theme.textTheme.bodySmall,
                        ),
                        if (caseData.secondaryReviewScore != null) ...[
                          const SizedBox(width: 12),
                          Icon(
                            Icons.star_border,
                            size: 14,
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            '复评: ${(caseData.secondaryReviewScore! * 100).toInt()}%',
                            style: theme.textTheme.bodySmall,
                          ),
                        ],
                        const Spacer(),
                        Text(
                          _formatTime(caseData.createdAt),
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Icon(
                Icons.chevron_right,
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ],
          ),
        ),
      ),
    );

  Widget _buildStatusChip(ThemeData theme, ArbitrationCase caseData) {
    Color color;
    String label;

    if (caseData.isPending) {
      color = Colors.orange;
      label = '待分配';
    } else if (caseData.isAssigned || caseData.isInReview) {
      color = Colors.blue;
      label = '处理中';
    } else {
      color = Colors.green;
      label = '已解决';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: theme.textTheme.labelSmall?.copyWith(
          color: color,
          fontSize: 10,
        ),
      ),
    );
  }

  Widget _buildCaseDetail(ThemeData theme) {
    final caseData = _selectedCase;
    if (caseData == null) return const SizedBox.shrink();

    return Column(
      children: [
        // Header with back button
        Container(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              IconButton(
                onPressed: () {
                  setState(() {
                    _selectedCase = null;
                  });
                },
                icon: const Icon(Icons.arrow_back),
              ),
              Expanded(
                child: Text(
                  '案件 #${caseData.caseId}',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              if (caseData.isPending)
                FilledButton.icon(
                  onPressed: () => _assignCase(caseData.caseId),
                  icon: const Icon(Icons.person_add, size: 18),
                  label: const Text('分配给我'),
                ),
            ],
          ),
        ),
        const Divider(height: 1),

        // Case details
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Priority and status
                Row(
                  children: [
                    _buildDetailChip(
                      theme: theme,
                      label: caseData.priority.label,
                      color: caseData.priority.color,
                      icon: Icons.flag,
                    ),
                    const SizedBox(width: 8),
                    _buildDetailChip(
                      theme: theme,
                      label: caseData.escalationReason.label,
                      color: Colors.blue,
                      icon: Icons.info_outline,
                    ),
                  ],
                ),

                const SizedBox(height: 24),

                // Scores
                Text(
                  '审查分数对比',
                  style: theme.textTheme.labelLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: _buildScoreCard(
                        theme: theme,
                        label: '原审查',
                        score: caseData.originalReviewScore,
                      ),
                    ),
                    const SizedBox(width: 16),
                    if (caseData.secondaryReviewScore != null)
                      Expanded(
                        child: _buildScoreCard(
                          theme: theme,
                          label: '二次审查',
                          score: caseData.secondaryReviewScore!,
                        ),
                      ),
                  ],
                ),

                if (caseData.scoreDiscrepancy > 0.1) ...[
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.orange.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.warning, size: 16, color: Colors.orange),
                        const SizedBox(width: 8),
                        Text(
                          '分数差异: ${(caseData.scoreDiscrepancy * 100).toInt()}%',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: Colors.orange,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],

                const SizedBox(height: 24),

                // Appeal information
                Text(
                  '申诉信息',
                  style: theme.textTheme.labelLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                _buildInfoRow(theme, '申诉ID', caseData.appealId),
                _buildInfoRow(theme, '审查ID', caseData.reviewId),
                _buildInfoRow(theme, '用户ID', caseData.userId),
                _buildInfoRow(theme, '创建时间', _formatDateTime(caseData.createdAt)),
                if (caseData.assignedTo != null)
                  _buildInfoRow(theme, '分配给', caseData.assignedTo!),

                const SizedBox(height: 24),

                // Notes
                if (caseData.notes.isNotEmpty) ...[
                  Text(
                    '备注',
                    style: theme.textTheme.labelLarge?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 8),
                  ...caseData.notes.map((note) => Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Text(
                        note,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ),),
                  const SizedBox(height: 16),
                ],

                // Decision section
                if (!caseData.isResolved) ...[
                  Text(
                    '仲裁决策',
                    style: theme.textTheme.labelLarge?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 12),
                  ...AppealDecision.values.map((decision) => Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: FilledButton.tonal(
                        onPressed: () => _showDecisionDialog(
                          caseData.caseId,
                          decision,
                        ),
                        style: FilledButton.styleFrom(
                          backgroundColor: decision.color.withValues(alpha: 0.2),
                          foregroundColor: decision.color,
                        ),
                        child: Row(
                          children: [
                            Icon(_getDecisionIcon(decision), size: 18),
                            const SizedBox(width: 8),
                            Text(decision.label),
                          ],
                        ),
                      ),
                    ),),
                ] else ...[
                  Text(
                    '已解决',
                    style: theme.textTheme.labelLarge?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: Colors.green,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    caseData.resolution ?? '无说明',
                    style: theme.textTheme.bodyMedium,
                  ),
                  if (caseData.resolvedBy != null)
                    _buildInfoRow(theme, '解决者', caseData.resolvedBy!),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildScoreCard({
    required ThemeData theme,
    required String label,
    required double score,
  }) {
    final percentage = (score * 100).toInt();
    final color = percentage >= 70
        ? Colors.green
        : percentage >= 50
            ? Colors.orange
            : Colors.red;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          Text(
            label,
            style: theme.textTheme.labelSmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '$percentage%',
            style: theme.textTheme.headlineMedium?.copyWith(
              color: color,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailChip({
    required ThemeData theme,
    required String label,
    required Color color,
    required IconData icon,
  }) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: color.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 4),
          Text(
            label,
            style: theme.textTheme.labelSmall?.copyWith(
              color: color,
            ),
          ),
        ],
      ),
    );

  Widget _buildInfoRow(ThemeData theme, String label, String value) => Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: theme.textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );

  IconData _getDecisionIcon(AppealDecision decision) {
    switch (decision) {
      case AppealDecision.approved:
        return Icons.check_circle;
      case AppealDecision.rejected:
        return Icons.cancel;
      case AppealDecision.partiallyApproved:
        return Icons.remove_circle_outline;
      case AppealDecision.escalated:
        return Icons.arrow_upward;
    }
  }

  void _showPriorityMenu(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      builder: (context) => SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Padding(
                padding: EdgeInsets.all(16),
                child: Text(
                  '选择优先级',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              ...ArbitrationPriority.values.map((p) => ListTile(
                  leading: Icon(Icons.circle, color: p.color, size: 12),
                  title: Text(p.label),
                  onTap: () {
                    setState(() {
                      if (_priorityFilter == p) {
                        _priorityFilter = null;
                      } else {
                        _priorityFilter = p;
                      }
                    });
                    Navigator.pop(context);
                  },
                  trailing: _priorityFilter == p
                      ? const Icon(Icons.check, color: Colors.green)
                      : null,
                ),),
              ListTile(
                title: const Center(child: Text('清除筛选')),
                onTap: () {
                  setState(() {
                    _priorityFilter = null;
                  });
                  Navigator.pop(context);
                },
              ),
            ],
          ),
        ),
    );
  }

  void _showDecisionDialog(String caseId, AppealDecision decision) {
    final controller = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
          title: Text(decision.label),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: controller,
                maxLines: 4,
                decoration: const InputDecoration(
                  hintText: '请输入决策说明...',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('取消'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(context);
                _submitDecision(caseId, decision, controller.text);
              },
              child: const Text('提交'),
            ),
          ],
        ),
    );
  }

  String _formatTime(String isoTime) {
    final time = DateTime.parse(isoTime);
    final now = DateTime.now();
    final diff = now.difference(time);

    if (diff.inMinutes < 60) {
      return '${diff.inMinutes}分钟前';
    } else if (diff.inHours < 24) {
      return '${diff.inHours}小时前';
    } else {
      return '${diff.inDays}天前';
    }
  }

  String _formatDateTime(String isoTime) {
    final time = DateTime.parse(isoTime);
    return '${time.year}-${time.month.toString().padLeft(2, '0')}-${time.day.toString().padLeft(2, '0')} '
        '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
  }
}
