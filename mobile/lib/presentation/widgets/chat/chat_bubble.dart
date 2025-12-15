import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/presentation/widgets/chat/action_card.dart';

class ChatBubble extends StatefulWidget {
  final ChatMessageModel message;
  final bool showAvatar;

  const ChatBubble({
    required this.message, 
    super.key,
    this.showAvatar = true,
  });

  @override
  State<ChatBubble> createState() => _ChatBubbleState();
}

class _ChatBubbleState extends State<ChatBubble> with TickerProviderStateMixin {
  late AnimationController _entryController;
  late Animation<double> _opacity;
  late Animation<Offset> _position;

  bool _showHeart = false;

  @override
  void initState() {
    super.initState();
    _entryController = AnimationController(
      duration: AppDesignTokens.durationNormal,
      vsync: this,
    );

    _opacity = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _entryController, curve: Curves.easeOut),
    );

    _position = Tween<Offset>(
      begin: const Offset(0, 0.2),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _entryController, curve: Curves.easeOut));

    _entryController.forward();
  }

  @override
  void dispose() {
    _entryController.dispose();
    super.dispose();
  }

  void _handleDoubleTap() {
    if (widget.message.role == MessageRole.user) return; // Only like AI messages

    setState(() {
      _showHeart = true;
    });

    Future.delayed(const Duration(milliseconds: 1000), () {
      if (mounted) {
        setState(() {
          _showHeart = false;
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final bool isUser = widget.message.role == MessageRole.user;
    
    return FadeTransition(
      opacity: _opacity,
      child: SlideTransition(
        position: _position,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 12.0, horizontal: 8.0),
          child: Row(
            mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (!isUser && widget.showAvatar) _buildAvatar(isUser),
              if (!isUser && !widget.showAvatar) const SizedBox(width: 40), 

              Flexible(
                child: GestureDetector(
                  onDoubleTap: _handleDoubleTap,
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      Column(
                        crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                        children: [
                          Container(
                            margin: const EdgeInsets.symmetric(horizontal: 8.0),
                            constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
                            decoration: isUser 
                              ? BoxDecoration(
                                  gradient: AppDesignTokens.primaryGradient,
                                  borderRadius: _getBorderRadius(isUser),
                                  boxShadow: AppDesignTokens.shadowSm,
                                )
                              : BoxDecoration(
                                  color: Colors.white,
                                  borderRadius: _getBorderRadius(isUser),
                                  boxShadow: AppDesignTokens.shadowSm,
                                  border: Border.all(color: AppDesignTokens.neutral200),
                                ),
                            child: ClipRRect(
                              borderRadius: _getBorderRadius(isUser),
                              child: BackdropFilter(
                                filter: ImageFilter.blur(sigmaX: 0, sigmaY: 0), 
                                child: Padding(
                                  padding: const EdgeInsets.symmetric(vertical: 12.0, horizontal: 16.0),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      MarkdownBody(
                                        data: widget.message.content,
                                        styleSheet: MarkdownStyleSheet(
                                          p: TextStyle(
                                            color: isUser ? Colors.white : AppDesignTokens.neutral900,
                                            fontSize: AppDesignTokens.fontSizeBase,
                                            height: 1.5,
                                          ),
                                          code: TextStyle(
                                            backgroundColor: isUser ? Colors.white24 : AppDesignTokens.neutral100,
                                            fontFamily: 'monospace',
                                            fontSize: AppDesignTokens.fontSizeSm,
                                            color: isUser ? Colors.white : AppDesignTokens.neutral800,
                                          ),
                                          codeblockDecoration: BoxDecoration(
                                            color: isUser ? Colors.white12 : AppDesignTokens.neutral100,
                                            borderRadius: AppDesignTokens.borderRadius8,
                                          ),
                                          blockquote: TextStyle(
                                            color: isUser ? Colors.white70 : AppDesignTokens.neutral600,
                                            fontStyle: FontStyle.italic,
                                          ),
                                        ),
                                        onTapLink: (text, href, title) {
                                          if (href != null) {
                                            launchUrl(Uri.parse(href));
                                          }
                                        },
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                          
                          // Action Cards
                          if (widget.message.actions != null && widget.message.actions!.isNotEmpty)
                            Padding(
                              padding: const EdgeInsets.only(top: 8.0, left: 8.0),
                              child: Column(
                                children: widget.message.actions!.map((action) => 
                                  Padding(
                                    padding: const EdgeInsets.only(bottom: 8.0),
                                    child: ActionCard(action: action),
                                  )
                                ).toList(),
                              ),
                            ),
                        ],
                      ),
                      
                      // Heart Animation Overlay
                      if (_showHeart)
                        TweenAnimationBuilder<double>(
                          tween: Tween(begin: 0.0, end: 1.0),
                          duration: const Duration(milliseconds: 500),
                          curve: Curves.elasticOut,
                          builder: (context, value, child) {
                            return Transform.scale(
                              scale: value,
                              child: const Icon(
                                Icons.favorite,
                                color: AppDesignTokens.error,
                                size: 64,
                                shadows: [
                                  Shadow(blurRadius: 10, color: Colors.black26, offset: Offset(0, 4)),
                                ],
                              ),
                            );
                          },
                        ),
                    ],
                  ),
                ),
              ),

              if (isUser && widget.showAvatar) _buildAvatar(isUser),
              if (isUser && !widget.showAvatar) const SizedBox(width: 40),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAvatar(bool isUser) {
    return Container(
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        gradient: isUser ? AppDesignTokens.primaryGradient : AppDesignTokens.secondaryGradient,
        shape: BoxShape.circle,
      ),
      child: Container(
        padding: const EdgeInsets.all(8),
        decoration: const BoxDecoration(
          color: Colors.white,
          shape: BoxShape.circle,
        ),
        child: Icon(
          isUser ? Icons.person : Icons.auto_awesome,
          color: isUser ? AppDesignTokens.primaryBase : AppDesignTokens.secondaryBase,
          size: 16,
        ),
      ),
    );
  }

  BorderRadius _getBorderRadius(bool isUser) {
    return BorderRadius.only(
      topLeft: const Radius.circular(20),
      topRight: const Radius.circular(20),
      bottomLeft: isUser ? const Radius.circular(20) : const Radius.circular(4),
      bottomRight: isUser ? const Radius.circular(4) : const Radius.circular(20),
    );
  }
}
