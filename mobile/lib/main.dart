import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'widgets/pixel_rpg_card.dart'; // 引入卡片组件
import 'execution_screen.dart';       // ★★★ 必须引入这个文件，否则找不到 ExecutionScreen
import 'chat_screen.dart';

void main() {
  runApp(const SparkleApp());
}

class SparkleApp extends StatelessWidget {
  const SparkleApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Sparkle',
      theme: ThemeData(
        // --- 核心修改：使用像素字体 ---
        // 'Press Start 2P' 是最经典的红白机风格粗体
        // 'VT323' 是稍微细一点的复古终端风格
        textTheme: GoogleFonts.vt323TextTheme(),
        
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFFEDA446),
          brightness: Brightness.light, 
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF5F5F5),
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // --- 顶部导航栏 ---
      appBar: AppBar(
        backgroundColor: const Color(0xFFEDA446),
        title: const Text('Sparkle 任务板', style: TextStyle(fontWeight: FontWeight.bold)),
        centerTitle: true,
        elevation: 0,
        shape: const Border(bottom: BorderSide(color: Colors.black, width: 3)), // 像素风底边
      ),
      
      // --- 页面主体 ---
      body: ListView(
        padding: const EdgeInsets.only(top: 20),
        children: [
          // 模拟的 AI 任务推荐
          PixelRPGCard(
            title: '复习离散数学',
            description: '逻辑运算章节 - 预计 5 分钟',
            icon: Icons.auto_stories,
            themeColor: Colors.blueAccent,
            // --- 修复点：这里之前有一堆重复的烂代码，现在修好了 ---
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (context) => const ExecutionScreen(
                  taskTitle: '复习离散数学',
                  durationMinutes: 5,
                ),
              ),
            ),
          ),
          
          // 你可以复制上面那个 PixelRPGCard 再加几个任务试试...
        ],
      ),
      
      // --- 底部浮动按钮 (FAB) ---
    floatingActionButton: FloatingActionButton.large(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (context) => const ChatScreen()),
          );
        },
        backgroundColor: const Color(0xFF6C63FF), // 亮紫色
        shape: const RoundedRectangleBorder(
          side: BorderSide(color: Colors.black, width: 3), // 像素风边框
          borderRadius: BorderRadius.all(Radius.circular(16)),
        ), // RoundedRectangleBorder 结束
        child: const Icon(Icons.chat_bubble_outline, color: Colors.white, size: 32),
      ), // FloatingActionButton.large 结束
    );
// 新增的聊天页面
  
}
}