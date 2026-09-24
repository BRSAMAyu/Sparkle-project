import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// J-02（A-SPEC8B §5 改造 #2 / N48 具象令）· 首启两级副标题必须含北极星
/// 可感场景词（期末/备考/提分类），禁纯抽象口号。
///
/// 背景（A-SPEC8B G3）：旧版 login「点燃你的学习潜能」/ splash「从第一秒
/// 开始，进入更聪明也更有温度的学习旅程」均无场景词——首屏（全漏斗最便宜的
/// 一段）没回答「进来能得到什么」。本测试钉住：两语言 × 两键都必须携带
/// 期末备考提分语义，且不得回退为旧抽象口号。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('first-run value subtitle concretization (J-02 / N48)', () {
    test('zh login welcomeSubtitle carries exam-sprint scenario words',
        () async {
      final zh = await AppLocalizations.delegate.load(const Locale('zh'));

      expect(zh.welcomeSubtitle, isNot('点燃你的学习潜能'));
      expect(zh.welcomeSubtitle, contains('期末'));
      expect(zh.welcomeSubtitle, contains('备考'));
      expect(
        zh.welcomeSubtitle.contains('提分') ||
            zh.welcomeSubtitle.contains('拿回'),
        isTrue,
        reason: 'welcomeSubtitle 应含可感的「提分/拿回」类价值词',
      );
    });

    test('zh splash splashSubtitle carries exam-sprint scenario words',
        () async {
      final zh = await AppLocalizations.delegate.load(const Locale('zh'));

      expect(zh.splashSubtitle, isNot('从第一秒开始，进入更聪明也更有温度的学习旅程。'));
      expect(zh.splashSubtitle, contains('期末'));
      expect(
        zh.splashSubtitle.contains('备考') || zh.splashSubtitle.contains('提分'),
        isTrue,
        reason: 'splashSubtitle 应含备考/提分类场景词',
      );
    });

    test('en subtitles carry the same concrete scenario (bilingual sync)',
        () async {
      final en = await AppLocalizations.delegate.load(const Locale('en'));
      final welcome = en.welcomeSubtitle.toLowerCase();
      final splash = en.splashSubtitle.toLowerCase();

      expect(welcome, contains('final'));
      expect(
        welcome.contains('grade') ||
            welcome.contains('point') ||
            welcome.contains('prep'),
        isTrue,
        reason: 'en welcomeSubtitle 应含提分/备考类价值词',
      );
      expect(splash, contains('final'));
      expect(
        splash.contains('point') || splash.contains('grade'),
        isTrue,
        reason: 'en splashSubtitle 应含可感的分数价值词',
      );
    });
  });
}
