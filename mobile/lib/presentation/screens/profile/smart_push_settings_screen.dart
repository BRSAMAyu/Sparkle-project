import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/user_model.dart';
import 'package:sparkle/data/repositories/user_repository.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:logger/logger.dart';

class SmartPushSettingsScreen extends ConsumerStatefulWidget {
  const SmartPushSettingsScreen({super.key});

  @override
  ConsumerState<SmartPushSettingsScreen> createState() => _SmartPushSettingsScreenState();
}

class _SmartPushSettingsScreenState extends ConsumerState<SmartPushSettingsScreen> {
  final Logger _logger = Logger();
  
  // Local state
  String _persona = 'coach';
  int _dailyCap = 5;
  List<Map<String, String>> _activeSlots = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    // Initialize state from current user
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadPreferences();
    });
  }

  void _loadPreferences() {
    final user = ref.read(authProvider).user;
    if (user != null && user.pushPreferences != null) {
      final prefs = user.pushPreferences!;
      setState(() {
        _persona = prefs.personaType;
        _dailyCap = prefs.dailyCap;
        _activeSlots = List.from(prefs.activeSlots ?? []);
      });
    }
  }

  Future<void> _savePreferences() async {
    setState(() => _isLoading = true);
    try {
      final prefs = PushPreferences(
        personaType: _persona,
        dailyCap: _dailyCap,
        activeSlots: _activeSlots,
        timezone: 'Asia/Shanghai', // TODO: Get from device
      );

      await ref.read(userRepositoryProvider).updatePushPreferences(prefs);
      
      // Force refresh user profile to update state
      // Assuming authProvider has a refresh method or we just rely on the updated user return
      // Ideally ref.read(authProvider.notifier).updateUser(updatedUser);
      // For now just show success
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('设置已保存')),
        );
      }
    } catch (e) {
      _logger.e('Failed to save push settings: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('保存失败: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _selectTime(int index, bool isStart) async {
    final currentStr = isStart ? _activeSlots[index]['start'] : _activeSlots[index]['end'];
    final parts = currentStr?.split(':') ?? ['08', '00'];
    final initialTime = TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1]));

    final picked = await showTimePicker(
      context: context,
      initialTime: initialTime,
    );

    if (picked != null) {
      setState(() {
        final formatted = '${picked.hour.toString().padLeft(2, '0')}:${picked.minute.toString().padLeft(2, '0')}';
        if (isStart) {
          _activeSlots[index]['start'] = formatted;
        } else {
          _activeSlots[index]['end'] = formatted;
        }
      });
    }
  }

  void _addSlot() {
    setState(() {
      _activeSlots.add({'start': '09:00', 'end': '10:00'});
    });
  }

  void _removeSlot(int index) {
    setState(() {
      _activeSlots.removeAt(index);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('智能推送设置'),
        actions: [
          if (_isLoading)
            const Center(child: Padding(
              padding: EdgeInsets.only(right: 16.0),
              child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)),
            ),)
          else
            IconButton(
              icon: const Icon(Icons.save),
              onPressed: _savePreferences,
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          _buildSectionTitle('角色设定 (Persona)'),
          const SizedBox(height: DS.sm),
          _buildPersonaSelector(),
          
          const SizedBox(height: DS.xl),
          _buildSectionTitle('频控设置 (每日上限)'),
          _buildFrequencySlider(),
          
          const SizedBox(height: DS.xl),
          _buildSectionTitle('活跃时间段 (Active Slots)'),
          const Text(
            '仅在这些时间段内发送推送，避开休息时间。',
            style: TextStyle(color: DS.brandPrimary, fontSize: 12),
          ),
          const SizedBox(height: DS.sm),
          _buildActiveSlotsList(),
          const SizedBox(height: DS.sm),
          ElevatedButton.icon(
            onPressed: _addSlot,
            icon: const Icon(Icons.add),
            label: const Text('添加时间段'),
          ),

          const SizedBox(height: 40),
          const Divider(),
          Center(
            child: TextButton.icon(
              onPressed: () {
                ref.read(notificationServiceProvider).showSmartPush(
                  title: '⚡ 调试：记忆临界点',
                  body: '你的 [线性代数] 正在遗忘，点击立即复习！',
                  payload: {'taskId': 'debug_123'},
                );
                ScaffoldMessenger.of(context).showSnackBar(
                   const SnackBar(content: Text('测试通知已发送 (需退回桌面查看)')),
                );
              },
              icon: const Icon(Icons.bug_report, color: DS.brandPrimary),
              label: const Text('发送测试通知 (Dev)', style: TextStyle(color: DS.brandPrimary)),
            ),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Text(
      title,
      style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
    );
  }

  Widget _buildPersonaSelector() {
    return Row(
      children: [
        Expanded(
          child: _buildPersonaChip(
            value: 'coach',
            label: '严厉教练',
            icon: Icons.sports_kabaddi,
            description: '督促、强调纪律',
          ),
        ),
        const SizedBox(width: DS.md),
        Expanded(
          child: _buildPersonaChip(
            value: 'anime',
            label: '二次元助手',
            icon: Icons.face_retouching_natural,
            description: '温柔、卖萌鼓励',
          ),
        ),
      ],
    );
  }

  Widget _buildPersonaChip({
    required String value,
    required String label,
    required IconData icon,
    required String description,
  }) {
    final isSelected = _persona == value;
    final colorScheme = Theme.of(context).colorScheme;
    
    return InkWell(
      onTap: () => setState(() => _persona = value),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: isSelected ? colorScheme.primaryContainer : colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
          border: isSelected ? Border.all(color: colorScheme.primary, width: 2) : null,
        ),
        child: Column(
          children: [
            Icon(icon, color: isSelected ? colorScheme.primary : colorScheme.onSurfaceVariant),
            const SizedBox(height: DS.sm),
            Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: DS.xs),
            Text(
              description,
              style: TextStyle(fontSize: 10, color: colorScheme.onSurfaceVariant),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFrequencySlider() {
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text('3条/天'),
            Text('$_dailyCap条', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            const Text('10条/天'),
          ],
        ),
        Slider(
          value: _dailyCap.toDouble(),
          min: 3,
          max: 10,
          divisions: 7,
          label: '$_dailyCap 条',
          onChanged: (val) => setState(() => _dailyCap = val.toInt()),
        ),
      ],
    );
  }

  Widget _buildActiveSlotsList() {
    if (_activeSlots.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 16.0),
        child: Center(child: Text('暂无设置，建议添加活跃时间')),
      );
    }
    
    return Column(
      children: List.generate(_activeSlots.length, (index) {
        final slot = _activeSlots[index];
        return Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: Padding(
            padding: const EdgeInsets.all(8.0),
            child: Row(
              children: [
                const Icon(Icons.access_time, size: 20),
                const SizedBox(width: DS.md),
                Expanded(
                  child: Row(
                    children: [
                      _buildTimeButton(slot['start'] ?? '00:00', index, true),
                      const Padding(
                        padding: EdgeInsets.symmetric(horizontal: 8.0),
                        child: Text('-'),
                      ),
                      _buildTimeButton(slot['end'] ?? '00:00', index, false),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.delete, color: DS.errorAccent),
                  onPressed: () => _removeSlot(index),
                ),
              ],
            ),
          ),
        );
      }),
    );
  }

  Widget _buildTimeButton(String time, int index, bool isStart) {
    return InkWell(
      onTap: () => _selectTime(index, isStart),
      borderRadius: BorderRadius.circular(4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          border: Border.all(color: DS.brandPrimary.shade400),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          time,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
        ),
      ),
    );
  }
}
