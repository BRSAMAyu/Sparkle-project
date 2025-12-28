import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/presentation/providers/community_providers.dart';

class CreatePostScreen extends ConsumerStatefulWidget {
  const CreatePostScreen({super.key});

  @override
  ConsumerState<CreatePostScreen> createState() => _CreatePostScreenState();
}

class _CreatePostScreenState extends ConsumerState<CreatePostScreen> {
  final _contentController = TextEditingController();
  final _topicController = TextEditingController();
  bool _isPosting = false;
  XFile? _selectedImage;
  String? _selectedLocation;

  Future<void> _pickImage() async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: ImageSource.gallery);
    if (image != null) {
      setState(() {
        _selectedImage = image;
      });
    }
  }

  Future<void> _pickLocation() async {
    // Feature: Implement location picker using geolocator package
    // Requires: flutter pub add geolocator
    // 暂时使用模拟位置
    setState(() {
      _selectedLocation = '模拟位置';
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('位置选择功能开发中，使用模拟位置'),
        duration: Duration(seconds: 2),
      ),
    );
  }

  Future<void> _submit() async {
    final content = _contentController.text.trim();
    if (content.isEmpty) return;

    setState(() => _isPosting = true);

    try {
      await ref.read(feedProvider.notifier).addPostOptimistically(
            content,
            _selectedImage != null ? [_selectedImage!.path] : [],
            _topicController.text.trim(),
          );
      // Feature: Save location data separately if provided
      if (_selectedLocation != null) {
        print('位置信息: $_selectedLocation');
      }
      if (mounted) context.pop();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to post: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isPosting = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text('New Post'),
        actions: [
          Padding(
            padding: EdgeInsets.only(right: 16),
            child: TextButton(
              onPressed: _isPosting ? null : _submit,
              style: TextButton.styleFrom(
                backgroundColor: DS.brandPrimary.withOpacity(0.1),
                foregroundColor: DS.brandPrimary,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20),
                ),
              ),
              child: _isPosting
                  ? SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(color: DS.brandPrimaryConst, strokeWidth: 2),
                    )
                  : Text('Post', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ),
        ],
      ),
      body: Padding(
        padding: EdgeInsets.all(DS.lg),
        child: Column(
          children: [
            TextField(
              controller: _contentController,
              autofocus: true,
              maxLines: 8,
              style: TextStyle(color: DS.brandPrimaryConst, fontSize: 16),
              decoration: InputDecoration(
                hintText: "What's on your mind?",
                hintStyle: TextStyle(color: DS.brandPrimary.withOpacity(0.3)),
                border: InputBorder.none,
              ),
            ),
            Divider(color: DS.brandPrimary.withOpacity(0.24)),
            TextField(
              controller: _topicController,
              style: TextStyle(color: DS.brandSecondary),
              decoration: InputDecoration(
                prefixText: '# ',
                hintText: 'Topic (optional)',
                hintStyle: TextStyle(color: DS.brandPrimary.withOpacity(0.3)),
                border: InputBorder.none,
              ),
            ),
            const Spacer(),
            // Toolbar (Placeholder)
            Row(
              children: [
                IconButton(
                  icon: Icon(
                    Icons.image_outlined,
                    color: _selectedImage != null
                        ? DS.brandPrimary
                        : DS.brandPrimary,
                  ),
                  onPressed: _pickImage,
                ),
                IconButton(
                  icon: Icon(
                    Icons.location_on_outlined,
                    color: _selectedLocation != null
                        ? DS.brandPrimary
                        : DS.brandPrimary,
                  ),
                  onPressed: _pickLocation,
                ),
              ],
            ),
          ],
        ),
      ),
    );
}
