import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 设计系统 2.0 使用示例
///
/// 这个文件展示了如何在实际应用中使用新的设计系统

// ==================== 示例 1: 基础使用 ====================

class BasicUsageExample extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // 使用主题管理器自动适配深色/浅色模式
      backgroundColor: context.sparkleColors.surfacePrimary,

      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // 1. 使用原子按钮组件
            SparkleButton.primary(
              label: '主要操作',
              onPressed: () {
                print('主要操作被点击');
              },
              icon: Icon(Icons.star),
            ),

            SizedBox(height: DS.sm), // 2. 使用间距系统

            // 3. 次要按钮
            SparkleButton.secondary(
              label: '次要操作',
              onPressed: () {},
            ),

            SizedBox(height: DS.sm),

            // 4. 轮廓按钮
            SparkleButton.outline(
              label: '查看详情',
              onPressed: () {},
            ),

            SizedBox(height: DS.lg),

            // 5. 使用设计令牌的容器
            Container(
              padding: DS.edgeLg.edge,
              decoration: BoxDecoration(
                color: DS.brandPrimary,
                borderRadius: BorderRadius.circular(DS.sm),
                boxShadow: context.sparkleShadows.medium,
              ),
              child: Text(
                '语义化颜色和阴影',
                style: DS.bodyLarge.copyWith(
                  color: Colors.white,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ==================== 示例 2: 响应式布局 ====================

class ResponsiveExample extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    // 使用 AdaptiveLayout 自动切换布局
    return AdaptiveLayout(
      mobile: MobileLayout(),
      tablet: TabletLayout(),
      desktop: DesktopLayout(),
    );
  }
}

class MobileLayout extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('移动端布局')),
      body: Padding(
        padding: EdgeInsets.all(DS.lg),
        child: Column(
          children: [
            SparkleButton.primary(
              label: '移动端按钮',
              onPressed: () {},
              expand: true,
            ),
            SizedBox(height: DS.md),
            _buildCard(context, '卡片 1'),
            SizedBox(height: DS.md),
            _buildCard(context, '卡片 2'),
          ],
        ),
      ),
    );
  }

  Widget _buildCard(BuildContext context, String title) {
    return Container(
      padding: DS.edgeLg.edge,
      decoration: BoxDecoration(
        color: context.sparkleColors.surfaceSecondary,
        borderRadius: BorderRadius.circular(DS.sm),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: DS.headingMedium),
          SizedBox(height: DS.sm),
          Text(
            '这是移动端的卡片内容，使用紧凑的布局和较小的间距。',
            style: DS.bodyMedium,
          ),
        ],
      ),
    );
  }
}

class TabletLayout extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('平板布局')),
      body: Padding(
        padding: EdgeInsets.all(DS.xl),
        child: GridView.count(
          crossAxisCount: 2,
          crossAxisSpacing: DS.lg,
          mainAxisSpacing: DS.lg,
          children: [
            _buildCard(context, '卡片 1'),
            _buildCard(context, '卡片 2'),
            _buildCard(context, '卡片 3'),
            _buildCard(context, '卡片 4'),
          ],
        ),
      ),
    );
  }

  Widget _buildCard(BuildContext context, String title) {
    return Container(
      padding: DS.edgeXl.edge,
      decoration: BoxDecoration(
        color: context.sparkleColors.surfaceSecondary,
        borderRadius: BorderRadius.circular(DS.lg),
        boxShadow: context.sparkleShadows.medium,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: DS.headingLarge),
          SizedBox(height: DS.md),
          Text(
            '平板布局使用更宽松的间距和网格系统，提供更好的视觉层次。',
            style: DS.bodyLarge,
          ),
          SizedBox(height: DS.lg),
          SparkleButton.outline(
            label: '操作',
            onPressed: () {},
          ),
        ],
      ),
    );
  }
}

