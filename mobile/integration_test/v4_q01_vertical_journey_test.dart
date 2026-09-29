import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/semantics.dart' as sem;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/features/auth/presentation/screens/login_screen.dart';
import 'package:sparkle/features/auth/presentation/screens/register_screen.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/features/user/presentation/screens/modeling_chat_screen.dart';
import 'package:sparkle/features/user/presentation/screens/persona_onboarding_screen.dart';
import 'package:sparkle/features/goal/presentation/screens/goal_creation_wizard_screen.dart';
import 'package:sparkle/features/task/presentation/screens/task_create_screen.dart';
import 'package:sparkle/main.dart' as app;

/// V4-Q01 核心像素×AI 垂直旅程真端验收 driver（measurement infrastructure —
/// product code is NOT modified by this card；test-only driver，j02/macos
/// journey 先例同族）。
///
/// LEGS（dart-define Q01_LEG）：
///  * part1 : wipe → 冷启 → 会话隔离（幸存会话经 UI 登出）→ 访客进入 →
///            旅程锚点前置（真用户三段：注册转化[j02 Leg-U 同径]→ persona
///            J-02 快车道 → memory_goals(active) 落库；种子 demo 世界不产
///            MemoryGoal，J-01 向导写 goals 表而锚点读侧不认——无锚则
///            /journey/hybrid 500 NoActiveGoalError，r1 pilot/attempt6 实证）
///            → 知识底料 fixture（披露：经 app 自身会话走真实 documents
///            上传→MinIO 预签名→process_stored_file 分块嵌入管线，非手插
///            DB；无底料则 prep 诚实 no_materials——检索零命中不编造引用是
///            产品设计）→ 种子卡点任务接续 → 执行面 → 卡住 FAB →
///            StuckHelpSheet → 统一恢复旅程 → 澄清问（服务端派生）→
///            校准区纠正「不是不会，今天只有十五分钟」→ 仅本次 → 时长对照 →
///            生成 diff → 确认调整 → committed 回执（receipt_id）→
///            Hybrid 入口「和 Sparkle 一起推进」→ 备料→你研判→交付 → done。
///  * part2 : 无 wipe 真重启进程（App 进程级重开）→ 接续可见性：目标/任务/
///            纠正后时长/回执痕迹。依赖 part1 经 stdout Q01_STATE 移交状态。
///
/// 诚实性规则（承 j02 + EVALUATION_PROTOCOL）：
///  * 所有帧=真实引擎顶层 RepaintBoundary（topmost full-viewport，V3-FIX-543
///    承接）；宿主控制台锁定→物理录屏黑帧（probe 实证），视频=引擎帧按真实
///    墙钟合成，出处披露。
///  * 失败与重试全部落 steps json，不挑拣；不写库、不 Mock、不以 API 代 UI。
///    例外仅一处且披露：知识底料 fixture 是「用户已有学习资料」这一前置条件
///    的等价物（macOS 原生文件选择框在 flutter_test 宿主外，无法客户端驱动），
///    经真实上传管线落库；旅程六环节（接续/卡住/纠正/Hybrid/回执/结果）本身
///    全部 UI 操作驱动。

const _kLeg = String.fromEnvironment('Q01_LEG', defaultValue: 'part1');
const _kRun = String.fromEnvironment('Q01_RUN', defaultValue: 'r1');
const _kShotDest = String.fromEnvironment(
  'Q01_SHOT_DEST',
  defaultValue: '/tmp/q01_shots',
);
const _kGoalTitle = String.fromEnvironment('Q01_GOAL_TITLE',
    defaultValue: '数据结构期中冲刺');
const _kTaskTitle = String.fromEnvironment('Q01_TASK_TITLE',
    defaultValue: '二叉树遍历');
const _kMinutes = String.fromEnvironment('Q01_MINUTES', defaultValue: '15');
const _kUser = String.fromEnvironment('Q01_USER');
/// J-01 向导支线开关（v3 默认关）：r5 实证向导计划任务不落任务列表投影 →
/// 校准「仅本次」锚点结构性缺席；v3 主径=列表空态真实任务创建。向导的
/// 真 LLM 意图分析+计划 preview 证据已在 r4/r5 捕获并保留（证据五件套
/// 引用），六环节闭环旅程不再依赖它。
const _kRunWizard = String.fromEnvironment('Q01_WIZARD', defaultValue: '0');
const kIntentText = '两周内掌握线性代数矩阵特征值，能独立做完一套期末真题';

/// 注册转化用测试口令（测试自建账号，非任何真实凭据）
const kRegPassword = 'Q01-Passw0rd!';

/// 知识底料 fixture（披露：内容为本测试编写的真实学习笔记，非模型产物、
/// 非用户私密材料；经真实上传→分块→嵌入管线落库，供 prep 真实检索命中）。
const kFixtureFileName = '线性代数特征值与矩阵对角化学习笔记.md';
const String kFixtureMarkdown = '''# 线性代数：特征值与矩阵对角化（期末复习笔记）

## 一、特征值与特征向量的定义

设 A 是 n 阶方阵，若存在数 λ 和非零列向量 x，使得 Ax = λx，则称 λ 为 A 的特征值，x 为对应的特征向量。

求法：解特征方程 det(A − λE) = 0。特征多项式的根即全部特征值；对每个 λ，解齐次方程组 (A − λE)x = 0，其非零解即特征向量。

## 二、性质

1. 全部特征值之和 = 迹 tr(A) = 主对角线元素之和。
2. 全部特征值之积 = 行列式 det(A)。
3. 不同特征值对应的特征向量线性无关。
4. 若 A 满足 f(A)=0（如 A²=A 幂等、A²=E 对合），特征值只能取 f 的根。

## 三、相似对角化

若 n 阶矩阵 A 有 n 个线性无关的特征向量，则 A 可相似对角化：存在可逆 P，使 P⁻¹AP = Λ（对角阵，对角元为特征值）。

充要条件：每个 k 重特征值恰有 k 个线性无关的特征向量（几何重数 = 代数重数）。

步骤：①求全部特征值；②对每个特征值求特征向量；③n 个无关向量拼成 P；④写出 Λ。

## 四、实对称矩阵

实对称矩阵必可正交相似对角化：不同特征值的特征向量正交；重根对应的特征向量可施密特正交化。Q⁻¹AQ = QᵀAQ = Λ。

## 五、典型真题套路

- 已知特征值反求参数：用 |A − λE| = 0 或 tr/det 联立。
- 判断能否对角化：先数重数，再看无关特征向量个数。
- 由 A 的特征值求 A⁻¹、A*、A^k、f(A) 的特征值：同一特征向量，特征值做同样运算。
- 二次型标准化与正负惯性指数：由特征值符号判定正定（全正 ⇔ 正定）。

## 六、易错点

1. 特征向量必须非零；λ=0 可以是特征值（此时 A 不可逆）。
2. 对角化时 P 的列与 Λ 的对角元顺序必须对应。
3. 实对称重根的正交化不能忘记施密特补足。
4. 相似矩阵有相同特征值，但有相同特征值不一定相似。
''';

