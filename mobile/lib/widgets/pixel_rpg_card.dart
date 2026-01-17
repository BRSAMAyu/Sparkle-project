import 'package:flutter/material.dart';

class PixelRPGCard extends StatelessWidget {
  final String title;
  final String description;
  final IconData icon; // 暂时用 Icon 代替图片，防报错
  final Color themeColor;
  final VoidCallback onTap;

  const PixelRPGCard({
    super.key,
    required this.title,
    required this.description,
    this.icon = Icons.local_fire_department, // 默认火苗图标
    this.themeColor = const Color(0xFFEDA446), // 暖橙色
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
        // --- 核心：复古硬边框 ---
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: Colors.black, width: 3), // 粗黑边框
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.3),
              offset: const Offset(6, 6), // 硬投影
              blurRadius: 0, // 0 模糊度 = 像素锐利感
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(12.0),
          child: Row(
            children: [
              // --- 图标容器 ---
              Container(
                width: 50,
                height: 50,
                decoration: BoxDecoration(
                  color: themeColor.withOpacity(0.2),
                  border: Border.all(color: Colors.black, width: 2),
                ),
                child: Icon(icon, color: Colors.black, size: 30),
              ),
              const SizedBox(width: 16),
              // --- 文本区域 ---
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontSize: 16, 
                        fontWeight: FontWeight.w900, //以此模拟像素字体的粗重感
                        color: Colors.black,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      description,
                      style: TextStyle(fontSize: 12, color: Colors.grey[800]),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.arrow_forward_ios, size: 16, color: Colors.black),
            ],
          ),
        ),
      ),
    );
  }
}