class DesktopLayout extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          // 侧边栏
          Container(
            width: 280,
            color: context.sparkleColors.surfaceSecondary,
            padding: DS.edgeXl.edge,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('导航', style: DS.headingLarge),
                SizedBox(height: DS.lg),
                SparkleButton.ghost(label: '首页', onPressed: () {}),
                SizedBox(height: DS.sm),
                SparkleButton.ghost(label: '设置', onPressed: () {}),
              ],
            ),
          ),
          // 主内容
          Expanded(
            child: Padding(
              padding: EdgeInsets.all(DS.xxl),
              child: GridView.count(
                crossAxisCount: 3,
                crossAxisSpacing: DS.xl,
                mainAxisSpacing: DS.xl,
                children: [
                  _buildCard(context, '卡片 1'),
                  _buildCard(context, '卡片 2'),
                  _buildCard(context, '卡片 3'),
                  _buildCard(context, '卡片 4'),
                  _buildCard(context, '卡片 5'),
                  _buildCard(context, '卡片 6'),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCard(BuildContext context, String title) {
    return Container(
      padding: DS.edgeXxl.edge,
      decoration: BoxDecoration(
        color: context.sparkleColors.surfaceSecondary,
        borderRadius: BorderRadius.circular(DS.xl),
        boxShadow: context.sparkleShadows.large,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: DS.displayLarge),
          SizedBox(height: DS.md),
          Text(
            '桌面布局充分利用大屏幕空间，提供多列网格和丰富的视觉层次。',
            style: DS.bodyLarge,
          ),
          SizedBox(height: DS.xl),
          SparkleButtonGroup(
            buttons: [
              SparkleButton.primary(label: '主要', onPressed: () {}),
              SparkleButton.outline(label: '次要', onPressed: () {}),
            ],
          ),
        ],
      ),
    );
  }
}

// ==================== 示例 3: 动态主题切换 ====================

class ThemeSwitcherExample extends StatefulWidget {
  @override
  State<ThemeSwitcherExample> createState() => _ThemeSwitcherExampleState();
}

class _ThemeSwitcherExampleState extends State<ThemeSwitcherExample> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('主题切换演示'),
        actions: [
          // 主题切换按钮
          IconButton(
            icon: Icon(Icons.brightness_6),
            onPressed: () async {
              await ThemeManager().toggleDarkMode();
              setState(() {});
            },
          ),
        ],
      ),
      body: Padding(
        padding: DS.edgeLg.edge,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('当前主题', style: DS.headingLarge),
            SizedBox(height: DS.md),

            // 显示当前主题信息
            Container(
              padding: DS.edgeLg.edge,
              decoration: BoxDecoration(
                color: context.sparkleColors.surfaceSecondary,
                borderRadius: BorderRadius.circular(DS.sm),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildInfoRow('模式', ThemeManager().mode.name),
                  _buildInfoRow('品牌', ThemeManager().brandPreset.name),
                  _buildInfoRow('高对比度', ThemeManager().highContrast.toString()),
                ],
              ),
            ),

            SizedBox(height: DS.lg),

            // 品牌预设选择
            Text('品牌预设', style: DS.headingMedium),
            SizedBox(height: DS.sm),

            SparkleButtonGroup(
              direction: Axis.vertical,
              buttons: [
                SparkleButton.outline(
                  label: 'Sparkle (默认)',
                  onPressed: () async {
                    await ThemeManager().setBrandPreset(BrandPreset.sparkle);
                    setState(() {});
                  },
                ),
                SparkleButton.outline(
                  label: 'Ocean',
                  onPressed: () async {
                    await ThemeManager().setBrandPreset(BrandPreset.ocean);
                    setState(() {});
                  },
                ),
                SparkleButton.outline(
                  label: 'Forest',
                  onPressed: () async {
                    await ThemeManager().setBrandPreset(BrandPreset.forest);
                    setState(() {});
                  },
                ),
              ],
            ),

            SizedBox(height: DS.lg),

            // 高对比度切换
            Row(
              children: [
                Text('高对比度模式', style: DS.bodyLarge),
                Spacer(),
                Switch(
                  value: ThemeManager().highContrast,
                  onChanged: (value) async {
                    await ThemeManager().toggleHighContrast(value);
                    setState(() {});
                  },
                ),
              ],
            ),

            SizedBox(height: DS.lg),

            // 颜色预览
            Text('颜色预览', style: DS.headingMedium),
            SizedBox(height: DS.sm),

            Wrap(
              spacing: DS.sm,
              runSpacing: DS.sm,
              children: [
                _buildColorBox('品牌主色', DS.brandPrimary),
                _buildColorBox('品牌次色', DS.brandSecondary),
                _buildColorBox('成功', DS.success),
                _buildColorBox('警告', DS.warning),
                _buildColorBox('错误', DS.error),
                _buildColorBox('信息', DS.info),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: EdgeInsets.only(bottom: DS.sm),
      child: Row(
        children: [
          Text('$label: ', style: DS.labelLarge),
          Text(value, style: DS.bodyMedium),
        ],
      ),
    );
  }

  Widget _buildColorBox(String label, Color color) {
    return Container(
      width: 80,
      height: 60,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(DS.sm),
      ),
      alignment: Alignment.center,
      child: Text(
        label,
        style: DS.labelSmall.copyWith(
          color: color.computeLuminance() > 0.5 ? Colors.black : Colors.white,
        ),
        textAlign: TextAlign.center,
      ),
    );
  }
}