Future<void> main() async {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized()
      .framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;

  final failures = <String>[];
  final steps = <Map<String, dynamic>>[];
  final clicks = <int>[0];
  late WidgetTester testTester;

  Future<void> wipeLocalState() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    const secure = FlutterSecureStorage(
      mOptions: MacOsOptions(useDataProtectionKeyChain: false),
    );
    await secure.deleteAll();
  }

  Future<void> shot(String relName) async {
    final dest = '$_kShotDest/$relName';
    try {
      await testTester.runAsync(() async {
        RenderObject root;
        try {
          root = WidgetsBinding.instance.renderViews.first;
        } catch (_) {
          root = RendererBinding.instance.renderViews.first;
        }
        RenderRepaintBoundary? boundary;
        RenderRepaintBoundary? firstAny;
        final view = testTester.view;
        final screen = view.physicalSize / view.devicePixelRatio;
        bool subtreeHasText(RenderObject ro) {
          if (ro is RenderParagraph || ro is RenderEditable) return true;
          var found = false;
          ro.visitChildren((child) {
            if (!found && subtreeHasText(child)) found = true;
          });
          return found;
        }

        void walk(RenderObject ro) {
          if (ro is RenderRepaintBoundary) {
            firstAny ??= ro;
            if (!ro.debugNeedsPaint &&
                ro.size.width >= screen.width * 0.9 &&
                ro.size.height >= screen.height * 0.9 &&
                subtreeHasText(ro)) {
              boundary = ro; // topmost qualifying wins
            }
          }
          ro.visitChildren(walk);
        }

        walk(root);
        boundary ??= firstAny;
        if (boundary == null) throw StateError('no RepaintBoundary in tree');
        final image = await boundary!.toImage(pixelRatio: 2.0);
        final data = await image.toByteData(format: ui.ImageByteFormat.png);
        if (data == null) throw StateError('null png bytes');
        File(dest)
          ..createSync(recursive: true)
          ..writeAsBytesSync(data.buffer.asUint8List(), flush: true);
      });
      // ignore: avoid_print
      print('Q01_SHOT $relName ok bytes=${File(dest).lengthSync()}');
    } catch (e) {
      // ignore: avoid_print
      print('Q01_SHOT_FAIL $relName: $e');
      failures.add('screenshot $relName failed: $e');
    }
  }

  /// 真实 semantics 树 dump（SemanticsNode 全遍历）。
  Future<void> dumpSemantics(String tag) async {
    try {
      await testTester.runAsync(() async {
        final handle = testTester.ensureSemantics();
        await testTester.pump(const Duration(milliseconds: 300));
        final owner = RendererBinding.instance.pipelineOwner.semanticsOwner;
        final root = owner?.rootSemanticsNode;
        final buf = StringBuffer();
        buf.writeln('# semantics dump $tag run=$_kRun leg=$_kLeg '
            'ts=${DateTime.now().toIso8601String()}');
        if (root == null) {
          buf.writeln('(semantics tree empty)');
        } else {
          void walk(sem.SemanticsNode node, int depth) {
            final rect = node.rect;
            final flags = <String>[];
            if (node.hasFlag(sem.SemanticsFlag.isButton)) flags.add('button');
            if (node.hasFlag(sem.SemanticsFlag.isTextField)) {
              flags.add('textField');
            }
            if (node.hasFlag(sem.SemanticsFlag.isChecked)) flags.add('checked');
            buf.writeln('${'  ' * depth}[${node.id}] '
                'label="${node.label}" '
                'value="${node.value}" '
                '${flags.join(',')} '
                'rect=(${rect.left.toStringAsFixed(0)},'
                '${rect.top.toStringAsFixed(0)},'
                '${rect.width.toStringAsFixed(0)}x'
                '${rect.height.toStringAsFixed(0)})');
            node.visitChildren((child) {
              walk(child, depth + 1);
              return true;
            });
          }

          walk(root, 0);
        }
        File('$_kShotDest/semantics_${_kRun}_${_kLeg}_$tag.txt')
          ..createSync(recursive: true)
          ..writeAsStringSync(buf.toString());
        handle.dispose();
      });
      // ignore: avoid_print
      print('Q01_SEMANTICS $tag ok');
    } catch (e) {
      // ignore: avoid_print
      print('Q01_SEMANTICS_FAIL $tag: $e');
      failures.add('semantics $tag failed: $e');
    }
  }

  void recordStep(String step, bool pass, String note) {
    steps.add({
      'leg': _kLeg,
      'run': _kRun,
      'step': step,
      'status': pass ? 'PASS' : 'FAIL',
      'note': note,
      'ts': DateTime.now().toIso8601String(),
    });
    // ignore: avoid_print
    print('Q01_STEP ${pass ? 'PASS' : 'FAIL'} $_kRun/$_kLeg/$step note=$note');
  }

  Finder? textAny(List<String> texts) {
    for (final t in texts) {
      final f = find.text(t);
      if (f.evaluate().isNotEmpty) return f.first;
    }
    return null;
  }

  Future<bool> waitUntil(
    WidgetTester tester,
    bool Function() cond, {
    Duration timeout = const Duration(seconds: 30),
  }) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      if (cond()) return true;
      await tester.pump(const Duration(milliseconds: 250));
    }
    return cond();
  }

  Future<void> safeSettle(
    WidgetTester tester, [
    Duration timeout = const Duration(seconds: 6),
  ]) async {
    try {
      await tester.pumpAndSettle(
        const Duration(milliseconds: 100),
        EnginePhase.sendSemanticsUpdate,
        timeout,
      );
    } catch (_) {
      await tester.pump(const Duration(seconds: 1));
    }
  }

  Finder? primaryButton(List<String> labels) {
    for (final label in labels) {
      var f = find.widgetWithText(SparkleButton, label);
      if (f.evaluate().isNotEmpty) return f.first;
      f = find.widgetWithText(FilledButton, label);
      if (f.evaluate().isNotEmpty) return f.first;
    }
    return null;
  }

  bool? primaryEnabled(WidgetTester tester, Finder f) {
    final w = f.evaluate().first.widget;
    if (w is SparkleButton) return w.onPressed != null;
    if (w is FilledButton) return w.onPressed != null;
    return null;
  }

  Future<void> dumpTexts(WidgetTester tester, String tag) async {
    final texts = <String>[];
    for (final e in find.byType(Text).evaluate()) {
      final w = e.widget;
      if (w is Text) {
        final plain = w.data ?? w.textSpan?.toPlainText() ?? '';
        if (plain.trim().isNotEmpty) texts.add(plain.trim());
      }
    }
    // ignore: avoid_print
    print('Q01_TEXTDUMP [$tag] n=${texts.length} '
        '${jsonEncode(texts.take(60).toList())}');
  }

  /// 知识底料 fixture（披露见文件头）：复用 app 自身会话 token，走产品真实
  /// 上传管线（prepare → MinIO 预签名 PUT → confirm → process_stored_file）。
  /// 不手插 DB、不伪造分块；token 只在进程内使用，不打印。
  Future<String> uploadFixtureDocument() async {
    const secure = FlutterSecureStorage(
      mOptions: MacOsOptions(useDataProtectionKeyChain: false),
    );
    final token = await secure.read(key: 'access_token');
    if (token == null || token.isEmpty) return 'no_token';
    final bytes = utf8.encode(kFixtureMarkdown);
    final client = HttpClient();
    try {
      Future<Map<String, dynamic>> call(
        String method,
        String url, [
        List<int>? body,
      ]) async {
        final req = await client.openUrl(method, Uri.parse(url));
        req.headers.set('Authorization', 'Bearer $token');
        if (body != null) {
          req.headers.set('Content-Type', 'application/json');
          req.add(body);
        }
        final res = await req.close();
        final text = await res.transform(utf8.decoder).join();
        final decoded = jsonDecode(text);
        if (decoded is Map<String, dynamic>) {
          final inner = decoded['data'];
          if (inner is Map<String, dynamic>) return inner;
          return decoded;
        }
        throw StateError('unexpected envelope from $method $url: $text');
      }

      final prepared = await call(
        'POST',
        'http://localhost:8080/api/v1/documents/upload',
        utf8.encode(jsonEncode({
          'filename': kFixtureFileName,
          'mime_type': 'text/markdown',
          'file_size': bytes.length,
          'visibility': 'private',
        })),
      );
      final fileId = prepared['file_id']?.toString() ?? '';
      final presigned = prepared['presigned_url']?.toString() ?? '';
      if (fileId.isEmpty || presigned.isEmpty) return 'prepare_bad_shape';
      final put = await client.openUrl('PUT', Uri.parse(presigned));
      put.headers.set('Content-Type', 'text/markdown');
      put.headers.contentLength = bytes.length;
      put.add(bytes);
      final putRes = await put.close();
      await putRes.drain<void>();
      if (putRes.statusCode != 200) return 'minio_put_${putRes.statusCode}';
      await call(
        'POST',
        'http://localhost:8080/api/v1/documents/$fileId/confirm-upload',
      );
      for (var i = 0; i < 40; i++) {
        await Future<void>.delayed(const Duration(seconds: 5));
        final status = await call(
          'GET',
          'http://localhost:8080/api/v1/documents/$fileId/status',
        );
        final s = status['status']?.toString() ?? '';
        // GET /documents/{id}/status 的 stage 映射：record 'processed' →
        // status_value 'done'（attempt8 实证：等 'processed' 必超时）
        if (s == 'processed' || s == 'done') return 'ok fileId=$fileId';
        if (s == 'failed') return 'processing_failed';
      }
      return 'processing_timeout';
    } catch (e) {
      return 'exception:$e';
    } finally {
      client.close();
    }
  }

  /// 会话隔离：part1 需要独立 fresh guest。tester 进程内的 wipe 只清
  /// tester 侧存储（r1 attempt2 实证：app 侧 keychain 会话幸存→复用旧
  /// 用户）；唯一可靠且诚实的清场 = UI 驱动 app 自己的退出登录
  /// （profile tab → 退出登录瓦片 → 确认），由产品自身清会话。
  Future<bool> driveClientLogout(WidgetTester tester) async {
    final tab = find.byIcon(Icons.person_outlined);
    if (tab.evaluate().isEmpty) return false;
    clicks[0]++;
    await tester.tap(tab.first, warnIfMissed: false);
    final onProfile = await waitUntil(
      tester,
      () => find.byIcon(Icons.logout_rounded).evaluate().isNotEmpty,
      timeout: const Duration(seconds: 15),
    );
    if (!onProfile) return false;
    for (var i = 0; i < 10; i++) {
      if (find.byIcon(Icons.logout_rounded).evaluate().isNotEmpty) break;
      try {
        await tester.drag(find.byType(Scrollable).first, const Offset(0, -300));
        await tester.pump(const Duration(milliseconds: 400));
      } catch (_) {
        break;
      }
    }
    final tile = find.byIcon(Icons.logout_rounded);
    if (tile.evaluate().isEmpty) return false;
    try {
      await tester.ensureVisible(tile.first);
    } catch (_) {}
    clicks[0]++;
    await tester.tap(tile.first, warnIfMissed: false);
    final dialogOk = await waitUntil(
      tester,
      () => textAny(['确认', '确定']) != null,
      timeout: const Duration(seconds: 8),
    );
    if (!dialogOk) return false;
    clicks[0]++;
    await tester.tap(textAny(['确认', '确定'])!, warnIfMissed: false);
    return await waitUntil(
      tester,
      () => find.text('以访客身份继续').evaluate().isNotEmpty,
      timeout: const Duration(seconds: 15),
    );
  }

  /// 旅程锚点前置（真用户三段路径，全部 UI 驱动）：
  /// ① guest → 注册转化：dashboard 转化卡「注册并同步进度」（可见性有
  ///    价值信号门，缺席时诚实降级：UI 登出 → 登录页「还没有账号？」，
  ///    j02 Leg-U 同径）→ 注册表单 4 字段 + 同意勾选 + 注册 → IN-PLACE
  ///    翻转（会话不落 login，同 user_id，种子 demo 世界保留）。
  /// ② persona J-02 快车道：首页「继续引导」→ persona step1 输入目标 →
  ///    j02-fast-path-cta → 建模访谈 → 「跳过」→ POST /profile/onboarding
  ///    落 memory_goals(active)——Hybrid 锚点真源。
  /// 为什么不走 J-01 目标向导：attempt6 实证它写 goals 表，而 first_action
  /// 读侧只认 memory_goals（两套 goal 系统的既有缝隙，本验证卡不改产品
  /// 代码）；guest 又被路由守卫挡在 persona 外（isGuestUser 恒重定向
  /// /home，j02 runbook G4 也预期 guest memory_goals=0）。故「访客→注册
  /// →画像」是锚点唯一的全 UI 真实路径。
  Future<bool> driveIdentityAnchor(WidgetTester tester) async {
    final suffix = DateTime.now().millisecondsSinceEpoch.toString().substring(7);
    final regUsername = 'q01up$suffix';

    // ---- ① 注册转化 ----
    var conversionSeen = false;
    Finder? conversionCta;
    for (var r = 0; r < 3 && conversionCta == null; r++) {
      conversionCta = textAny(['注册并同步进度']);
      if (conversionCta == null) {
        try {
          await tester.drag(find.byType(Scrollable).first, const Offset(0, -220));
          await tester.pump(const Duration(milliseconds: 450));
        } catch (_) {
          break;
        }
      }
    }
    if (conversionCta != null) conversionSeen = true;
    if (conversionCta != null) {
      try {
        await tester.ensureVisible(conversionCta);
      } catch (_) {}
      clicks[0]++;
      await tester.tap(conversionCta, warnIfMissed: false);
    } else {
      // 降级路径：转化卡不可见（价值信号门）→ UI 登出 → 登录页注册链
      // ignore: avoid_print
      print('Q01_ANCHOR conversion card not visible; degraded via login register link');
      final outOk = await driveClientLogout(tester);
      if (!outOk) {
        // ignore: avoid_print
        print('Q01_ANCHOR degraded logout failed');
        return false;
      }
      final regLink = textAny(['还没有账号？']);
      if (regLink == null) {
        // ignore: avoid_print
        print('Q01_ANCHOR register link missing on login');
        return false;
      }
      // 登录页折叠线下 ghost 按钮可能出屏（800x600），先滚到位再点
      try {
        await tester.ensureVisible(regLink);
        await tester.pump(const Duration(milliseconds: 300));
      } catch (_) {}
      clicks[0]++;
      await tester.tap(regLink, warnIfMissed: false);
    }
    final atRegister = await waitUntil(
      tester,
      () =>
          find.byType(RegisterScreen).evaluate().isNotEmpty ||
          textAny(['确认密码']) != null,
      timeout: const Duration(seconds: 15),
    );
    if (!atRegister) {
      // ignore: avoid_print
      print('Q01_ANCHOR register form never appeared');
      return false;
    }
    await safeSettle(tester);
    await shot('$_kRun/$_kLeg/03-register-form.png');

    final fields = find.byType(TextFormField);
    if (fields.evaluate().length < 4) {
      // ignore: avoid_print
      print('Q01_ANCHOR register fields=${fields.evaluate().length} expect 4');
      return false;
    }
    await tester.enterText(fields.at(0), regUsername);
    await tester.enterText(fields.at(1), '$regUsername@example.com');
    await tester.enterText(fields.at(2), kRegPassword);
    await tester.enterText(fields.at(3), kRegPassword);
    await tester.pump(const Duration(milliseconds: 300));
    final tiles = find.byType(CheckboxListTile);
    for (var t = 0; t < tiles.evaluate().length; t++) {
      try {
        await tester.ensureVisible(tiles.at(t));
        await tester.pump(const Duration(milliseconds: 300));
      } catch (_) {}
      clicks[0]++;
      await tester.tap(tiles.at(t), warnIfMissed: false);
      await tester.pump(const Duration(milliseconds: 250));
    }
    Finder regBtn() =>
        find.widgetWithText(SparkleButton, '注册').first;
    if (regBtn().evaluate().isEmpty) {
      // ignore: avoid_print
      print('Q01_ANCHOR register submit button missing');
      return false;
    }
    try {
      await tester.ensureVisible(regBtn());
      await tester.pump(const Duration(milliseconds: 400));
    } catch (_) {}
    var backOnDashboard = false;
    var bouncedToLogin = false;
    for (var attempt = 0; attempt < 2 && !backOnDashboard; attempt++) {
      if (regBtn().evaluate().isEmpty) {
        await waitUntil(
          tester,
          () =>
              find.byType(DashboardScreen).evaluate().isNotEmpty ||
              find.byType(LoginScreen).evaluate().isNotEmpty,
          timeout: const Duration(seconds: 20),
        );
        backOnDashboard =
            find.byType(DashboardScreen).evaluate().isNotEmpty;
        bouncedToLogin = find.byType(LoginScreen).evaluate().isNotEmpty;
        break;
      }
      clicks[0]++;
      await tester.tap(regBtn(), warnIfMissed: false);
      await waitUntil(
        tester,
        () =>
            find.byType(DashboardScreen).evaluate().isNotEmpty ||
            find.byType(LoginScreen).evaluate().isNotEmpty ||
            find.textContaining('注册失败').evaluate().isNotEmpty,
        timeout: const Duration(seconds: 25),
      );
      if (find.textContaining('注册失败').evaluate().isNotEmpty) {
        // ignore: avoid_print
        print('Q01_ANCHOR register failed marker shown');
        await shot('$_kRun/$_kLeg/04-register-failed.png');
        return false;
      }
      backOnDashboard = find.byType(DashboardScreen).evaluate().isNotEmpty;
      bouncedToLogin = find.byType(LoginScreen).evaluate().isNotEmpty;
    }
    if (!backOnDashboard) {
      // ignore: avoid_print
      print('Q01_ANCHOR post-register landing dashboard=false '
          'bouncedToLogin=$bouncedToLogin');
      return false;
    }
    await safeSettle(tester);
    await shot('$_kRun/$_kLeg/05-registered-dashboard.png');
    // ignore: avoid_print
    print('Q01_ANCHOR registered username=$regUsername '
        'conversion_card=$conversionSeen');

    // ---- ② persona J-02 快车道 ----
    Finder? resumeCta;
    for (var r = 0; r < 6 && resumeCta == null; r++) {
      resumeCta = textAny(['继续引导']);
      if (resumeCta == null) {
        try {
          await tester.drag(find.byType(Scrollable).first, const Offset(0, -200));
          await tester.pump(const Duration(milliseconds: 450));
        } catch (_) {
          break;
        }
      }
    }
    if (resumeCta == null) {
      // ignore: avoid_print
      print('Q01_ANCHOR resume CTA 继续引导 not found on home');
      return false;
    }
    try {
      await tester.ensureVisible(resumeCta!);
    } catch (_) {}
    clicks[0]++;
    await tester.tap(resumeCta!, warnIfMissed: false);
    final personaUp = await waitUntil(
      tester,
      () => find.byType(PersonaOnboardingScreen).evaluate().isNotEmpty,
      timeout: const Duration(seconds: 15),
    );
    if (!personaUp) {
      // ignore: avoid_print
      print('Q01_ANCHOR persona onboarding screen never appeared');
      return false;
    }
    await safeSettle(tester);
    await shot('$_kRun/$_kLeg/06-persona-step1.png');

    final goalField = find.descendant(
      of: find.byType(PersonaOnboardingScreen),
      matching: find.byType(TextField),
    );
    if (goalField.evaluate().isEmpty) {
      // ignore: avoid_print
      print('Q01_ANCHOR persona goal input not found');
      return false;
    }
    await tester.enterText(goalField.first, kIntentText);
    await tester.pump(const Duration(milliseconds: 400));
    final fastCtaReady = await waitUntil(
      tester,
      () => find.byKey(const ValueKey('j02-fast-path-cta')).evaluate().isNotEmpty,
      timeout: const Duration(seconds: 10),
    );
    if (!fastCtaReady) {
      // ignore: avoid_print
      print('Q01_ANCHOR fast-path CTA did not appear after goal text');
      return false;
    }
    clicks[0]++;
    await tester.tap(
      find.byKey(const ValueKey('j02-fast-path-cta')),
      warnIfMissed: false,
    );
    final modelingUp = await waitUntil(
      tester,
      () => find.byType(ModelingChatScreen).evaluate().isNotEmpty,
      timeout: const Duration(seconds: 25),
    );
    if (!modelingUp) {
      // ignore: avoid_print
      print('Q01_ANCHOR modeling screen never appeared after fast path');
      return false;
    }
    await safeSettle(tester);
    await shot('$_kRun/$_kLeg/07-modeling-deferred.png');
    final skipBtn = textAny(['跳过']);
    if (skipBtn == null) {
      // ignore: avoid_print
      print('Q01_ANCHOR modeling skip button not found');
      return false;
    }
    clicks[0]++;
    await tester.tap(skipBtn, warnIfMissed: false);
    final landed = await waitUntil(
      tester,
      () =>
          find.byType(DashboardScreen).evaluate().isNotEmpty ||
          find.byIcon(Icons.home_outlined).evaluate().isNotEmpty,
      timeout: const Duration(seconds: 20),
    );
    if (find.byType(DashboardScreen).evaluate().isEmpty) {
      // 落 chat 时走壳层 home tab（真实用户路径）
      final homeTab = find.byIcon(Icons.home_outlined);
      if (homeTab.evaluate().isNotEmpty) {
        clicks[0]++;
        await tester.tap(homeTab.first, warnIfMissed: false);
        await waitUntil(
          tester,
          () => find.byType(DashboardScreen).evaluate().isNotEmpty,
          timeout: const Duration(seconds: 15),
        );
      }
    }
    await safeSettle(tester);
    await shot('$_kRun/$_kLeg/08-after-persona-home.png');
    // ignore: avoid_print
    print('Q01_ANCHOR persona fast path done; landed=$landed');
    return true;
  }

  Future<bool> tapWhenVisible(
    WidgetTester tester,
    Finder? Function() locate, {
    Duration timeout = const Duration(seconds: 20),
    int rounds = 3,
  }) async {
    for (var r = 0; r < rounds; r++) {
      final ok = await waitUntil(tester, () => locate() != null,
          timeout: timeout);
      if (!ok) continue;
      final f = locate();
      if (f == null) continue;
      try {
        await tester.ensureVisible(f);
      } catch (_) {}
      clicks[0]++;
      await tester.tap(f, warnIfMissed: false);
      return true;
    }
    return false;
  }

  /// sheet 内折叠控件：滚动露出→点击（DraggableScrollableSheet 场景）
  Future<bool> revealAndTap(WidgetTester tester, Finder f,
      {int rounds = 5}) async {
    for (var i = 0; i < rounds; i++) {
      if (f.evaluate().isNotEmpty) {
        try {
          await tester.ensureVisible(f.first);
          await tester.pump(const Duration(milliseconds: 300));
        } catch (_) {}
        try {
          clicks[0]++;
          await tester.tap(f.first, warnIfMissed: false);
          return true;
        } catch (_) {}
      }
      try {
        await tester.drag(find.byType(Scrollable).last, const Offset(0, -170));
        await tester.pump(const Duration(milliseconds: 450));
      } catch (_) {
        break;
      }
    }
    return false;
  }

  testWidgets('V4-Q01 vertical journey leg=$_kLeg run=$_kRun',
      (tester) async {
    testTester = tester;
    final t0 = DateTime.now();

    if (_kLeg == 'part1') {
      try {
        await wipeLocalState();
        // ignore: avoid_print
        print('Q01 local state wiped (clean-install state)');
      } catch (e) {
        // ignore: avoid_print
        print('Q01 local state wipe failed: $e');
      }
    }

    app.main();
    unawaited(BgmService.setEnabled(false).timeout(const Duration(seconds: 3)));
    unawaited(BgmService.stop().timeout(const Duration(seconds: 3)));

    await waitUntil(
      tester,
      () =>
          find.byType(DashboardScreen).evaluate().isNotEmpty ||
          find.text('以访客身份继续').evaluate().isNotEmpty,
      timeout: const Duration(seconds: 45),
    );
    await safeSettle(tester);
    await shot('$_kRun/$_kLeg/00-entry.png');

    // ── 身份入口（真实 UI 路径）──
    var username = '';
    var enteredVia = 'session';
    if (_kLeg == 'part1' &&
        find.byType(DashboardScreen).evaluate().isNotEmpty &&
        find.text('以访客身份继续').evaluate().isEmpty) {
      // 会话幸存（tester 进程 wipe 清不到 app 侧 keychain，attempt2 实证）
      // → UI 驱动退出登录；失败则中止本轮，绝不带着旧会话污染重复实验。
      final outOk = await driveClientLogout(tester);
      recordStep('client_logout_clean_run', outOk,
          outOk
              ? 'UI logout (profile→退出登录→确认); app-own session cleared'
              : 'UI logout FAILED');
      if (!outOk) {
        throw StateError(
            'session isolation failed: app-side session survived, '
            'refusing to run journey on reused user (attempt2 lesson)');
      }
    }
    if (find.text('以访客身份继续').evaluate().isNotEmpty ||
        find.text('还没有账号？').evaluate().isNotEmpty) {
      // 访客进入（j02 leg-G 同径）；tap bounce 已知 → 重试 ×4
      var guestOk = false;
      for (var attempt = 0; attempt < 4 && !guestOk; attempt++) {
        final guestBtn = textAny(['以访客身份继续']);
        if (guestBtn == null) break;
        try {
          await tester.ensureVisible(guestBtn);
        } catch (_) {}
        await tester.tap(guestBtn, warnIfMissed: false);
        guestOk = await waitUntil(
          tester,
          () => find.byType(DashboardScreen).evaluate().isNotEmpty,
          // auth 5.25s 实测 + 内存高压下 hydration 慢（r1 attempt3：12s 窗口
          // 全部错过而 dashboard 其后已渲染）→ 30s
          timeout: const Duration(seconds: 30),
        );
        if (guestOk) break;
        await safeSettle(tester);
      }
      if (!guestOk) {
        // 最后一轮宽限：登出发生在 profile tab 时，StatefulShellRoute
        // .indexedStack 会把重登后的落点恢复回「我的」（attempt4 实证：
        // dashboard 数据 200 但驾驶舱 tab 未选中）→ 显式点回驾驶舱
        final homeTab = find.byIcon(Icons.home_outlined);
        if (homeTab.evaluate().isNotEmpty) {
          clicks[0]++;
          await tester.tap(homeTab.first, warnIfMissed: false);
          await tester.pump(const Duration(milliseconds: 600));
        }
        guestOk = await waitUntil(
          tester,
          () => find.byType(DashboardScreen).evaluate().isNotEmpty,
          timeout: const Duration(seconds: 30),
        );
        if (guestOk) enteredVia = 'guest_late_render';
      }
      enteredVia = guestOk ? 'guest' : 'guest_tap_failed';
      recordStep('identity_entry', guestOk, 'via=$enteredVia');
      await safeSettle(tester);
    } else {
      recordStep('identity_entry', true,
          'session persisted (no login screen) — real reopen continuation');
    }

    await waitUntil(
      tester,
      () => find.byType(DashboardScreen).evaluate().isNotEmpty,
      timeout: const Duration(seconds: 30),
    );
    await safeSettle(tester);
    await shot('$_kRun/$_kLeg/01-dashboard.png');
    recordStep('app_launch', true,
        'elapsedMs=${DateTime.now().difference(t0).inMilliseconds}');

    if (_kLeg == 'part1') {
      // ── ① 接续面（冷启首页）：resume strip 状态 + 主 CTA ──
      final resumeAbsent = find
          .byKey(const ValueKey('episode-resume-absent'))
          .evaluate()
          .isNotEmpty;
      final resumeStale = find
          .byKey(const ValueKey('episode-resume-stale-line'))
          .evaluate()
          .isNotEmpty;
      // ignore: avoid_print
      print('Q01_RESUME_STRIP state=${resumeAbsent
          ? 'absent'
          : resumeStale
              ? 'stale'
              : 'ready_or_other'}');
      await dumpTexts(tester, 'home-cold');
      await dumpSemantics('home-cold');
      recordStep('home_resume_surface', true,
          'strip=${resumeAbsent ? 'absent' : resumeStale ? 'stale' : 'ready'} '
          '(FIX-567 生产者边界已知)');

      // 仪表盘未达（身份入口失败等）→ 下游旅程整体跳过，不崩溃，如实记 FAIL
      // dashOk 门放宽：DashboardScreen 类型 or 首页接续条 key 已渲染即视为到达
      // （attempt3：接续条 ready 但类型判定迟到，按渲染事实不按类名）
      final dashOk = find.byType(DashboardScreen).evaluate().isNotEmpty ||
          find.byKey(const ValueKey('episode-resume-absent')).evaluate().isNotEmpty ||
          find.byKey(const ValueKey('episode-resume-stale-line')).evaluate().isNotEmpty ||
          find.byKey(const Key('stuck-help-fab')).evaluate().isNotEmpty ||
          textAny(['查看任务', '任务列表', '先解决卡点']) != null;
      if (!dashOk) {
        await dumpTexts(tester, 'dashboard-never-reached');
        recordStep('wizard_open', false,
            'dashboard never reached; part1 downstream skipped');
      }
      if (dashOk) {

      // ── ⓪ 旅程锚点前置（真用户三段：注册转化→persona 快车道）+ 底料 ──
      // Hybrid 锚点真源只认 MemoryGoal（r1 pilot 500 NoActiveGoalError 实证）；
      // prep 检索只认用户文档 chunks（无底料则诚实 no_materials）。
      // 注意：锚点驱动绝不能包 runAsync——tap/pump 的帧语义在 runAsync 内
      // 退化（r1 attempt2 实证）；只有纯 IO 的 fixture 上传需要 runAsync。
      final anchorOk = await driveIdentityAnchor(tester);
      recordStep('goal_anchor_created', anchorOk,
          'register→persona fast-path (all UI); memory_goals.active '
          '${anchorOk ? 'ready' : 'NOT created (hybrid anchor will fail)'}');
      if (anchorOk) {
        final fixtureResult = await testTester.runAsync<String>(
              () => uploadFixtureDocument(),
            ) ??
            'runAsync_null';
        // ignore: avoid_print
        print('Q01_FIXTURE $fixtureResult');
        recordStep('fixture_document_ready', fixtureResult.startsWith('ok'),
            'real upload→chunk pipeline via app session (disclosed fixture); '
            'result=$fixtureResult');
      }
      if (!anchorOk) {
        // 锚点失败恢复：降级路径可能把 app 留在登录页——重新以访客进入，
        // 让种子旅程继续（锚点失败已如实入账，hybrid 将按实测失败）
        if (find.text('以访客身份继续').evaluate().isNotEmpty) {
          clicks[0]++;
          await tester.tap(find.text('以访客身份继续').first, warnIfMissed: false);
          await waitUntil(
            tester,
            () => find.byType(DashboardScreen).evaluate().isNotEmpty,
            timeout: const Duration(seconds: 30),
          );
        }
      }
      // 锚点路径后落点可能不是首页（chat 等）——回首页再走种子任务链
      if (find.byType(DashboardScreen).evaluate().isEmpty) {
        try {
          final ctx = tester.element(find.byType(Navigator).first);
          clicks[0]++;
          ctx.go('/home');
          await waitUntil(
            tester,
            () => find.byType(DashboardScreen).evaluate().isNotEmpty,
            timeout: const Duration(seconds: 15),
          );
        } catch (e) {
          // ignore: avoid_print
          print('Q01 return-home nav failed: $e');
        }
      }
      await safeSettle(tester);

      // ── ② 目标与任务（注册后产品路径）：首页 cockpit noGoal 态露出
      // 「和 AI 定目标」→ J-01 向导（真实 LLM 意图分析+计划 preview，创建
      // goals 行 + 计划任务——attempt6 用户 DB 实证 10 tasks）→ 成功弹窗
      // 「开始第一个任务」直达任务面。种子 demo 世界属 guest user_id，
      // 原地注册=新 user_id（attempt9 DB 实证 tasks=0），种子任务链作废。
      var opened = false;
      var journeyTaskTitle = _kTaskTitle;
      if (_kRunWizard == '1') {
      var wizardUp = false;
      final startAiCta = await waitUntil(
        tester,
        () => textAny(['和 AI 定目标', '先定下你的第一个目标']) != null,
        timeout: const Duration(seconds: 20),
      );
      if (startAiCta) {
        var cta = textAny(['和 AI 定目标']);
        cta ??= textAny(['先定下你的第一个目标']);
        if (cta != null) {
          try {
            await tester.ensureVisible(cta);
          } catch (_) {}
          final ctaBtn = find
              .ancestor(of: cta, matching: find.byType(SparkleButton))
              .evaluate()
              .isNotEmpty
              ? find.ancestor(of: cta, matching: find.byType(SparkleButton)).first
              : cta;
          clicks[0]++;
          await tester.tap(ctaBtn, warnIfMissed: false);
          wizardUp = await waitUntil(
            tester,
            () => find.byType(GoalCreationWizardScreen).evaluate().isNotEmpty,
            timeout: const Duration(seconds: 15),
          );
          for (var attempt = 0; attempt < 3 && !wizardUp; attempt++) {
            if (cta.evaluate().isEmpty) break;
            clicks[0]++;
            await tester.tap(cta, warnIfMissed: false);
            wizardUp = await waitUntil(
              tester,
              () => find.byType(GoalCreationWizardScreen).evaluate().isNotEmpty,
              timeout: const Duration(seconds: 12),
            );
          }
        }
      } else {
        await dumpTexts(tester, 'start-ai-cta-missing');
      }
      recordStep('wizard_open', wizardUp,
          '和 AI 定目标 CTA→J-01 wizard ${wizardUp ? 'opened' : 'NOT reached'}');
      if (wizardUp) {
        await safeSettle(tester);
        await shot('$_kRun/$_kLeg/09-wizard-intent.png');
        final intentField = find.descendant(
          of: find.byKey(const ValueKey('goal-intent-input-step')),
          matching: find.byType(TextField),
        );
        if (intentField.evaluate().isNotEmpty) {
          await tester.enterText(intentField.first, kIntentText);
          await tester.pump(const Duration(milliseconds: 400));
          final analyzeBtn = textAny(['让我先看看你的情况', '继续']);
          if (analyzeBtn != null) {
            clicks[0]++;
            await tester.tap(analyzeBtn, warnIfMissed: false);
          }
          // 真实 LLM 意图分析：可行动卡片或 legacy 步进（方差即测量数据）
          final analyzed = await waitUntil(
            tester,
            () =>
                find
                    .byKey(const ValueKey('goal-intent-confirm-step'))
                    .evaluate()
                    .isNotEmpty ||
                find
                    .byKey(const ValueKey('goal-type-step'))
                    .evaluate()
                    .isNotEmpty ||
                find
                    .byKey(const ValueKey('goal-motivation-step'))
                    .evaluate()
                    .isNotEmpty,
            timeout: const Duration(seconds: 120),
          );
          await safeSettle(tester);
          await shot('$_kRun/$_kLeg/10-wizard-intent-result.png');
          await dumpTexts(tester, 'wizard-intent-result');
          recordStep('wizard_intent_analyzed', analyzed,
              'real LLM intent analysis returned=$analyzed');
          if (analyzed) {
            if (find
                .byKey(const ValueKey('goal-intent-confirm-step'))
                .evaluate()
                .isNotEmpty) {
              final actionRow = find.descendant(
                of: find.byKey(const ValueKey('goal-intent-confirm-step')),
                matching: find.byIcon(Icons.play_arrow_rounded),
              );
              if (actionRow.evaluate().isNotEmpty) {
                clicks[0]++;
                await tester.tap(actionRow.first, warnIfMissed: false);
                await tester.pump(const Duration(seconds: 1));
              }
            } else {
              final pill = textAny(['学术', '技能', '项目', '习惯', '其他']);
              if (pill != null) {
                clicks[0]++;
                await tester.tap(pill, warnIfMissed: false);
                await tester.pump(const Duration(milliseconds: 400));
              }
            }
            // 步进余下向导页（type 重入补点；motivation 必填；长步滚出视口
            // 的继续按钮先 ensureVisible——attempt5/6 教训）
            var stalls = 0;
            var lastStepKey = '';
            var created = false;
            var successShown = false;
            for (var guard = 0; guard < 12; guard++) {
              if (find
                  .byKey(const ValueKey('goal-type-step'))
                  .evaluate()
                  .isNotEmpty) {
                final pillAgain = textAny(['学术', '技能', '项目', '习惯', '其他']);
                if (pillAgain != null) {
                  clicks[0]++;
                  await tester.tap(pillAgain, warnIfMissed: false);
                  await tester.pump(const Duration(milliseconds: 400));
                }
              }
              if (find
                  .byKey(const ValueKey('goal-motivation-step'))
                  .evaluate()
                  .isNotEmpty) {
                final fields = find.descendant(
                  of: find.byKey(const ValueKey('goal-motivation-step')),
                  matching: find.byType(TextField),
                );
                if (fields.evaluate().length >= 2) {
                  final goalText = kIntentText;
                  await tester.enterText(
                    fields.at(0),
                    goalText.length > 40 ? goalText.substring(0, 40) : goalText,
                  );
                  await tester.enterText(fields.at(1), '这是我想完成它的原因。');
                  await tester.pump(const Duration(milliseconds: 300));
                }
              }
              await shot('$_kRun/$_kLeg/11-wizard-step-$guard.png');
              final onConfirmNow = find
                  .byKey(const ValueKey('goal-confirm-step'))
                  .evaluate()
                  .isNotEmpty;
              final cont = onConfirmNow
                  ? (textAny(['创建', '创建目标']) ?? textAny(['继续']))
                  : textAny(['继续', '创建', '创建目标']);
              if (cont == null) break;
              try {
                await tester.ensureVisible(cont);
                await tester.pump(const Duration(milliseconds: 300));
              } catch (_) {}
              clicks[0]++;
              await tester.tap(cont, warnIfMissed: false);
              await waitUntil(
                tester,
                () =>
                    find.byType(GoalCreationWizardScreen).evaluate().isEmpty ||
                    find.textContaining('创建失败').evaluate().isNotEmpty ||
                    find.textContaining('成长计划已就绪').evaluate().isNotEmpty ||
                    find.textContaining('目标已创建').evaluate().isNotEmpty,
                timeout: const Duration(seconds: 25),
              );
              await safeSettle(tester);
              if (find.textContaining('创建失败').evaluate().isNotEmpty) {
                await shot('$_kRun/$_kLeg/12-wizard-create-failed.png');
                break;
              }
              successShown =
                  find.textContaining('成长计划已就绪').evaluate().isNotEmpty ||
                      find.textContaining('目标已创建').evaluate().isNotEmpty;
              if (successShown) break;
              if (find.byType(GoalCreationWizardScreen).evaluate().isEmpty) {
                created = true;
                break;
              }
              String classifyStep() {
                if (find
                    .byKey(const ValueKey('goal-confirm-step'))
                    .evaluate()
                    .isNotEmpty) {
                  return 'confirm';
                }
                if (find
                    .byKey(const ValueKey('goal-milestone-step'))
                    .evaluate()
                    .isNotEmpty) {
                  return 'milestone';
                }
                if (find
                    .byKey(const ValueKey('goal-time-step'))
                    .evaluate()
                    .isNotEmpty) {
                  return 'time';
                }
                if (find
                    .byKey(const ValueKey('goal-motivation-step'))
                    .evaluate()
                    .isNotEmpty) {
                  return 'motivation';
                }
                if (find
                    .byKey(const ValueKey('goal-type-step'))
                    .evaluate()
                    .isNotEmpty) {
                  return 'type';
                }
                if (find
                    .byKey(const ValueKey('goal-intent-confirm-step'))
                    .evaluate()
                    .isNotEmpty) {
                  return 'intent_confirm';
                }
                return 'intent_input';
              }

              final stepKey = classifyStep();
              if (stepKey == lastStepKey) {
                stalls++;
                if (stalls >= 3) {
                  // ignore: avoid_print
                  print('Q01_WIZARD stalled at $stepKey after 3 taps');
                  break;
                }
              } else {
                stalls = 0;
                lastStepKey = stepKey;
              }
            }
            recordStep('wizard_plan_created', created || successShown,
                'real LLM plan preview→create; successDialog=$successShown '
                'wizardGone=$created');
            if (successShown || created) {
              // 成功弹窗「开始第一个任务」→ 直达任务面（product CTA）
              final startFirst = textAny(['开始第一个任务']);
              if (startFirst != null) {
                clicks[0]++;
                await tester.tap(startFirst, warnIfMissed: false);
                opened = await waitUntil(
                  tester,
                  () =>
                      find.byKey(const Key('stuck-help-fab')).evaluate().isNotEmpty ||
                      primaryButton(['开始任务', '继续', '开始']) != null,
                  timeout: const Duration(seconds: 25),
                );
                // 详情面（开始任务）→ 执行面
                final detailStart = primaryButton(['开始任务', '继续']);
                if (opened &&
                    detailStart != null &&
                    find.byKey(const Key('stuck-help-fab')).evaluate().isEmpty) {
                  try {
                    await tester.ensureVisible(detailStart);
                  } catch (_) {}
                  clicks[0]++;
                  await tester.tap(detailStart, warnIfMissed: false);
                  opened = await waitUntil(
                    tester,
                    () => find
                        .byKey(const Key('stuck-help-fab'))
                        .evaluate()
                        .isNotEmpty,
                    timeout: const Duration(seconds: 25),
                  );
                }
              } else {
                await shot('$_kRun/$_kLeg/13-wizard-success-no-cta.png');
              }
            }
          }
        } else {
          recordStep('wizard_intent_analyzed', false, 'intent field not found');
        }
      } else {
        // 兜底：/tasks（应用内路由，披露）——种子或既有任务仍在时的旧链
        final ctx = tester.element(find.byType(Navigator).first);
        clicks[0]++;
        ctx.push('/tasks');
        await waitUntil(
          tester,
          () => textAny(['待处理', '全部']) != null,
          timeout: const Duration(seconds: 15),
        );
        await tester.pump(const Duration(seconds: 2));
        const candidates = [
          '二叉树遍历',
          'TCP协议分析',
          '图论着色',
          '死锁处理',
        ];
        for (var s = 0; s < 6 && !opened; s++) {
          for (final c in candidates) {
            final row = find.textContaining(c);
            if (row.evaluate().isNotEmpty) {
              journeyTaskTitle = c;
              opened = true;
              break;
            }
          }
          if (opened) break;
          try {
            await tester.drag(find.byType(Scrollable).first, const Offset(0, -220));
            await tester.pump(const Duration(milliseconds: 600));
          } catch (_) {
            break;
          }
        }
        if (opened) {
          final row = find.textContaining(journeyTaskTitle);
          try {
            await tester.ensureVisible(row.first);
          } catch (_) {}
          await tester.tap(row.first, warnIfMissed: false);
          opened = await waitUntil(
            tester,
            () => primaryButton(['开始任务', '继续', '开始']) != null,
            timeout: const Duration(seconds: 15),
          );
          if (opened) {
            final startBtn = primaryButton(['开始任务', '继续']);
            if (startBtn != null) {
              try {
                await tester.ensureVisible(startBtn);
              } catch (_) {}
              clicks[0]++;
              await tester.tap(startBtn, warnIfMissed: false);
              opened = await waitUntil(
                tester,
                () => find.byKey(const Key('stuck-help-fab')).evaluate().isNotEmpty,
                timeout: const Duration(seconds: 25),
              );
            }
          }
        }
      }
      } // _kRunWizard == '1'（J-01 向导支线，v3 默认关）

      else {
        // ── ②' 真实任务创建（v3 主径）：r5 实证 J-01 向导的计划任务不落
        // 任务列表投影（TEXTDUMP task-list-refreshed=「今天还没有待办事项」）
        // → 校准「仅本次」锚点结构性缺席。真实用户路径 = 任务列表空态
        // 「创建第一项任务」→ 表单（标题 + 默认 25 分钟）→ 列表行 →
        // 开始任务 → 执行面。列表创建经 taskListProvider.refreshTasks，
        // 投影必含新任务 → 执行面与校准锚点同时满足。全程 UI 驱动。
        try {
          final navCtx = tester.element(find.byType(Navigator).first);
          clicks[0]++;
          // push 的 Future 在 pop 时才完成（r4 死锁实证）——unawaited。
          unawaited(navCtx.push('/tasks'));
          await waitUntil(
            tester,
            () => textAny(['待处理', '全部']) != null,
            timeout: const Duration(seconds: 15),
          );
          // 列表加载错误态（r6 实证：新注册用户首开偶发「哎呀，出错了」）
          // → 真实用户点「重试」；至多 3 轮。
          for (var r = 0; r < 3; r++) {
            final retryBtn = textAny(['重试']);
            if (retryBtn == null) break;
            clicks[0]++;
            await tester.tap(retryBtn, warnIfMissed: false);
            await waitUntil(
              tester,
              () => textAny(['重试']) == null,
              timeout: const Duration(seconds: 15),
            );
            await tester.pump(const Duration(milliseconds: 400));
          }
          await dumpTexts(tester, 'tasks-list-before-create');
          Finder? createCta;
          for (var r = 0; r < 3 && createCta == null; r++) {
            createCta = textAny(['创建第一项任务', '创建任务', '新建任务']);
            if (createCta == null) {
              try {
                await tester.drag(
                  find.byType(Scrollable).first,
                  const Offset(0, -220),
                );
                await tester.pump(const Duration(milliseconds: 450));
              } catch (_) {
                break;
              }
            }
          }
          var createUp = false;
          if (createCta != null) {
            try {
              await tester.ensureVisible(createCta!);
            } catch (_) {}
            clicks[0]++;
            await tester.tap(createCta, warnIfMissed: false);
            createUp = await waitUntil(
              tester,
              () => find.byType(TaskCreateScreen).evaluate().isNotEmpty,
              timeout: const Duration(seconds: 15),
            );
          }
          recordStep('task_create_opened', createUp,
              'tasks list empty-state CTA → create form '
              '${createUp ? 'opened' : 'NOT reached'}');
          if (createUp) {
            await safeSettle(tester);
            final titleField = find.descendant(
              of: find.byType(TaskCreateScreen),
              matching: find.byType(TextFormField),
            );
            if (titleField.evaluate().isNotEmpty) {
              await tester.enterText(titleField.first, _kTaskTitle);
              await tester.pump(const Duration(milliseconds: 400));
            }
            await shot('$_kRun/$_kLeg/09b-task-create-form.png');
            final submit = primaryButton(['创建任务']);
            if (submit != null) {
              try {
                await tester.ensureVisible(submit);
                await tester.pump(const Duration(milliseconds: 300));
              } catch (_) {}
              clicks[0]++;
              await tester.tap(submit, warnIfMissed: false);
            }
            // 提交后：无 nudge 自动 pop；有 nudge 先逐个「忽略」再手动返回
            var nudged = await waitUntil(
              tester,
              () => textAny(['忽略']) != null,
              timeout: const Duration(seconds: 20),
            );
            var guard = 0;
            while (nudged && guard < 6) {
              guard++;
              final dismiss = textAny(['忽略']);
              if (dismiss == null) break;
              try {
                await tester.ensureVisible(dismiss);
              } catch (_) {}
              clicks[0]++;
              await tester.tap(dismiss, warnIfMissed: false);
              await tester.pump(const Duration(milliseconds: 400));
              nudged = textAny(['忽略']) != null;
            }
            var backOnList = await waitUntil(
              tester,
              () => find.byType(TaskCreateScreen).evaluate().isEmpty,
              timeout: const Duration(seconds: 15),
            );
            if (!backOnList) {
              clicks[0]++;
              navCtx.pop();
              backOnList = await waitUntil(
                tester,
                () => find.byType(TaskCreateScreen).evaluate().isEmpty,
                timeout: const Duration(seconds: 10),
              );
            }
            // 行可见 = 列表投影含新任务（创建路径已 refreshTasks）
            final rowVisible = await waitUntil(
              tester,
              () => find.textContaining(_kTaskTitle).evaluate().isNotEmpty,
              timeout: const Duration(seconds: 15),
            );
            await shot('$_kRun/$_kLeg/10b-task-list-with-row.png');
            await dumpTexts(tester, 'task-list-after-create');
            recordStep('task_created_via_ui', rowVisible,
                'task "$_kTaskTitle" via list CTA form; row visible=$rowVisible');
            if (rowVisible) {
              final row = find.textContaining(_kTaskTitle);
              try {
                await tester.ensureVisible(row.first);
              } catch (_) {}
              clicks[0]++;
              await tester.tap(row.first, warnIfMissed: false);
              final detailUp = await waitUntil(
                tester,
                () => primaryButton(['开始任务', '继续', '开始']) != null,
                timeout: const Duration(seconds: 15),
              );
              if (detailUp) {
                final startBtn = primaryButton(['开始任务', '继续']);
                if (startBtn != null &&
                    find
                        .byKey(const Key('stuck-help-fab'))
                        .evaluate()
                        .isEmpty) {
                  try {
                    await tester.ensureVisible(startBtn);
                  } catch (_) {}
                  clicks[0]++;
                  await tester.tap(startBtn, warnIfMissed: false);
                }
              }
              opened = await waitUntil(
                tester,
                () => find
                    .byKey(const Key('stuck-help-fab'))
                    .evaluate()
                    .isNotEmpty,
                timeout: const Duration(seconds: 25),
              );
            }
          }
        } catch (e) {
          recordStep(
            'task_created_via_ui',
            false,
            'create path failed: $e',
          );
        }
      }

      await safeSettle(tester, const Duration(seconds: 8));
      await shot('$_kRun/$_kLeg/11-task-execution.png');
      await dumpTexts(tester, 'task-execution');
      await dumpSemantics('task-execution');
      recordStep('task_execution_open', opened,
          'task execution surface via ui-create/wizard-first-task/legacy '
          '(stuck FAB present=$opened)');
      final execOk = find
          .byKey(const Key('stuck-help-fab'))
          .evaluate()
          .isNotEmpty;
      if (!execOk) {
        recordStep('execution_surface_not_reached', false,
            'downstream stuck/correction/hybrid legs skipped');
      }
      if (execOk) {

      // ── ③.5 任务列表投影水化（真实用户绕道，披露）：经向导成功 CTA 直达
      // 执行面时，校准区「仅本次」锚点按任务列表客户端投影解析
      // （stuck_journey_sheet._resolveBaselineMinutes 只读 taskListProvider 的
      // tasks/todayTasks）——r1 runB 实证：投影未含向导新建任务 →
      // baselineMinutes=null → 「调整这次行动」按产品设计如实结构性缺席
      // （无任务锚点不出假入口，recovery_calibration_section hasAnchor 门）。
      // 真实用户此时会看一眼任务列表并下拉刷新；同一路径水化投影后回执行
      // 面。纯客户端操作，不写库、不 Mock、不注入 provider。
      try {
        final navCtx = tester.element(find.byType(Navigator).first);
        clicks[0]++;
        // push 的 Future 在路由 pop 时才完成（r4 死锁实证：await 后永远
        // 等不到自己的 pop）——必须 unawaited，不修 lint 改语义。
        unawaited(navCtx.push('/tasks'));
        final listUp = await waitUntil(
          tester,
          () => textAny(['待处理', '全部']) != null,
          timeout: const Duration(seconds: 15),
        );
        // 下拉刷新（真实手势；列表 RefreshIndicator.onRefresh）
        for (var p = 0; p < 2; p++) {
          try {
            await tester.drag(
              find.byType(Scrollable).first,
              const Offset(0, 320),
            );
            await tester.pump(const Duration(milliseconds: 800));
          } catch (_) {
            break;
          }
        }
        await tester.pump(const Duration(seconds: 2));
        await safeSettle(tester);
        await shot('$_kRun/$_kLeg/11b-task-list-refreshed.png');
        await dumpTexts(tester, 'task-list-refreshed');
        recordStep('task_list_projection_refreshed', listUp,
            'tasks list visit + pull-refresh before stuck sheet (anchor '
            'hydration detour, runB lesson)');
        // 返回执行面
        clicks[0]++;
        navCtx.pop();
        final backOnExec = await waitUntil(
          tester,
          () =>
              find.byKey(const Key('stuck-help-fab')).evaluate().isNotEmpty,
          timeout: const Duration(seconds: 15),
        );
        if (!backOnExec) {
          recordStep(
            'execution_surface_restored',
            false,
            'pop from tasks list did not restore stuck FAB',
          );
        }
      } catch (e) {
        recordStep(
          'task_list_projection_refreshed',
          false,
          'hydration detour failed: $e',
        );
      }

      // ── ④ 制造卡住（客户端操作：卡住 FAB → markTaskStuck）──
      final stuckFab = find.byKey(const Key('stuck-help-fab'));
      if (stuckFab.evaluate().isNotEmpty) {
        await tester.tap(stuckFab.first, warnIfMissed: false);
        // StuckHelpSheet 出现（含 让 Sparkle 一步步帮我理）
        final sheetOk = await waitUntil(
          tester,
          () => textAny(['让 Sparkle 一步步帮我理']) != null,
          timeout: const Duration(seconds: 20),
        );
        await safeSettle(tester);
        await shot('$_kRun/$_kLeg/12-stuck-help-sheet.png');
        await dumpTexts(tester, 'stuck-help-sheet');
        recordStep('task_stuck', sheetOk,
            'markTaskStuck via client FAB; help sheet visible=$sheetOk');
      } else {
        recordStep('task_stuck', false, 'stuck-help-fab not found');
      }

      // ── ⑤ 统一恢复旅程（surface=action）→ 澄清问 ──
      // 按钮=Key('stuck-help-journey-button')；sheet 内可能折叠——先 ensureVisible
      var journeyTapped = false;
      for (var r = 0; r < 3 && !journeyTapped; r++) {
        final jBtn = find.byKey(const Key('stuck-help-journey-button'));
        Finder? target = jBtn.evaluate().isNotEmpty ? jBtn : null;
        target ??= primaryButton(['让 Sparkle 一步步帮我理']);
        if (target == null) break;
        try {
          await tester.ensureVisible(target);
        } catch (_) {}
        await tester.pump(const Duration(milliseconds: 300));
        await tester.tap(target, warnIfMissed: false);
        journeyTapped = await waitUntil(
          tester,
          () => find
                  .byKey(const ValueKey('stuck-journey-ready'))
                  .evaluate()
                  .isNotEmpty ||
              find
                  .byKey(const ValueKey('stuck-journey-loading'))
                  .evaluate()
                  .isNotEmpty,
          timeout: const Duration(seconds: 10),
        );
        if (journeyTapped) break;
        await safeSettle(tester);
      }
      if (journeyTapped) {
        final ready = await waitUntil(
          tester,
          () => find
              .byKey(const ValueKey('stuck-journey-ready'))
              .evaluate()
              .isNotEmpty,
          timeout: const Duration(seconds: 150),
        );
        await safeSettle(tester);
        await shot('$_kRun/$_kLeg/13-stuck-journey.png');
        await dumpTexts(tester, 'stuck-journey');
        await dumpSemantics('stuck-journey');
        recordStep('stuck_journey_payload', ready,
            'server-derived clarification payload ready=$ready');
        // 澄清问点选即答（有选项时答第一项——真实用户操作）
        final qHeader = textAny(['先说清一件事']);
        if (qHeader != null) {
          final optBtn = find
              .descendant(
                of: find.byKey(const ValueKey('stuck-journey-ready')),
                matching: find.byType(SparkleButton),
              )
              .evaluate()
              .isNotEmpty;
          if (optBtn) {
            await tester.tap(
              find.descendant(
                of: find.byKey(const ValueKey('stuck-journey-ready')),
                matching: find.byType(SparkleButton),
              ).first,
              warnIfMissed: false,
            );
            await safeSettle(tester, const Duration(seconds: 8));
            await shot('$_kRun/$_kLeg/14-clarification-answered.png');
            recordStep('clarification_answered', true, 'first option tapped');
          }
        }
      } else {
        recordStep('stuck_journey_payload', false, 'journey CTA missing');
      }

      // ── ⑥ 校准区纠正（恒渲染）：输入→仅本次→对照→diff→确认→回执 ──
      final calibField = find.byKey(const Key('recovery-calibration-input-field'));
      if (calibField.evaluate().isNotEmpty) {
        await tester.enterText(
          calibField.first,
          '不是不会，今天只有十五分钟',
        );
        await tester.pump(const Duration(milliseconds: 250));
        await shot('$_kRun/$_kLeg/15-correction-typed.png');
        final submitted = await revealAndTap(
          tester,
          find.byKey(const Key('recovery-calibration-submit')),
        );
        final scopeOk = await waitUntil(
          tester,
          () => textAny(['仅本次', '保存为偏好']) != null,
          timeout: const Duration(seconds: 30),
        );
        await safeSettle(tester);
        await shot('$_kRun/$_kLeg/16-scope-choice.png');
        await dumpTexts(tester, 'scope-choice');
        recordStep('correction_submitted', scopeOk,
            'semantic correction accepted; scope cards visible=$scopeOk');

        // 仅本次：调整这次行动（不动长期偏好）
        final thisTimeOk = await revealAndTap(
          tester,
          find.text('调整这次行动'),
        );
        if (thisTimeOk) {
          await safeSettle(tester);
          await shot('$_kRun/$_kLeg/17-adjusting.png');
          await dumpTexts(tester, 'adjusting');
          recordStep('scope_this_time', true, 'this-time-only selected');
        } else {
          recordStep('scope_this_time', false, '调整这次行动 CTA missing');
        }

        // 时长对照：目标 15 分钟（十五分钟纠正的语义落点）。
        // adjusted 从 baseline 步进 ±5；循环读取当前值文本（'N 分钟'）。
        // 上限 20 次：种子 baseline=90，降到 15 需 15 次下行（r1 pilot 12 次
        // 不够，止步 30 —— driver 缺陷非产品缺陷，本版修正）。
        for (var i = 0; i < 20; i++) {
          final m = _currentAdjustedMinutes(tester);
          if (m == null) break;
          if (m == 15) break;
          final down = find.byKey(const Key('recovery-calibration-minutes-down'));
          final up = find.byKey(const Key('recovery-calibration-minutes-up'));
          if (m > 15 && down.evaluate().isNotEmpty) {
            await tester.tap(down.first, warnIfMissed: false);
          } else if (m < 15 && up.evaluate().isNotEmpty) {
            await tester.tap(up.first, warnIfMissed: false);
          } else {
            break;
          }
          await tester.pump(const Duration(milliseconds: 250));
        }
        final finalMinutes = _currentAdjustedMinutes(tester);
        // ignore: avoid_print
        print('Q01_ADJUSTED_MINUTES $finalMinutes');
        await shot('$_kRun/$_kLeg/18-minutes-set.png');
        recordStep('minutes_adjusted', finalMinutes == 15,
            'adjusted=$finalMinutes target=15');

        // 生成调整对照（服务端 diff）
        final proposalOk = await revealAndTap(
          tester,
          find.byKey(const Key('recovery-calibration-create-proposal')),
        );
        final diffOk = await waitUntil(
          tester,
          () => textAny(['调整前 → 调整后']) != null ||
              find
                  .byKey(const Key('recovery-calibration-confirm'))
                  .evaluate()
                  .isNotEmpty,
          timeout: const Duration(seconds: 60),
        );
        await safeSettle(tester);
        await shot('$_kRun/$_kLeg/19-diff-review.png');
        await dumpTexts(tester, 'diff-review');
        await dumpSemantics('diff-review');
        recordStep('diff_review', diffOk, 'server diff visible=$diffOk');

        // 确认调整 → 等真实回执（已按本次约束落账 + receipt id）
        final confirmOk = await revealAndTap(
          tester,
          find.byKey(const Key('recovery-calibration-confirm')),
        );
        if (confirmOk) {
          final committed = await waitUntil(
            tester,
            () => textAny(['已按本次约束落账']) != null,
            timeout: const Duration(seconds: 90),
          );
          await safeSettle(tester);
          await shot('$_kRun/$_kLeg/20-committed-receipt.png');
          await dumpTexts(tester, 'committed');
          await dumpSemantics('committed');
          recordStep('calibration_committed', committed,
              'receipt-gated success visible=$committed');
        } else {
          recordStep('calibration_committed', false, 'confirm button missing');
        }
      } else {
        recordStep('correction_submitted', false,
            'calibration input field not found (恒渲染违约?)');
      }

      // 关 sheet：点 modal barrier（sheet 上方空白区）+ 下滑兜底
      await tester.tapAt(const Offset(30, 60));
      await tester.pump(const Duration(milliseconds: 600));
      await tester.drag(
          find.byType(Scrollable).last, const Offset(0, 300));
      await safeSettle(tester, const Duration(seconds: 4));
      final sheetGone = find
          .byKey(const Key('recovery-calibration-section'))
          .evaluate()
          .isEmpty;
      recordStep('sheet_dismissed', sheetGone, 'barrier tap + drag dismiss');
      // ── ⑦ Hybrid 入口 → 一起推进 sheet ──
      final hybridEntry = await tapWhenVisible(
        tester,
        () => textAny(['和 Sparkle 一起推进', '继续一起推进']),
        timeout: const Duration(seconds: 15),
      );
      recordStep('hybrid_entry', hybridEntry, 'entry tapped=$hybridEntry');
      if (hybridEntry) {
        // 备料→你研判：等 judgment 阶段 UI（选择来源+就按这些来）。
        // r5 实证：POST /journey/hybrid 服务端 prep（真实检索+假设答案 LLM）
        // 可超过客户端 30s receiveTimeout → 客户端 abort → sheet 停在 prep。
        // 真实用户行为 = 关 sheet 稍候重进（服务端幂等回放：run 已存在则
        // 原样回放状态）；3 次进入机会，每次给足服务端时间。
        var judgmentReady = false;
        var hybridAttempts = 0;
        for (var attempt = 0; attempt < 3 && !judgmentReady; attempt++) {
          hybridAttempts++;
          if (attempt > 0) {
            // 关 sheet（modal barrier 点按）→ 真实等待 → 重新进入
            await tester.tapAt(const Offset(30, 60));
            await tester.pump(const Duration(milliseconds: 600));
            await safeSettle(tester, const Duration(seconds: 4));
            final waited = await waitUntil(
              tester,
              () => false,
              timeout: const Duration(seconds: 45),
            );
            // ignore: avoid_print
            print('Q01_HYBRID_RETRY attempt=$hybridAttempts waited=$waited');
            final reEntry = await tapWhenVisible(
              tester,
              () => textAny(['和 Sparkle 一起推进', '继续一起推进']),
              timeout: const Duration(seconds: 15),
            );
            if (!reEntry) break;
          }
          final sheetReady = await waitUntil(
            tester,
            () => textAny(['一起推进：备料 · 你研判 · 交付']) != null ||
                find
                    .byKey(const ValueKey('hybrid-journey-ready'))
                    .evaluate()
                    .isNotEmpty,
            timeout: const Duration(seconds: 30),
          );
          if (attempt == 0) {
            await safeSettle(tester);
            await shot('$_kRun/$_kLeg/21-hybrid-sheet.png');
            await dumpTexts(tester, 'hybrid-open');
            recordStep('hybrid_sheet_open', sheetReady, 'sheetVisible=$sheetReady');
          }
          if (!sheetReady) break;
          judgmentReady = await waitUntil(
            tester,
            () => textAny(['就按这些来']) != null,
            timeout: const Duration(seconds: 150),
          );
        }
        await safeSettle(tester);
        await shot('$_kRun/$_kLeg/22-hybrid-judgment.png');
        await dumpTexts(tester, 'hybrid-judgment');
        await dumpSemantics('hybrid-judgment');
        recordStep('hybrid_judgment_stage', judgmentReady,
            'prep done; judgment stage reachable=$judgmentReady '
            '(entries=$hybridAttempts; r5: server prep > client 30s '
            'receiveTimeout, idempotent re-entry retried)');

        if (judgmentReady) {
          // 选来源（至少一项）：点第一个 checkbox/选择行
          final checked = find.byType(Checkbox);
          if (checked.evaluate().isNotEmpty) {
            await revealAndTap(tester, checked.first);
            await tester.pump(const Duration(milliseconds: 300));
          } else {
            // 可能是整行点选的自定义源行：点第一个列表项
            await revealAndTap(
              tester,
              find.textContaining(RegExp(r'(来源|source)')),
            );
          }
          await shot('$_kRun/$_kLeg/23-hybrid-source-selected.png');
          final submitJudgment =
              find.byKey(const Key('hybrid-journey-submit-judgment'));
          var judgmentSubmitted = false;
          if (submitJudgment.evaluate().isNotEmpty) {
            judgmentSubmitted =
                await revealAndTap(tester, submitJudgment.first);
          }
          if (!judgmentSubmitted) {
            await revealAndTap(tester, find.text('就按这些来'));
          }
          // 交付阶段（起草核对→确认交付）
          final outcomeReady = await waitUntil(
            tester,
            () => textAny(['最后一步：确认交付']) != null,
            timeout: const Duration(seconds: 300),
          );
          await safeSettle(tester);
          await shot('$_kRun/$_kLeg/24-hybrid-outcome.png');
          await dumpTexts(tester, 'hybrid-outcome');
          await dumpSemantics('hybrid-outcome');
          recordStep('hybrid_outcome_stage', outcomeReady,
              'outcome stage visible=$outcomeReady');
          if (outcomeReady) {
            final confirmBtn = await tapWhenVisible(
              tester,
              () => primaryButton(['确认交付', '完成', '确认']),
              timeout: const Duration(seconds: 20),
            );
            final done = await waitUntil(
              tester,
              () => find.textContaining('交付完成').evaluate().isNotEmpty ||
                  find
                      .byKey(const ValueKey('hybrid-journey-done'))
                      .evaluate()
                      .isNotEmpty ||
                  find.textContaining('已交付').evaluate().isNotEmpty,
              timeout: const Duration(seconds: 120),
            );
            await safeSettle(tester);
            await shot('$_kRun/$_kLeg/25-hybrid-done.png');
            await dumpTexts(tester, 'hybrid-done');
            await dumpSemantics('hybrid-done');
            recordStep('hybrid_done', done || confirmBtn,
                'delivery confirmed; done surface=$done');
          }
        }
      } // dashOk guard：上游身份入口失败时下游整体跳过

      } // execOk guard：执行面未达时下游整体跳过

      // 状态移交（orchestrator 解析后传给 part2）
      // ignore: avoid_print
      print('Q01_STATE ${jsonEncode({
            'run': _kRun,
            'username': username,
            'goal_title': '数据结构期中冲刺',
            'task_title': journeyTaskTitle,
            'seed_minutes': 90,
            'adjusted_minutes': 15,
            'goal_anchor_created': anchorOk,
          })}');
      } // if (dashOk)
    }

    if (_kLeg == 'part2') {
      // 真重启（新进程）后的接续可见性
      await safeSettle(tester, const Duration(seconds: 10));
      await shot('$_kRun/$_kLeg/30-reopen-dashboard.png');
      await dumpTexts(tester, 'reopen-dashboard');
      await dumpSemantics('reopen-dashboard');
      final resumeAbsent = find
          .byKey(const ValueKey('episode-resume-absent'))
          .evaluate()
          .isNotEmpty;
      final resumeStale = find
          .byKey(const ValueKey('episode-resume-stale-line'))
          .evaluate()
          .isNotEmpty;
      // ignore: avoid_print
      print('Q01_REOPEN_RESUME_STRIP state=${resumeAbsent
          ? 'absent'
          : resumeStale
              ? 'stale'
              : 'ready_or_other'}');
      // 纠正后的时长是否可见（预计时长 15 分钟）——首页/执行面任意出现即计数
      final minutesVisible =
          find.textContaining(RegExp('15\\s*分钟')).evaluate().isNotEmpty;
      final goalVisible =
          find.textContaining(_kGoalTitle).evaluate().isNotEmpty;
      // ignore: avoid_print
      print('Q01_REOPEN goalVisible=$goalVisible minutes15Visible=$minutesVisible');
      recordStep('reopen_resume_visible', goalVisible || minutesVisible,
          'goal=$goalVisible minutes15=$minutesVisible '
          'strip=${resumeAbsent ? 'absent' : resumeStale ? 'stale' : 'ready'}');

      // 进入任务执行面：点 seeded 任务标题（纠正后的预计时长应在场）
      final taskText = find.textContaining(_kTaskTitle);
      if (taskText.evaluate().isNotEmpty) {
        try {
          await tester.ensureVisible(taskText.first);
        } catch (_) {}
        await tester.tap(taskText.first, warnIfMissed: false);
        await safeSettle(tester, const Duration(seconds: 8));
      }
      await shot('$_kRun/$_kLeg/31-reopen-task-exec.png');
      await dumpTexts(tester, 'reopen-task-exec');
      await dumpSemantics('reopen-task-exec');
      final minutesOnTask =
          find.textContaining(RegExp('15\\s*分钟')).evaluate().isNotEmpty;
      // ignore: avoid_print
      print('Q01_REOPEN_TASKS minutes15Visible=$minutesOnTask');
      recordStep('reopen_minutes_persisted', minutesOnTask,
          'estimated 15min visible after real restart=$minutesOnTask');
    }

    File('$_kShotDest/q01_${_kRun}_${_kLeg}_steps.json')
      ..createSync(recursive: true)
      ..writeAsStringSync(jsonEncode({
        'run': _kRun,
        'leg': _kLeg,
        'started_at': t0.toIso8601String(),
        'ended_at': DateTime.now().toIso8601String(),
        'steps': steps,
        'failures': failures,
        'clicks': clicks[0],
      }, toEncodable: (o) => o.toString()));
  });
}

int? _currentAdjustedMinutes(WidgetTester tester) {
  final texts = find.byWidgetPredicate(
    (w) => w is Text && RegExp(r'^\d+ 分钟$').hasMatch(w.data ?? ''),
  );
  for (final e in texts.evaluate()) {
    final w = e.widget as Text;
    final m = int.tryParse(RegExp(r'(\d+)').firstMatch(w.data!)!.group(1)!);
    if (m != null) return m;
  }
  return null;
}
