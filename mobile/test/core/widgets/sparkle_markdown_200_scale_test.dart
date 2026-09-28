import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';

/// V4-U07 验收「200%长中文/代码/公式不横向破屏」的可失败钉。
///
/// 200% 文字缩放（系统大字号档）+ 窄屏（360 逻辑宽）下，长中文段落、
/// 长代码块、长公式（无空格长 token）与表格均不得产生横向溢出异常；
/// 代码块横向滚动是允许的溢出消化路径（代码保真，容器不破）。
/// 对照组用必然溢出的 Row 证明断言判别力（真破屏会被抓到）。

const _kNarrowWidth = 360.0;
const _k200Scale = TextScaler.linear(2.0);

Widget _host(
  Widget child, {
  TextScaler? scaler,
  double width = _kNarrowWidth,
}) =>
    MaterialApp(
      home: MediaQuery(
        data: MediaQueryData(
          size: Size(width, 720),
          textScaler: scaler ?? _k200Scale,
        ),
        child: Scaffold(
          body: SingleChildScrollView(
            child: SizedBox(
              width: width,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: child,
              ),
            ),
          ),
        ),
      ),
    );

/// 气泡真实内容宽（chat_screen._StreamingBubble：min(屏宽×0.8, 内容列×0.9)
/// 再减内边距——比整屏更紧的约束面）。
const _kBubbleContentWidth = 288.0;

