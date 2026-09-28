import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/audio_focus_controller.dart';

/// V4-S02 · 音频焦点状态机（卡验收 2/3 的调用级证据；MOTION_AUDIO_HAPTICS
/// §音频焦点状态逐迁移钉死，每面一正一反）。
///
/// 口径：全部是**调用级**断言（模拟器只认调用与录制证据）；真机扬声器/
/// 真实系统来电/耳机拔出 OS 事件未实测，DEVICE_UNVERIFIED（归 Q06）。
///
/// 覆盖迁移：IDLE→USER_PLAYING→DUCKED_BY_TTS / PAUSED_BY_RECORDING /
/// PAUSED_BY_CALL / STOPPED_BY_USER，以及各抢占结束的恢复语义：
/// - 录音/通话结束 → 按平台惯例恢复到抢占前会话态（瞬时抢占）；
/// - 耳机拔出 → STOPPED_BY_USER，**任何**抢占结束都不自续（不转扬声器
///   大声续播）；
/// - 重开不自续：会话态不持久化，冷启动等价（debugReset）后恒 IDLE。
void main() {
  setUp(AudioFocusController.instance.debugReset);

  tearDown(AudioFocusController.instance.debugReset);

  group('S02 基础会话（IDLE ⇄ USER_PLAYING）', () {
    test('正·冷启动 IDLE，显式点播进入 USER_PLAYING', () {
      expect(AudioFocusController.instance.state, AudioFocusState.idle);

      final started = AudioFocusController.instance.beginUserPlaybackSession();

      expect(started, isTrue);
      expect(AudioFocusController.instance.state, AudioFocusState.userPlaying);
      expect(
        AudioFocusController.instance.ambientFactor,
        1.0,
      );
      expect(
        AudioFocusController.instance.promptsSuppressed,
        isFalse,
      );
    });

    test('反·录音抢占期间点播被拒（录音不回录背景床）', () {
      AudioFocusController.instance.beginRecording();
      expect(
        AudioFocusController.instance.state,
        AudioFocusState.pausedByRecording,
      );

      final started = AudioFocusController.instance.beginUserPlaybackSession();

      expect(started, isFalse);
      expect(
        AudioFocusController.instance.state,
        AudioFocusState.pausedByRecording,
      );
    });

    test('反·通话抢占期间点播被拒', () {
      AudioFocusController.instance.beginCallInterruption();

      final started = AudioFocusController.instance.beginUserPlaybackSession();

      expect(started, isFalse);
      expect(AudioFocusController.instance.state, AudioFocusState.pausedByCall);
    });

    test('会话自然结束（路由离开）回 IDLE；STOPPED_BY_USER 不被自然结束改写', () {
      AudioFocusController.instance.beginUserPlaybackSession();
      AudioFocusController.instance.endUserPlaybackSession();
      expect(AudioFocusController.instance.state, AudioFocusState.idle);

      AudioFocusController.instance.stopByUser();
      AudioFocusController.instance.endUserPlaybackSession();
      expect(
        AudioFocusController.instance.state,
        AudioFocusState.stoppedByUser,
      );
    });
  });

  group('S02 TTS duck（TTS可duck/暂停环境床）', () {
    test('正·播放中 TTS 开始 → DUCKED_BY_TTS，环境系数压低不消除', () {
      AudioFocusController.instance.beginUserPlaybackSession();

      AudioFocusController.instance.beginTts();

      expect(AudioFocusController.instance.state, AudioFocusState.duckedByTts);
      expect(AudioFocusController.instance.ambientFactor, kTtsAmbientDuckFactor);
      // duck 只压低环境床：提示音不被抑制（MOTION 回录约束只落在录音面）。
      expect(AudioFocusController.instance.promptsSuppressed, isFalse);
    });

    test('正·TTS 结束 → 解除压低回 USER_PLAYING，系数复原', () {
      AudioFocusController.instance.beginUserPlaybackSession();
      AudioFocusController.instance.beginTts();

      AudioFocusController.instance.endTts();

      expect(AudioFocusController.instance.state, AudioFocusState.userPlaying);
      expect(AudioFocusController.instance.ambientFactor, 1.0);
    });

    test('反·无播放会话时 TTS 不造会话（保持 IDLE）', () {
      AudioFocusController.instance.beginTts();

      expect(AudioFocusController.instance.state, AudioFocusState.idle);
      expect(AudioFocusController.instance.promptsSuppressed, isFalse);

      AudioFocusController.instance.endTts();
      expect(AudioFocusController.instance.state, AudioFocusState.idle);
    });

    test('恢复目标依赖 duck 而 TTS 先结束：录音结束直接回播放态', () {
      AudioFocusController.instance.beginUserPlaybackSession();
      AudioFocusController.instance.beginTts(); // duck
      AudioFocusController.instance.beginRecording(); // 抢占（记录恢复目标）
      AudioFocusController.instance.endTts(); // TTS 先完成

      AudioFocusController.instance.endRecording();

      expect(AudioFocusController.instance.state, AudioFocusState.userPlaying);
    });
  });

  group('S02 录音抢占（录音不回录提示音）', () {
    test('正·录音开始 → PAUSED_BY_RECORDING：提示音抑制 + 环境床系数 0', () {
      AudioFocusController.instance.beginUserPlaybackSession();

      AudioFocusController.instance.beginRecording();

      expect(
        AudioFocusController.instance.state,
        AudioFocusState.pausedByRecording,
      );
      expect(AudioFocusController.instance.promptsSuppressed, isTrue);
      expect(AudioFocusController.instance.ambientFactor, 0);
      expect(
        AudioFocusController.instance.lastDecision?.ambientPausedTemporarily,
        isTrue,
      );
    });

    test('正·录音结束 → 平台惯例恢复到抢占前会话（USER_PLAYING）', () {
      AudioFocusController.instance.beginUserPlaybackSession();
      AudioFocusController.instance.beginRecording();

      AudioFocusController.instance.endRecording();

      expect(AudioFocusController.instance.state, AudioFocusState.userPlaying);
      expect(AudioFocusController.instance.promptsSuppressed, isFalse);
    });

    test('反·无会话时录音结束回 IDLE（不造播放会话）', () {
      AudioFocusController.instance.beginRecording();
      AudioFocusController.instance.endRecording();

      expect(AudioFocusController.instance.state, AudioFocusState.idle);
    });

    test('反例钉·录音中 emit 面全抑制：endRecording 前抑制位恒真', () {
      AudioFocusController.instance.beginUserPlaybackSession();
      AudioFocusController.instance.beginRecording();

      // 录音进行中的任意时点：抑制位必须为真（服务面据此拦提示音输出，
      // 「录音不回录提示音」的机制锚点）。
      expect(AudioFocusController.instance.promptsSuppressed, isTrue);
      AudioFocusController.instance.beginTts(); // 录音期间 TTS 不解除抑制
      expect(AudioFocusController.instance.promptsSuppressed, isTrue);
    });
  });

  group('S02 来电抢占（PAUSED_BY_CALL）', () {
    test('正·来电 → 暂停；结束 → 按平台惯例恢复播放', () {
      AudioFocusController.instance.beginUserPlaybackSession();

      AudioFocusController.instance.beginCallInterruption();
      expect(AudioFocusController.instance.state, AudioFocusState.pausedByCall);
      expect(AudioFocusController.instance.promptsSuppressed, isTrue);

      AudioFocusController.instance.endCallInterruption();
      expect(AudioFocusController.instance.state, AudioFocusState.userPlaying);
    });

    test('反·多抢占并存：录音+来电，只结束其一时仍暂停', () {
      AudioFocusController.instance.beginUserPlaybackSession();
      AudioFocusController.instance.beginRecording();
      AudioFocusController.instance.beginCallInterruption();

      AudioFocusController.instance.endRecording();
      expect(AudioFocusController.instance.state, AudioFocusState.pausedByCall);
      expect(AudioFocusController.instance.promptsSuppressed, isTrue);

      AudioFocusController.instance.endCallInterruption();
      expect(AudioFocusController.instance.state, AudioFocusState.userPlaying);
    });

    test('反·通话中录音结束的抑制位不解除（另一抢占仍在）', () {
      AudioFocusController.instance.beginCallInterruption();
      AudioFocusController.instance.beginRecording();

      AudioFocusController.instance.endRecording();

      expect(AudioFocusController.instance.promptsSuppressed, isTrue);
    });
  });

  group('S02 耳机拔出（STOPPED_BY_USER，不自续）', () {
    test('正·播放中耳机拔出 → STOPPED_BY_USER，环境系数归零', () {
      AudioFocusController.instance.beginUserPlaybackSession();

      AudioFocusController.instance.handleHeadphoneUnplugged();

      expect(
        AudioFocusController.instance.state,
        AudioFocusState.stoppedByUser,
      );
      expect(AudioFocusController.instance.ambientFactor, 0);
      // 停止 ≠ 暂停：不允许按「瞬时抢占」惯例恢复。
      expect(
        AudioFocusController.instance.lastDecision?.ambientPausedTemporarily,
        isFalse,
      );
    });

    test('反例钉·耳机拔出后任何抢占结束都不自续（不转扬声器大声续播）', () {
      AudioFocusController.instance.beginUserPlaybackSession();
      AudioFocusController.instance.beginTts();
      AudioFocusController.instance.handleHeadphoneUnplugged();

      // 抢占结束回调（TTS 完成/录音清理/通话挂断）逐一到达——状态必须停在
      // STOPPED_BY_USER。
      AudioFocusController.instance.endTts();
      expect(
        AudioFocusController.instance.state,
        AudioFocusState.stoppedByUser,
      );
      AudioFocusController.instance.endCallInterruption();
      expect(
        AudioFocusController.instance.state,
        AudioFocusState.stoppedByUser,
      );

      // 唯一再播路径 = 用户显式点播。
      final started = AudioFocusController.instance.beginUserPlaybackSession();
      expect(started, isTrue);
      expect(AudioFocusController.instance.state, AudioFocusState.userPlaying);
    });
  });

  group('S02 重开不自续（会话态不持久化）', () {
    test('正·播放会话只存在于进程内：重开（冷启动等价复位）后恒 IDLE', () {
      AudioFocusController.instance.beginUserPlaybackSession();
      expect(AudioFocusController.instance.state, AudioFocusState.userPlaying);

      // 「重开 App」= 新进程：控制器新实例从 IDLE 起步（静态 instance 的
      // debugReset 即冷启动等价态；无任何持久化恢复路径）。
      AudioFocusController.instance.debugReset();

      expect(AudioFocusController.instance.state, AudioFocusState.idle);
      expect(AudioFocusController.instance.ambientFactor, 1.0);
    });

    test('反·用户停止后录音/TTS 结束不复活会话', () {
      AudioFocusController.instance.beginUserPlaybackSession();
      AudioFocusController.instance.beginRecording();
      AudioFocusController.instance.stopByUser();

      AudioFocusController.instance.endRecording();

      expect(
        AudioFocusController.instance.state,
        AudioFocusState.stoppedByUser,
      );
    });
  });

  group('S02 监听面（策略权威 → 执行面）', () {
    test('正·监听器收到每次裁决（含迁移前后与原因）', () {
      final decisions = <AudioFocusDecision>[];
      AudioFocusController.instance.addListener(decisions.add);
      AudioFocusController.instance.beginUserPlaybackSession();
      AudioFocusController.instance.beginTts();
      AudioFocusController.instance.endTts();

      expect(decisions, hasLength(3));
      expect(decisions[0].previousState, AudioFocusState.idle);
      expect(decisions[0].state, AudioFocusState.userPlaying);
      expect(decisions[1].state, AudioFocusState.duckedByTts);
      expect(
        decisions[1].interruption,
        AudioFocusInterruption.tts,
      );
      expect(decisions[2].state, AudioFocusState.userPlaying);
    });

    test('反·监听器抛异常不反噬状态机（呈现策略异常不伤任务流）', () {
      AudioFocusController.instance.addListener((_) => throw StateError('x'));
      var healthy = 0;
      AudioFocusController.instance.addListener((_) => healthy++);

      AudioFocusController.instance.beginUserPlaybackSession();

      expect(healthy, 1);
      expect(AudioFocusController.instance.state, AudioFocusState.userPlaying);
    });

    test('解绑函数生效：解绑后不再收到裁决', () {
      final decisions = <AudioFocusDecision>[];
      final unbind = AudioFocusController.instance.addListener(decisions.add);
      unbind();

      AudioFocusController.instance.beginUserPlaybackSession();

      expect(decisions, isEmpty);
    });
  });
}
