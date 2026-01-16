import 'package:flutter/material.dart';
import 'dart:async';
import 'widgets/pixel_focus_widgets.dart'; // 引入刚才写的组件

class ExecutionScreen extends StatefulWidget {
  final String taskTitle;
  final int durationMinutes;

  const ExecutionScreen({
    super.key,
    required this.taskTitle,
    required this.durationMinutes,
  });

  @override
  State<ExecutionScreen> createState() => _ExecutionScreenState();
}

class _ExecutionScreenState extends State<ExecutionScreen> {
  late int _secondsRemaining;
  late int _totalSeconds;
  Timer? _timer;
  bool _isPaused = false;

  @override
  void initState() {
    super.initState();
    _totalSeconds = widget.durationMinutes * 60;
    _secondsRemaining = _totalSeconds;
    _startTimer();
  }

  void _startTimer() {
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!_isPaused) {
        setState(() {
          if (_secondsRemaining > 0) {
            _secondsRemaining--;
          } else {
            _timer?.cancel();
            // TODO: 任务完成逻辑，弹出结算弹窗
          }
        });
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final progress = 1.0 - (_secondsRemaining / _totalSeconds);

    return Scaffold(
      backgroundColor: const Color(0xFFF0F0F0),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        shape: const Border(bottom: BorderSide(color: Colors.black, width: 3)),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.black),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text("执行中...", style: TextStyle(color: Colors.black, fontWeight: FontWeight.w900)),
        centerTitle: true,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          children: [
            // 1. 任务信息区
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFFFFF8E1), // 米黄色纸张感
                border: Border.all(color: Colors.black, width: 3),
                boxShadow: const [BoxShadow(color: Colors.black, offset: Offset(6, 6))],
              ),
              child: Column(
                children: [
                  Text(
                    widget.taskTitle,
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  const Text("🔥 保持专注，不要切屏", style: TextStyle(color: Colors.grey)),
                ],
              ),
            ),
            
            const Spacer(),
            
            // 2. 核心倒计时区
            PixelTimerDisplay(secondsRemaining: _secondsRemaining),
            const SizedBox(height: 32),
            
            // 3. 进度条
            Text("完成度 ${(progress * 100).toInt()}%", style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            PixelProgressBar(progress: progress, color: const Color(0xFF4CAF50)), // 绿色进度
            
            const Spacer(),
            
            // 4. 控制按钮区
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                PixelButton(
                  label: "放弃",
                  color: const Color(0xFFFF5252), // 红色
                  onPressed: () => Navigator.pop(context),
                ),
                PixelButton(
                  label: _isPaused ? "继续" : "暂停",
                  color: const Color(0xFF64B5F6), // 蓝色
                  isLarge: true,
                  icon: _isPaused ? Icons.play_arrow : Icons.pause,
                  onPressed: () {
                    setState(() {
                      _isPaused = !_isPaused;
                    });
                  },
                ),
              ],
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}