void main() {
  testWidgets('正：200% 长中文段落不横向破屏', (tester) async {
    const longChinese = '这是一段非常长的中文说明，用于验证在系统大字号档位下，聊天正文是否会在'
        '窄屏设备上产生横向溢出。中文没有空格分词，排版引擎必须逐字换行才能保证'
        '不破屏。这一段刻意写到远超一屏的长度，并且夹杂一些 English words 与'
        '数字 1234567890 混排，以及全角标点符号「」『』（），确保边界情况都被覆盖。'
        '再补一句：学习是一个把陌生变成熟悉的过程，而工具应当帮助人看见下一步。';

    await tester.pumpWidget(
      _host(
        const SparkleMarkdown(
          content: longChinese,
          textColor: Colors.black,
          codeBackgroundColor: Color(0x11000000),
          linkColor: Colors.blue,
        ),
      ),
    );
    await tester.pump();

    expect(tester.takeException(), isNull, reason: '200% 长中文不得横向溢出');
  });

  testWidgets('正：200% 长代码块不破屏（代码块内部横向滚动消化）', (tester) async {
    const longCode = '''
```python
def compute_alignment(user_goal, current_state, memory_snapshot, constraints, budget, history_window=90, strategy_version="v4", enable_shadow_compare=True, verbose_logging=False, telemetry_sink=None):
    aligned = [step for step in plan.steps if step.satisfies(user_goal) and step.respects(constraints) and step.cost_micro_usd <= budget.remaining_micro_usd]
    return AlignmentResult(steps=aligned, watermark=memory_snapshot.relational_watermark, fallback_reason=None, trace_id="0123456789abcdef0123456789abcdef")
```
''';

    await tester.pumpWidget(
      _host(
        const SparkleMarkdown(
          content: longCode,
          textColor: Colors.black,
          codeBackgroundColor: Color(0x11000000),
          linkColor: Colors.blue,
        ),
      ),
    );
    await tester.pump();

    expect(tester.takeException(), isNull, reason: '200% 长代码不得横向溢出容器');
    // 溢出消化路径在场：代码卡内横向滚动条（代码保真不折行、容器不破）。
    expect(
      find.descendant(
        of: find.byType(SparkleMarkdown),
        matching: find.byWidgetPredicate(
          (widget) =>
              widget is SingleChildScrollView &&
              widget.scrollDirection == Axis.horizontal,
        ),
      ),
      findsWidgets,
    );
  });

  testWidgets('正：200% 长公式（无空格长 token 与 LaTeX 源文）不横向破屏', (tester) async {
    const longFormula = r'''
傅里叶变换的定义式为 $F(\omega)=\int_{-\infty}^{\infty} f(t)e^{-i\omega t}dt$，
其离散形式 $X_k=\sum_{n=0}^{N-1}x_n\cdot e^{-i2\pi kn/N}=\sum_{n=0}^{N-1}x_n\cdot(\cos(2\pi kn/N)-i\sin(2\pi kn/N))$。
连续信号的能量谱密度可写作 $S_{xx}(\omega)=\lim_{T\to\infty}\mathbb{E}[|X_T(\omega)|^2]/(2T)\approx0.57721566490153286060651209008240243104215933593992$。
''';

    await tester.pumpWidget(
      _host(
        const SparkleMarkdown(
          content: longFormula,
          textColor: Colors.black,
          codeBackgroundColor: Color(0x11000000),
          linkColor: Colors.blue,
        ),
      ),
    );
    await tester.pump();

    expect(tester.takeException(), isNull, reason: '200% 长公式文本不得横向溢出');
  });

  testWidgets('正：200% 表格与列表混排在窄屏不横向破屏', (tester) async {
    const markdownTable = r'''
| 阶段 | 呈现语义 | 用户可见反馈 | 超时行为 |
|---|---|---|---|
| 检索 | 正在查找相关资料 | 阶段胶囊单行脉冲 | 如实说明未找到 |
| 思考 | 正在组织回答 | 阶段胶囊推进 | 显示已等待时长与取消 |
| 生成 | 正在写出回答 | 分段流式增量 | 中断内容保留标记 |

- 长列表项一：包含较长的中文说明与 English mixed words，验证条目换行；
- 长列表项二：`inline_code_with_a_very_long_identifier_name_here` 与公式 \$x^2\$；
- 长列表项三：编号、引用与嵌套结构。
''';

    await tester.pumpWidget(
      _host(
        const SparkleMarkdown(
          content: markdownTable,
          textColor: Colors.black,
          codeBackgroundColor: Color(0x11000000),
          linkColor: Colors.blue,
        ),
      ),
    );
    await tester.pump();

    expect(tester.takeException(), isNull, reason: '200% 表格/列表混排不得横向溢出');
  });

  testWidgets('对照：必然溢出的无约束 Row 会被本断言抓到（判别力自证）', (tester) async {
    await tester.pumpWidget(
      _host(
        Row(
          children: [
            Text('A' * 120),
            Text('B' * 120),
            Text('C' * 120),
          ],
        ),
      ),
    );
    await tester.pump();

    expect(
      tester.takeException(),
      isNotNull,
      reason: '真破屏必须被同款断言捕获，证明上述「isNull」有判别力',
    );
  });

  testWidgets('更紧约束：200% 长代码/公式在气泡真实内容宽（288）不破屏', (tester) async {
    const longCode = '''
```sql
SELECT memory.item_id, memory.scope, receipt.why_now_confidence, watermark.relational_max_updated_at, watermark.age_coverage_lag_ms, fallback.reason_code, fallback.relational_one_hop_payload_json FROM episodic_memories AS memory LEFT JOIN context_selection_receipts AS receipt ON receipt.memory_epoch = memory.epoch LEFT JOIN graph_index_watermarks AS watermark ON watermark.user_id = memory.user_id LEFT JOIN graph_index_fallbacks AS fallback ON fallback.query_id = receipt.receipt_id WHERE memory.user_id = '00000000-0000-0000-0000-000000000000' AND memory.deleted_at IS NULL ORDER BY memory.recency_score DESC LIMIT 50;
```
''';
    const longFormula = r'''
质能关系与相对论能量修正：$E^2=(pc)^2+(m_0c^2)^2$，其中 $p=\\gamma m_0v=\\frac{m_0v}{\\sqrt{1-v^2/c^2}}$，代入得 $E^2=m_0^2c^4+\\frac{m_0^2v^2c^2}{1-v^2/c^2}=0.57721566490153286060651209008240243104215933593992\\times10^{-34}\\mathrm{J^2}$。
''';

    for (final content in [longCode, longFormula]) {
      await tester.pumpWidget(
        _host(
          SparkleMarkdown(
            content: content,
            textColor: Colors.black,
            codeBackgroundColor: const Color(0x11000000),
            linkColor: Colors.blue,
          ),
          width: _kBubbleContentWidth,
        ),
      );
      await tester.pump();
      expect(
        tester.takeException(),
        isNull,
        reason: '气泡宽 288 下 200% 长内容不得横向溢出',
      );
    }
  });
}
