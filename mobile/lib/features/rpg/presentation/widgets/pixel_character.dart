import 'package:flutter/material.dart';
import 'package:sparkle/features/rpg/data/models/rpg_models.dart';

/// 像素风格人物形象组件
class PixelCharacter extends StatelessWidget {
  const PixelCharacter({
    super.key,
    required this.character,
    this.size = 128,
    this.showEquipmentPreview = false,
    this.selectedEquipment,
  });

  final Character character;
  final double size;
  final bool showEquipmentPreview;
  final Equipment? selectedEquipment;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.bottomCenter,
        children: [
          // 背景
          Container(
            width: size,
            height: size * 0.4, // 地面高度
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Colors.green.shade700,
                  Colors.green.shade900,
                ],
              ),
              borderRadius: BorderRadius.circular(size * 0.2),
            ),
            margin: EdgeInsets.only(top: size * 0.6),
          ),
          
          // 角色主体 - 使用像素风格绘制
          _buildPixelCharacter(),
        ],
      ),
    );
  }

  /// 构建像素风格角色
  Widget _buildPixelCharacter() {
    return Stack(
      alignment: Alignment.bottomCenter,
      children: [
        // 鞋子
        _buildEquipmentPart('shoes', character.equipment.shoes),
        
        // 裤子
        _buildEquipmentPart('pants', character.equipment.pants),
        
        // 上衣
        _buildEquipmentPart('shirt', character.equipment.shirt),
        
        // 武器
        _buildEquipmentPart('weapon', character.equipment.weapon),
        
        // 帽子
        _buildEquipmentPart('hat', character.equipment.hat),
        
        // 饰品
        _buildEquipmentPart('accessory', character.equipment.accessory),
        
        // 角色基础身体
        _buildBaseBody(),
      ],
    );
  }

  /// 构建角色基础身体（像素风格）
  Widget _buildBaseBody() {
    return SizedBox(
      width: size * 0.4,
      height: size * 0.7,
      child: CustomPaint(
        painter: _PixelBodyPainter(),
      ),
    );
  }

  /// 构建装备部位
  Widget _buildEquipmentPart(String type, String? equipmentId) {
    // 这里简化实现，使用颜色块代替实际像素图
    // 实际项目中应该根据equipmentId加载对应的像素图
    Color color = _getEquipmentColor(type);
    
    return SizedBox(
      width: size * 0.4,
      height: size * 0.7,
      child: CustomPaint(
        painter: _PixelEquipmentPainter(
          type: type,
          color: color,
        ),
      ),
    );
  }

  /// 获取装备部位颜色
  Color _getEquipmentColor(String type) {
    switch (type) {
      case 'hat':
        return Colors.blue;
      case 'shirt':
        return Colors.red;
      case 'pants':
        return Colors.green;
      case 'shoes':
        return Colors.brown;
      case 'weapon':
        return Colors.grey;
      case 'accessory':
        return Colors.yellow;
      default:
        return Colors.transparent;
    }
  }
}

