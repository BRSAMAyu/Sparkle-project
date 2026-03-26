import 'package:flutter/material.dart';

class SimulationChatBubble extends StatelessWidget {
  const SimulationChatBubble({
    required this.speaker,
    required this.message,
    super.key,
  });

  final String speaker;
  final String message;

  @override
  Widget build(BuildContext context) => Align(
        alignment: Alignment.centerLeft,
        child: Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xFFEFF4FF),
            borderRadius: BorderRadius.circular(18),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                speaker,
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF23408E),
                ),
              ),
              const SizedBox(height: 6),
              Text(message),
            ],
          ),
        ),
      );
}
