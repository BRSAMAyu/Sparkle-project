import 'package:flutter/material.dart';
import 'widgets/pixel_chat_widgets.dart'; // 引入刚才写的组件

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _controller = TextEditingController();
  final List<Map<String, dynamic>> _messages = [
    {
      "msg": "你好，我是 Sparkle AI 导师。你的离散数学复习进度好像慢了，需要帮忙拆解任务吗？",
      "isUser": false,
    },
  ];

  void _sendMessage() {
    if (_controller.text.isEmpty) return;
    setState(() {
      _messages.add({
        "msg": _controller.text,
        "isUser": true,
      });
      // 模拟 AI 回复 (延迟 1 秒)
      Future.delayed(const Duration(seconds: 1), () {
        if (mounted) {
          setState(() {
            _messages.add({
              "msg": "收到！已为你生成 3 个微任务：\n1. 阅读逻辑运算讲义 (5min)\n2. 刷 3 道真值表题目 (10min)\n3. 总结错题 (5min)",
              "isUser": false,
            });
          });
        }
      });
      _controller.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F5), // 经典的像素游戏浅灰背景
      appBar: AppBar(
        backgroundColor: const Color(0xFF2C3E50), // 深空蓝 Header
        title: const Text("AI 导师在线", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        centerTitle: true,
        iconTheme: const IconThemeData(color: Colors.white),
        elevation: 0,
        shape: const Border(bottom: BorderSide(color: Colors.black, width: 3)),
      ),
      body: Column(
        children: [
          // 消息列表
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.only(top: 16, bottom: 16),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final m = _messages[index];
                return PixelChatBubble(
                  message: m['msg'],
                  isUser: m['isUser'],
                  characterName: "Sparkle Bot",
                );
              },
            ),
          ),
          
          // 底部输入栏
          PixelInputBar(
            controller: _controller,
            onSend: _sendMessage,
          ),
        ],
      ),
    );
  }
}