// ==================== 示例 4: 表单和输入 ====================

class FormExample extends StatefulWidget {
  @override
  State<FormExample> createState() => _FormExampleState();
}

class _FormExampleState extends State<FormExample> {
  final _formKey = GlobalKey<FormState>();
  bool _loading = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('表单示例')),
      body: SingleChildScrollView(
        padding: DS.edgeLg.edge,
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 标题
              Text('用户信息', style: DS.headingLarge),
              SizedBox(height: DS.lg),

              // 输入字段示例（使用标准Material输入框）
              _buildTextField('姓名', '请输入姓名'),
              SizedBox(height: DS.md),

              _buildTextField('邮箱', '请输入邮箱'),
              SizedBox(height: DS.md),

              _buildTextField('描述', '请输入描述', maxLines: 3),
              SizedBox(height: DS.lg),

              // 按钮组
              SparkleButtonGroup(
                buttons: [
                  SparkleLoadingButton(
                    label: '提交',
                    onPressed: () async {
                      if (_formKey.currentState!.validate()) {
                        setState(() => _loading = true);
                        await Future.delayed(Duration(seconds: 2));
                        setState(() => _loading = false);

                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text('提交成功！'),
                            backgroundColor: DS.success,
                          ),
                        );
                      }
                    },
                  ),
                  SparkleButton.outline(
                    label: '重置',
                    onPressed: () {
                      _formKey.currentState?.reset();
                    },
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTextField(String label, String hint, {int maxLines = 1}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: DS.labelLarge),
        SizedBox(height: DS.xs),
        TextFormField(
          decoration: InputDecoration(
            hintText: hint,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(DS.sm),
            ),
          ),
          maxLines: maxLines,
          validator: (value) {
            if (value == null || value.isEmpty) {
              return '此字段不能为空';
            }
            return null;
          },
        ),
      ],
    );
  }
}

// ==================== 示例 5: 加载和状态 ====================

class LoadingStatesExample extends StatefulWidget {
  @override
  State<LoadingStatesExample> createState() => _LoadingStatesExampleState();
}

