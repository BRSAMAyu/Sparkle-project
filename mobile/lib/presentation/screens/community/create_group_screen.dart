import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';

class CreateGroupScreen extends ConsumerStatefulWidget {
  const CreateGroupScreen({super.key});

  @override
  ConsumerState<CreateGroupScreen> createState() => _CreateGroupScreenState();
}

class _CreateGroupScreenState extends ConsumerState<CreateGroupScreen> {
  final _formKey = GlobalKey<FormState>();
  
  // Controllers to track changes
  late TextEditingController _nameController;
  late TextEditingController _descController;
  late TextEditingController _tagsController;
  late TextEditingController _goalController;
  
  GroupType _type = GroupType.squad;
  DateTime? _deadline;
  
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController();
    _descController = TextEditingController();
    _tagsController = TextEditingController();
    _goalController = TextEditingController();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descController.dispose();
    _tagsController.dispose();
    _goalController.dispose();
    super.dispose();
  }
  
  bool get _isDirty {
    return _nameController.text.isNotEmpty || 
           _descController.text.isNotEmpty || 
           _tagsController.text.isNotEmpty ||
           _goalController.text.isNotEmpty;
  }

  Future<bool> _onWillPop() async {
    if (!_isDirty || _isSubmitting) return true;
    
    final shouldPop = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Discard Group?'),
        content: const Text('You have unsaved changes. Are you sure you want to discard them?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Keep Editing'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Discard'),
          ),
        ],
      ),
    );
    return shouldPop ?? false;
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    
    // No need to save(), controllers have values
    List<String> focusTags = [];
    if (_tagsController.text.isNotEmpty) {
      focusTags = _tagsController.text.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
    }

    if (_type == GroupType.sprint && _deadline == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a deadline for the sprint group')),
      );
      return;
    }

    setState(() {
      _isSubmitting = true;
    });

    try {
      final groupData = GroupCreate(
        name: _nameController.text.trim(),
        description: _descController.text.trim().isEmpty ? null : _descController.text.trim(),
        type: _type,
        focusTags: focusTags,
        deadline: _deadline,
        sprintGoal: _goalController.text.trim().isEmpty ? null : _goalController.text.trim(),
        maxMembers: 50,
        isPublic: true,
        joinRequiresApproval: false,
      );

      final group = await ref.read(myGroupsProvider.notifier).createGroup(groupData);
      
      if (mounted) {
        // Clear dirty state implicitly by popping success (or setting flag if needed)
        // But popping is enough.
        context.pop(); 
        context.push('/community/groups/${group.id}');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error creating group: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) return;
        final shouldPop = await _onWillPop();
        if (shouldPop && mounted) {
          Navigator.of(context).pop();
        }
      },
      child: Scaffold(
        appBar: AppBar(title: const Text('Create Group')),
        body: SingleChildScrollView(
          padding: const EdgeInsets.all(AppDesignTokens.spacing16),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextFormField(
                  controller: _nameController,
                  decoration: const InputDecoration(
                    labelText: 'Group Name',
                    hintText: 'e.g., Daily Algorithm Squad',
                    border: OutlineInputBorder(),
                  ),
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Please enter a name';
                    }
                    if (value.length < 2) return 'Name too short';
                    return null;
                  },
                ),
                const SizedBox(height: AppDesignTokens.spacing16),
                
                DropdownButtonFormField<GroupType>(
                  initialValue: _type,
                  decoration: const InputDecoration(
                    labelText: 'Group Type',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(
                      value: GroupType.squad,
                      child: Text('Study Squad (Long-term)'),
                    ),
                    DropdownMenuItem(
                      value: GroupType.sprint,
                      child: Text('Sprint Group (Short-term with DDL)'),
                    ),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _type = value!;
                    });
                  },
                ),
                const SizedBox(height: AppDesignTokens.spacing16),
                
                TextFormField(
                  controller: _descController,
                  decoration: const InputDecoration(
                    labelText: 'Description',
                    border: OutlineInputBorder(),
                    alignLabelWithHint: true,
                  ),
                  maxLines: 3,
                ),
                const SizedBox(height: AppDesignTokens.spacing16),
                
                TextFormField(
                  controller: _tagsController,
                  decoration: const InputDecoration(
                    labelText: 'Focus Tags',
                    hintText: 'Separate by comma, e.g., Math, CS, Exam',
                    border: OutlineInputBorder(),
                  ),
                ),
                
                if (_type == GroupType.sprint) ...[
                  const SizedBox(height: AppDesignTokens.spacing16),
                  const Divider(),
                  const SizedBox(height: AppDesignTokens.spacing8),
                  Text('Sprint Settings', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: AppDesignTokens.spacing16),
                  
                  ListTile(
                    title: const Text('Deadline'),
                    subtitle: Text(_deadline == null ? 'Select Date' : _deadline.toString().split(' ')[0]),
                    trailing: const Icon(Icons.calendar_today),
                    tileColor: Colors.grey.shade100,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    onTap: () async {
                      final date = await showDatePicker(
                        context: context,
                        initialDate: DateTime.now().add(const Duration(days: 7)),
                        firstDate: DateTime.now(),
                        lastDate: DateTime.now().add(const Duration(days: 365)),
                      );
                      if (date != null) {
                        setState(() {
                          _deadline = date;
                        });
                      }
                    },
                  ),
                  const SizedBox(height: AppDesignTokens.spacing16),
                  
                  TextFormField(
                    controller: _goalController,
                    decoration: const InputDecoration(
                      labelText: 'Sprint Goal',
                      hintText: 'e.g., Complete 50 LeetCode problems',
                      border: OutlineInputBorder(),
                    ),
                    validator: (value) {
                      if (_type == GroupType.sprint && (value == null || value.trim().isEmpty)) {
                        return 'Please enter a goal for sprint';
                      }
                      return null;
                    },
                  ),
                ],
                
                const SizedBox(height: AppDesignTokens.spacing32),
                
                CustomButton.primary(
                  text: _isSubmitting ? 'Creating...' : 'Create Group',
                  onPressed: _isSubmitting ? null : _submit,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}