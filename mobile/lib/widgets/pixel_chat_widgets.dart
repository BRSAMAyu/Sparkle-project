import 'package:flutter/material.dart';

// 1. 像素风聊天气泡
class PixelChatBubble extends StatelessWidget {
  final String message;
  final bool isUser;
  final String? characterName; // AI 的名字，如 "AI 导师"

  const PixelChatBubble({
    super.key,
    required this.message,
    required this.isUser,
    this.characterName,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12.0, horizontal: 16.0),
      child: Row(
        mainAxisAlignment:
            isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // --- AI 头像 (左侧) ---
          if (!isUser) ...[
            _buildPixelAvatar(Icons.smart_toy, const Color(0xFF2C3E50)), // 深空蓝背景
            const SizedBox(width: 12),
          ],

          // --- 气泡主体 ---
          Flexible(
            child: Column(
              crossAxisAlignment:
                  isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
              children: [
                // AI 的名字条 (RPG 风格)
                if (!isUser && characterName != null)
                  Container(
                    margin: const EdgeInsets.only(bottom: 4, left: 4),
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.black,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      characterName!,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),

                // 对话框容器
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    // 用户用暖橙色，AI 用米黄色(羊皮纸感)
                    color: isUser ? const Color(0xFFEDA446) : const Color(0xFFFFF8E1),
                    border: Border.all(color: Colors.black, width: 3),
                    boxShadow: const [
                      BoxShadow(
                        color: Colors.black,
                        offset: Offset(4, 4), // 硬阴影
                        blurRadius: 0,
                      )
                    ],
                  ),
                  child: Text(
                    message,
                    style: TextStyle(
                      color: Colors.black,
                      fontSize: 18, // 像素字体要大一点才好看
                      height: 1.4,
                      // 如果需要打字机效果，可以在这里扩展
                    ),
                  ),
                ),
              ],
            ),
          ),

          // --- 用户头像 (右侧) ---
          if (isUser) ...[
            const SizedBox(width: 12),
            _buildPixelAvatar(Icons.person, const Color(0xFFEDA446)), // 暖橙色背景
          ],
        ],
      ),
    );
  }

  // 构建方形像素头像
  Widget _buildPixelAvatar(IconData icon, Color bgColor) {
    return Container(
      width: 48,
      height: 48,
      decoration: BoxDecoration(
        color: bgColor,
        border: Border.all(color: Colors.black, width: 3),
        boxShadow: const [BoxShadow(color: Colors.black, offset: Offset(2, 2))],
      ),
      child: Icon(icon, color: Colors.white, size: 28),
    );
  }
}

// 2. 像素风输入框
class PixelInputBar extends StatelessWidget {
  final TextEditingController controller;
  final VoidCallback onSend;

  const PixelInputBar({
    super.key,
    required this.controller,
    required this.onSend,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: const BoxDecoration(
        color: Color(0xFFE0E0E0), // 控制台底色
        border: Border(top: BorderSide(color: Colors.black, width: 3)),
      ),
      child: Row(
        children: [
          // 输入框
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                color: Colors.white,
                border: Border.all(color: Colors.black, width: 2),
              ),
              child: TextField(
                controller: controller,
                style: const TextStyle(fontSize: 18),
                decoration: const InputDecoration(
                  hintText: " 输入指令...",
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 14),
                  isDense: true,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          
          // 发送按钮 (方形)
          GestureDetector(
            onTap: onSend,
            child: Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                color: const Color(0xFF6C63FF), // 发送按钮用亮紫色点缀
                border: Border.all(color: Colors.black, width: 2),
                boxShadow: const [BoxShadow(color: Colors.black, offset: Offset(2, 2))],
              ),
              child: const Icon(Icons.send, color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }
}