class _LoadingStatesExampleState extends State<LoadingStatesExample> {
  bool _isLoading = false;
  String _status = '就绪';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('加载状态演示')),
      body: Padding(
        padding: DS.edgeLg.edge,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 状态显示
            Container(
              padding: DS.edgeLg.edge,
              decoration: BoxDecoration(
                color: context.sparkleColors.surfaceSecondary,
                borderRadius: BorderRadius.circular(DS.sm),
              ),
              child: Row(
                children: [
                  Text('状态: ', style: DS.labelLarge),
                  Text(_status, style: DS.bodyLarge),
                  if (_isLoading) ...[
                    SizedBox(width: DS.sm),
                    SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                      ),
                    ),
                  ],
                ],
              ),
            ),

            SizedBox(height: DS.lg),

            // 操作按钮
            SparkleButtonGroup(
              direction: Axis.vertical,
              buttons: [
                SparkleButton.primary(
                  label: '模拟加载 (1秒)',
                  onPressed: () async {
                    setState(() {
                      _isLoading = true;
                      _status = '加载中...';
                    });
                    await Future.delayed(Duration(seconds: 1));
                    setState(() {
                      _isLoading = false;
                      _status = '加载完成';
                    });
                  },
                ),

                SparkleLoadingButton(
                  label: '自动加载按钮',
                  onPressed: () async {
                    await Future.delayed(Duration(seconds: 2));
                  },
                ),

                SparkleButton.destructive(
                  label: '错误状态',
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('发生错误！'),
                        backgroundColor: DS.error,
                      ),
                    );
                  },
                ),
              ],
            ),

            SizedBox(height: DS.lg),

            // 不同状态的按钮
            Text('按钮状态', style: DS.headingMedium),
            SizedBox(height: DS.sm),

            Wrap(
              spacing: DS.sm,
              runSpacing: DS.sm,
              children: [
                SparkleButton.primary(label: '正常', onPressed: () {}),
                SparkleButton.primary(label: '加载中', loading: true),
                SparkleButton.primary(label: '禁用', disabled: true),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ==================== 示例 6: 验证器使用 ====================

class ValidatorExample extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('设计验证器')),
      body: Padding(
        padding: DS.edgeLg.edge,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('设计系统验证', style: DS.headingLarge),
            SizedBox(height: DS.lg),

            // 验证按钮
            SparkleButton.primary(
              label: '运行验证',
              onPressed: () async {
                final report = await DesignSystemChecker.checkCurrentContext(context);

                // 显示结果
                showDialog(
                  context: context,
                  builder: (context) => AlertDialog(
                    title: Text('验证结果'),
                    content: SingleChildScrollView(
                      child: Text(
                        report.isValid
                          ? '✅ 所有检查通过！\n得分: ${(report.score * 100).toStringAsFixed(0)}%'
                          : '❌ 发现 ${report.violations.length} 个问题\n得分: ${(report.score * 100).toStringAsFixed(0)}%',
                        style: DS.bodyLarge,
                      ),
                    ),
                    actions: [
                      SparkleButton.primary(
                        label: '确定',
                        onPressed: () => Navigator.pop(context),
                      ),
                    ],
                  ),
                );
              },
            ),

            SizedBox(height: DS.lg),

            // 验证示例
            Text('验证示例', style: DS.headingMedium),
            SizedBox(height: DS.sm),

            // 触控目标验证
            Container(
              padding: DS.edgeLg.edge,
              decoration: BoxDecoration(
                color: context.sparkleColors.surfaceSecondary,
                borderRadius: BorderRadius.circular(DS.sm),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('✅ 触控目标大小', style: DS.labelLarge),
                  SizedBox(height: DS.xs),
                  Text(
                    '所有按钮自动满足 48x48px 最小尺寸',
                    style: DS.bodyMedium,
                  ),
                  SizedBox(height: DS.sm),
                  Row(
                    children: [
                      SparkleButton.primary(label: '小', size: ButtonSize.small),
                      SizedBox(width: DS.sm),
                      SparkleButton.primary(label: '中', size: ButtonSize.medium),
                      SizedBox(width: DS.sm),
                      SparkleButton.primary(label: '大', size: ButtonSize.large),
                    ],
                  ),
                ],
              ),
            ),

            SizedBox(height: DS.md),

            // 颜色对比度验证
            Container(
              padding: DS.edgeLg.edge,
              decoration: BoxDecoration(
                color: context.sparkleColors.surfaceSecondary,
                borderRadius: BorderRadius.circular(DS.sm),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('✅ 颜色对比度', style: DS.labelLarge),
                  SizedBox(height: DS.xs),
                  Text(
                    '所有文本颜色符合 WCAG 2.1 AA 标准',
                    style: DS.bodyMedium,
                  ),
                  SizedBox(height: DS.sm),
                  Wrap(
                    spacing: DS.sm,
                    runSpacing: DS.sm,
                    children: [
                      Container(
                        padding: EdgeInsets.all(DS.sm),
                        color: DS.brandPrimary,
                        child: Text('主色背景', style: DS.labelLarge.copyWith(color: Colors.white)),
                      ),
                      Container(
                        padding: EdgeInsets.all(DS.sm),
                        color: DS.success,
                        child: Text('成功背景', style: DS.labelLarge.copyWith(color: Colors.white)),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ==================== 示例 7: 响应式值 ====================

class ResponsiveValuesExample extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('响应式值演示')),
      body: SingleChildScrollView(
        padding: DS.edgeLg.edge,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('响应式间距', style: DS.headingLarge),
            SizedBox(height: DS.lg),

            // 响应式间距演示
            Container(
              padding: ResponsiveValue(
                mobile: DS.edgeSm.edge,
                tablet: DS.edgeLg.edge,
                desktop: DS.edgeXl.edge,
              ).resolve(context),
              decoration: BoxDecoration(
                color: context.sparkleColors.surfaceSecondary,
                borderRadius: BorderRadius.circular(DS.sm),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('当前设备: ${context.breakpointInfo.category.name}', style: DS.headingMedium),
                  SizedBox(height: DS.sm),
                  Text(
                    '这个容器的内边距会根据屏幕尺寸自动调整：\n'
                    '- 手机: ${DS.sm}px\n'
                    '- 平板: ${DS.lg}px\n'
                    '- 桌面: ${DS.xl}px',
                    style: DS.bodyMedium,
                  ),
                ],
              ),
            ),

            SizedBox(height: DS.lg),

            // 响应式字体大小
            Text('响应式字体', style: DS.headingLarge),
            SizedBox(height: DS.sm),

            Text(
              '这段文本的大小会自动调整',
              style: ResponsiveValue(
                mobile: DS.bodyMedium,
                tablet: DS.bodyLarge,
                desktop: DS.headingMedium,
              ).resolve(context),
            ),

            SizedBox(height: DS.lg),

            // 响应式网格
            Text('响应式网格', style: DS.headingLarge),
            SizedBox(height: DS.sm),

            Container(
              height: 200,
              child: GridView.builder(
                gridDelegate: ResponsiveGridSystem.delegate(context),
                itemCount: 6,
                itemBuilder: (context, index) {
                  return Container(
                    decoration: BoxDecoration(
                      color: DS.brandPrimary.withOpacity(0.2 + 0.1 * index),
                      borderRadius: BorderRadius.circular(DS.sm),
                    ),
                    alignment: Alignment.center,
                    child: Text('Item ${index + 1}', style: DS.labelLarge),
                  );
                },
              ),
            ),

            SizedBox(height: DS.lg),

            // 设备信息
            Text('设备信息', style: DS.headingLarge),
            SizedBox(height: DS.sm),

            Container(
              padding: DS.edgeLg.edge,
              decoration: BoxDecoration(
                color: context.sparkleColors.surfaceSecondary,
                borderRadius: BorderRadius.circular(DS.sm),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildDeviceInfo('类别', context.breakpointInfo.category.name),
                  _buildDeviceInfo('密度', context.breakpointInfo.density.name),
                  _buildDeviceInfo('宽度', '${context.breakpointInfo.width.toStringAsFixed(0)}px'),
                  _buildDeviceInfo('方向', context.isLandscape ? '横屏' : '竖屏'),
                  _buildDeviceInfo('类型',
                    context.isMobile ? '移动设备' :
                    context.isTablet ? '平板' :
                    '桌面设备'
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDeviceInfo(String label, String value) {
    return Padding(
      padding: EdgeInsets.only(bottom: DS.xs),
      child: Row(
        children: [
          Text('$label: ', style: DS.labelMedium),
          Text(value, style: DS.bodyMedium),
        ],
      ),
    );
  }
}

// ==================== 主应用入口 ====================

class DesignSystemDemoApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '设计系统 2.0 演示',
      theme: AppThemes.lightTheme,
      darkTheme: AppThemes.darkTheme,
      themeMode: ThemeManager().mode,
      home: DesignSystemHome(),
    );
  }
}

class DesignSystemHome extends StatelessWidget {
  final List<DemoItem> demos = [
    DemoItem('基础使用', '按钮、颜色、间距', BasicUsageExample()),
    DemoItem('响应式布局', '自适应布局演示', ResponsiveExample()),
    DemoItem('主题切换', '动态主题管理', ThemeSwitcherExample()),
    DemoItem('表单示例', '输入和验证', FormExample()),
    DemoItem('加载状态', '动画和状态', LoadingStatesExample()),
    DemoItem('设计验证', '合规性检查', ValidatorExample()),
    DemoItem('响应式值', '自适应属性', ResponsiveValuesExample()),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('设计系统 2.0 演示'),
        actions: [
          IconButton(
            icon: Icon(Icons.brightness_6),
            onPressed: () async {
              await ThemeManager().toggleDarkMode();
            },
          ),
        ],
      ),
      body: ListView.builder(
        padding: DS.edgeLg.edge,
        itemCount: demos.length,
        itemBuilder: (context, index) {
          final demo = demos[index];
          return Padding(
            padding: EdgeInsets.only(bottom: DS.sm),
            child: Card(
              child: ListTile(
                title: Text(demo.title, style: DS.headingMedium),
                subtitle: Text(demo.description, style: DS.bodyMedium),
                trailing: Icon(Icons.arrow_forward_ios),
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => demo.screen),
                  );
                },
              ),
            ),
          );
        },
      ),
    );
  }
}

class DemoItem {
  final String title;
  final String description;
  final Widget screen;

  DemoItem(this.title, this.description, this.screen);
}

// ==================== 使用说明 ====================

/// 如何运行这个示例：
///
/// 1. 确保已初始化设计系统：
///    await DesignSystemInitializer.initialize();
///
/// 2. 在MaterialApp中配置主题：
///    MaterialApp(
///      theme: AppThemes.lightTheme,
///      darkTheme: AppThemes.darkTheme,
///      home: DesignSystemDemoApp(),
///    );
///
/// 3. 在代码中使用：
///    - DS.* 访问设计令牌
///    - SparkleButton.* 使用原子组件
///    - context.sparkleColors 访问主题颜色
///    - ResponsiveSystem.* 处理响应式
///
/// 4. 运行验证：
///    - 使用 DesignSystemChecker
///    - 检查控制台输出
///    - 进行视觉回归测试
