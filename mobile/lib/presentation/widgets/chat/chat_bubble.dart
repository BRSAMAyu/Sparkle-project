import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:sparkle/app/theme.dart';
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
  late Animation<double> _scale;
  late Animation<Offset> _position;

  bool _showHeart = false;
  bool _isPressed = false; // For ScaleTap effect

  @override
  void initState() {
    super.initState();
    _entryController = AnimationController(
      duration: const Duration(milliseconds: 600), // Slightly longer for elasticity
      vsync: this,
    );

    _scale = Tween<double>(begin: 0.9, end: 1.0).animate(
      CurvedAnimation(parent: _entryController, curve: Curves.elasticOut),
    );

    _position = Tween<Offset>(
      begin: const Offset(0, 0.5), // Start lower
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _entryController, curve: Curves.easeOutQuart)); // Smoother slide

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
    
    return SlideTransition(
      position: _position,
      child: ScaleTransition(
        scale: _scale,
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
                  onTapDown: (_) => setState(() => _isPressed = true),
                  onTapUp: (_) => setState(() => _isPressed = false),
                  onTapCancel: () => setState(() => _isPressed = false),
                  child: AnimatedScale(
                    scale: _isPressed ? 0.98 : 1.0,
                    duration: const Duration(milliseconds: 100),
                    curve: Curves.easeInOut,
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
                                    boxShadow: [
                                      BoxShadow(
                                        color: AppDesignTokens.primaryBase.withValues(alpha: 0.3),
                                        blurRadius: 12,
                                        offset: const Offset(0, 4),
                                      ),
                                    ],
                                  )
                                : BoxDecoration(
                                    color: context.colors.surfaceCard,
                                    borderRadius: _getBorderRadius(isUser),
                                    boxShadow: [
                                      BoxShadow(
                                        color: Colors.black.withValues(alpha: 0.05),
                                        blurRadius: 8,
                                        offset: const Offset(0, 2),
                                      ),
                                    ],
                                    border: Border.all(color: context.colors.border.withValues(alpha: 0.5)),
                                  ),
                              child: ClipRRect(
                                borderRadius: _getBorderRadius(isUser),
                                child: BackdropFilter(
                                  filter: isUser ? ImageFilter.blur(sigmaX: 0, sigmaY: 0) : ImageFilter.blur(sigmaX: 10, sigmaY: 10),
                                  child: Container(
                                    decoration: isUser ? null : BoxDecoration(
                                      gradient: LinearGradient(
                                        colors: [
                                          context.colors.surfaceGlass.withValues(alpha: 0.8),
                                          context.colors.surfaceCard.withValues(alpha: 0.9),
                                        ],
                                        begin: Alignment.topLeft,
                                        end: Alignment.bottomRight,
                                      ),
                                    ),
                                  child: Padding(
                                    padding: const EdgeInsets.symmetric(vertical: AppDesignTokens.spacing12, horizontal: AppDesignTokens.spacing16),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        MarkdownBody(
                                          data: widget.message.content,
                                          styleSheet: MarkdownStyleSheet(
                                            p: TextStyle(
                                              color: isUser ? Colors.white : context.colors.textPrimary,
                                              fontSize: AppDesignTokens.fontSizeBase,
                                              height: AppDesignTokens.lineHeightNormal,
                                            ),
                                            h1: TextStyle(
                                              color: isUser ? Colors.white : context.colors.textPrimary,
                                              fontSize: AppDesignTokens.fontSize2xl,
                                              fontWeight: AppDesignTokens.fontWeightBold,
                                            ),
                                            h2: TextStyle(
                                              color: isUser ? Colors.white : context.colors.textPrimary,
                                              fontSize: AppDesignTokens.fontSizeXl,
                                              fontWeight: AppDesignTokens.fontWeightBold,
                                            ),
                                            h3: TextStyle(
                                              color: isUser ? Colors.white : context.colors.textPrimary,
                                              fontSize: AppDesignTokens.fontSizeLg,
                                              fontWeight: AppDesignTokens.fontWeightSemibold,
                                            ),
                                            code: TextStyle(
                                              backgroundColor: isUser ? Colors.white.withValues(alpha: 0.2) : context.colors.surfaceElevated,
                                              fontFamily: 'monospace',
                                              fontSize: AppDesignTokens.fontSizeSm,
                                              color: isUser ? Colors.white : AppDesignTokens.secondaryBase,
                                            ),
                                            codeblockDecoration: BoxDecoration(
                                              color: isUser ? Colors.white.withValues(alpha: 0.1) : context.colors.surfaceElevated,
                                              borderRadius: AppDesignTokens.borderRadius12,
                                            ),
                                            codeblockPadding: const EdgeInsets.all(AppDesignTokens.spacing12),
                                            blockquote: TextStyle(
                                              color: isUser ? Colors.white.withValues(alpha: 0.8) : context.colors.textSecondary,
                                              fontStyle: FontStyle.italic,
                                            ),
                                            blockquoteDecoration: BoxDecoration(
                                              border: Border(
                                                left: BorderSide(
                                                  color: isUser ? Colors.white.withValues(alpha: 0.5) : AppDesignTokens.primaryBase,
                                                  width: AppDesignTokens.spacing4 - 1.0,
                                                ),
                                              ),
                                            ),
                                            a: TextStyle(
                                              color: isUser ? Colors.white : AppDesignTokens.primaryBase,
                                              decoration: TextDecoration.underline,
                                            ),
                                            listBullet: TextStyle(
                                              color: isUser ? Colors.white : context.colors.textSecondary,
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
                          ),
                          
                          // Action Cards
                          if (widget.message.widgets != null && widget.message.widgets!.isNotEmpty)
                            Padding(
                              padding: const EdgeInsets.only(top: 8.0, left: 8.0),
                              child: Column(
                                children: widget.message.widgets!.map((widgetPayload) => 
                                  Padding(
                                    padding: const EdgeInsets.only(bottom: 8.0),
                                    child: ActionCard(action: widgetPayload),
                                  ),
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