/// 像素角色身体绘制器
class _PixelBodyPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    // 定义像素大小
    final pixelSize = size.width / 16; // 16x16像素网格
    
    // 肤色
    final skinColor = const Color(0xFFFFDBAC);
    final hairColor = const Color(0xFF5A3E2B);
    final shirtColor = const Color(0xFF4A90E2);
    final pantsColor = const Color(0xFF35495E);
    final shoeColor = const Color(0xFF2C3E50);
    
    // 绘制像素点的辅助方法
    void drawPixel(int x, int y, Color color) {
      final paint = Paint()..color = color;
      canvas.drawRect(
        Rect.fromLTWH(
          x * pixelSize,
          y * pixelSize,
          pixelSize,
          pixelSize,
        ),
        paint,
      );
    }
    
    // 绘制头部
    // 头发
    for (int x = 4; x < 12; x++) {
      drawPixel(x, 1, hairColor);
      drawPixel(x, 2, hairColor);
    }
    drawPixel(3, 2, hairColor);
    drawPixel(12, 2, hairColor);
    drawPixel(3, 3, hairColor);
    drawPixel(12, 3, hairColor);
    
    // 脸部
    for (int x = 5; x < 11; x++) {
      drawPixel(x, 3, skinColor);
      drawPixel(x, 4, skinColor);
      drawPixel(x, 5, skinColor);
    }
    drawPixel(4, 4, skinColor);
    drawPixel(11, 4, skinColor);
    
    // 眼睛
    drawPixel(6, 3, Colors.black);
    drawPixel(9, 3, Colors.black);
    
    // 嘴巴
    drawPixel(7, 5, Colors.red);
    drawPixel(8, 5, Colors.red);
    
    // 身体
    // 脖子
    drawPixel(7, 6, skinColor);
    drawPixel(8, 6, skinColor);
    
    // 躯干
    for (int x = 6; x < 10; x++) {
      drawPixel(x, 7, shirtColor);
      drawPixel(x, 8, shirtColor);
      drawPixel(x, 9, shirtColor);
      drawPixel(x, 10, shirtColor);
    }
    
    // 手臂
    // 左手臂
    drawPixel(5, 7, shirtColor);
    drawPixel(4, 8, shirtColor);
    drawPixel(3, 9, shirtColor);
    drawPixel(3, 10, shirtColor);
    drawPixel(4, 11, skinColor);
    drawPixel(5, 11, skinColor);
    
    // 右手臂
    drawPixel(10, 7, shirtColor);
    drawPixel(11, 8, shirtColor);
    drawPixel(12, 9, shirtColor);
    drawPixel(12, 10, shirtColor);
    drawPixel(11, 11, skinColor);
    drawPixel(10, 11, skinColor);
    
    // 腿部
    // 左腿
    for (int x = 6; x < 8; x++) {
      drawPixel(x, 11, pantsColor);
      drawPixel(x, 12, pantsColor);
      drawPixel(x, 13, pantsColor);
      drawPixel(x, 14, shoeColor);
    }
    
    // 右腿
    for (int x = 8; x < 10; x++) {
      drawPixel(x, 11, pantsColor);
      drawPixel(x, 12, pantsColor);
      drawPixel(x, 13, pantsColor);
      drawPixel(x, 14, shoeColor);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) {
    return false;
  }
}

/// 像素装备绘制器
class _PixelEquipmentPainter extends CustomPainter {
  const _PixelEquipmentPainter({
    required this.type,
    required this.color,
  });

  final String type;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    // 定义像素大小
    final pixelSize = size.width / 16; // 16x16像素网格
    
    // 绘制像素点的辅助方法
    void drawPixel(int x, int y, Color color) {
      final paint = Paint()..color = color;
      canvas.drawRect(
        Rect.fromLTWH(
          x * pixelSize,
          y * pixelSize,
          pixelSize,
          pixelSize,
        ),
        paint,
      );
    }
    
    switch (type) {
      case 'hat':
        // 绘制魔法帽子
        drawPixel(5, 0, color);
        drawPixel(6, 0, color);
        drawPixel(7, 0, color);
        drawPixel(8, 0, color);
        drawPixel(9, 0, color);
        drawPixel(10, 0, color);
        
        for (int x = 4; x < 12; x++) {
          drawPixel(x, 1, color);
        }
        
        drawPixel(3, 2, color);
        drawPixel(12, 2, color);
        break;
        
      case 'shirt':
        // 绘制胸甲
        for (int x = 5; x < 11; x++) {
          drawPixel(x, 7, color);
          drawPixel(x, 8, color);
          drawPixel(x, 9, color);
        }
        drawPixel(4, 8, color);
        drawPixel(11, 8, color);
        break;
        
      case 'pants':
        // 绘制裤子
        for (int x = 5; x < 8; x++) {
          drawPixel(x, 11, color);
          drawPixel(x, 12, color);
          drawPixel(x, 13, color);
        }
        for (int x = 8; x < 11; x++) {
          drawPixel(x, 11, color);
          drawPixel(x, 12, color);
          drawPixel(x, 13, color);
        }
        break;
        
      case 'shoes':
        // 绘制靴子
        for (int x = 5; x < 8; x++) {
          drawPixel(x, 14, color);
          drawPixel(x, 15, color);
        }
        for (int x = 8; x < 11; x++) {
          drawPixel(x, 14, color);
          drawPixel(x, 15, color);
        }
        break;
        
      case 'weapon':
        // 绘制剑
        // 剑柄
        drawPixel(13, 8, Colors.brown);
        drawPixel(13, 9, Colors.brown);
        drawPixel(13, 10, Colors.brown);
        
        // 剑身
        drawPixel(14, 6, color);
        drawPixel(14, 7, color);
        drawPixel(14, 8, color);
        drawPixel(14, 9, color);
        drawPixel(15, 7, color);
        drawPixel(15, 8, color);
        break;
        
      case 'accessory':
        // 绘制项链
        drawPixel(7, 6, color);
        drawPixel(8, 6, color);
        drawPixel(9, 6, color);
        
        drawPixel(7, 7, color);
        drawPixel(9, 7, color);
        break;
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) {
    return false;
  }
}
