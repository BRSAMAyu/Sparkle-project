import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';

class BreathingTool extends StatefulWidget {
  const BreathingTool({super.key});

  @override
  State<BreathingTool> createState() => _BreathingToolState();
}

class _BreathingToolState extends State<BreathingTool> with SingleTickerProviderStateMixin {
  int _selectedDurationIndex = 0;
  final List<int> _durations = [1, 3, 5]; // Minutes
  
  bool _isPlaying = false;
  int _completedRounds = 0;
  int _totalRounds = 0;
  String _instruction = '准备';
  
  late AnimationController _controller;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 19), // 4+7+8
    );

    // Initial setup
    _updateTotalRounds();
  }

  void _updateTotalRounds() {
    // Each cycle is 19 seconds.
    // Total rounds = (Duration * 60) / 19
    final seconds = _durations[_selectedDurationIndex] * 60;
    setState(() {
      _totalRounds = (seconds / 19).ceil();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _timer?.cancel();
    super.dispose();
  }

  void _startBreathing() {
    setState(() {
      _isPlaying = true;
      _completedRounds = 0;
      _instruction = '吸气';
    });
    _runCycle();
  }

  void _stopBreathing() {
    _controller.reset();
    _timer?.cancel();
    setState(() {
      _isPlaying = false;
      _instruction = '准备';
    });
  }

  void _runCycle() {
    if (_completedRounds >= _totalRounds) {
      _stopBreathing();
      return;
    }

    // Phase 1: Inhale (4s)
    setState(() => _instruction = '吸气');
    _controller.duration = const Duration(seconds: 4);
    _controller.forward(from: 0.0);

    _timer = Timer(const Duration(seconds: 4), () {
      if (!mounted || !_isPlaying) return;

      // Phase 2: Hold (7s)
      setState(() => _instruction = '屏息');
      // Animation stays at 1.0
      
      _timer = Timer(const Duration(seconds: 7), () {
        if (!mounted || !_isPlaying) return;

        // Phase 3: Exhale (8s)
        setState(() => _instruction = '呼气');
        _controller.duration = const Duration(seconds: 8);
        _controller.reverse(from: 1.0);

        _timer = Timer(const Duration(seconds: 8), () {
          if (!mounted || !_isPlaying) return;
          
          setState(() {
            _completedRounds++;
          });
          _runCycle();
        });
      });
    });
  }

  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.all(AppDesignTokens.spacing24),
      decoration: BoxDecoration(
        color: DS.brandPrimaryConst,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header
          Row(
            children: [
              Container(
                padding: EdgeInsets.all(DS.sm),
                decoration: BoxDecoration(
                  color: Colors.indigo.shade50,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(Icons.air, color: Colors.indigo),
              ),
              SizedBox(width: DS.md),
              const Text(
                '呼吸练习',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const Spacer(),
              IconButton(
                icon: Icon(Icons.close),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          SizedBox(height: DS.xxl),

          // Breathing Circle Animation
          Center(
            child: SizedBox(
              width: 200,
              height: 200,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  // Outer ring
                  Container(
                    width: 200,
                    height: 200,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: Colors.indigo.withValues(alpha: 0.1),
                        width: 2,
                      ),
                    ),
                  ),
                  // Animated Circle
                  AnimatedBuilder(
                    animation: _controller,
                    builder: (context, child) {
                      // Scale from 0.4 to 1.0
                      final scale = 0.4 + (_controller.value * 0.6);
                      return Transform.scale(
                        scale: scale,
                        child: Container(
                          width: 200,
                          height: 200,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: RadialGradient(
                              colors: [
                                Colors.indigo.shade200.withValues(alpha: 0.3),
                                Colors.indigo.shade100.withValues(alpha: 0.1),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                  // Inner Text
                  Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        _instruction,
                        style: TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                          color: Colors.indigo.shade700,
                        ),
                      ),
                      if (_isPlaying)
                        Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(
                            '$_completedRounds / $_totalRounds',
                            style: TextStyle(
                              fontSize: 14,
                              color: DS.brandPrimary.shade600,
                            ),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          
          SizedBox(height: DS.xxxl),

          // Duration Selector
          if (!_isPlaying)
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(_durations.length, (index) {
                final isSelected = _selectedDurationIndex == index;
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: InkWell(
                    onTap: () {
                      setState(() {
                        _selectedDurationIndex = index;
                        _updateTotalRounds();
                      });
                    },
                    borderRadius: BorderRadius.circular(20),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      decoration: BoxDecoration(
                        color: isSelected ? Colors.indigo : DS.brandPrimary.shade100,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        '${_durations[index]}分钟',
                        style: TextStyle(
                          color: isSelected ? DS.brandPrimary : DS.brandPrimary.shade600,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ),
                );
              }),
            ),

          SizedBox(height: DS.xl),

          // Control Button
          CustomButton.primary(
            text: _isPlaying ? '停止练习' : '开始练习',
            icon: _isPlaying ? Icons.stop : Icons.play_arrow,
            onPressed: _isPlaying ? _stopBreathing : _startBreathing,
            customGradient: _isPlaying 
              ? AppDesignTokens.warningGradient 
              : LinearGradient(colors: [Colors.indigo, DS.brandPrimaryConst]),
          ),
        ],
      ),
    );
}
