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
  
  // Form fields
  String _name = '';
  String _description = '';
  GroupType _type = GroupType.squad;
  List<String> _focusTags = [];
  DateTime? _deadline;
  String _sprintGoal = '';
  final _tagsController = TextEditingController();
  
  bool _isSubmitting = false;

  @override
  void dispose() {
    _tagsController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    _formKey.currentState!.save();

    // Parse tags
    if (_tagsController.text.isNotEmpty) {
      _focusTags = _tagsController.text.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
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
        name: _name,
        description: _description.isEmpty ? null : _description,
        type: _type,
        focusTags: _focusTags,
        deadline: _deadline,
        sprintGoal: _sprintGoal.isEmpty ? null : _sprintGoal,
        // Defaults
        maxMembers: 50,
        isPublic: true,
        joinRequiresApproval: false,
      );

      final group = await ref.read(myGroupsProvider.notifier).createGroup(groupData);
      
      if (mounted) {
        context.pop(); // Close create screen
        context.push('/community/groups/${group.id}'); // Go to new group
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
    return Scaffold(
      appBar: AppBar(title: const Text('Create Group')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppDesignTokens.spacing16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextFormField(
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
                onSaved: (value) => _name = value!.trim(),
              ),
              const SizedBox(height: AppDesignTokens.spacing16),
              
              DropdownButtonFormField<GroupType>(
                value: _type,
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
                decoration: const InputDecoration(
                  labelText: 'Description',
                  border: OutlineInputBorder(),
                  alignLabelWithHint: true,
                ),
                maxLines: 3,
                onSaved: (value) => _description = value?.trim() ?? '',
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
                  onSaved: (value) => _sprintGoal = value?.trim() ?? '',
                ),
              ],
              
              const SizedBox(height: AppDesignTokens.spacing32),
              
              CustomButton.filled(
                text: _isSubmitting ? 'Creating...' : 'Create Group',
                onPressed: _isSubmitting ? null : _submit,
              ),
            ],
          ),
        ),
      ),
    );
  }
}