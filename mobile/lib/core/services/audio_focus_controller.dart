/// V4-S02 · 音频焦点状态机（唯一策略权威，无第二播放路径）。
///
/// 合同（`v4/02_design/MOTION_AUDIO_HAPTICS.md` §音频焦点状态）：
/// 「音频焦点状态：IDLE→USER_PLAYING→DUCKED_BY_TTS / PAUSED_BY_RECORDING /
/// PAUSED_BY_CALL / STOPPED_BY_USER。耳机拔出不转扬声器大声续播；录音、TTS
/// 和背景床不得彼此回录；系统拒绝播放时降级静音并保持任务正常。」
///
/// 设计边界（卡验收 + 不造第二权威）：
/// - 本控制器只做**策略裁决**，不持有任何 AudioPlayer：播放仍由既有
///   SensoryFeedbackService（提示音池/环境床）与 TtsService（TTS）执行，
///   它们消费本控制器的裁决（抑制位/压低系数/可恢复位）。
/// - 两独立音量（环境/提示音）的持久化仍归 SensoryFeedbackService 的
///   SharedPreferences 键（U14 同源，键不重复）。
/// - 播放会话是**进程内的**：不持久化「正在播放」态——App 重开后状态回到
///   IDLE，环境床不自续（「重开App不自行续播」，与 U14「开启开关不自动
///   续播」语义对齐）；只有用户显式点播（选场景/开始专注）才进入
///   USER_PLAYING。
///
/// 模拟器证据口径（卡验收 3）：状态迁移全部是可失败的单测调用级证据；真
/// 扬声器/真中断（系统来电、耳机拔出的 OS 事件）未实测，标
/// DEVICE_UNVERIFIED（归 Q06 真机面），不冒充已验证。
library;

import 'package:flutter/foundation.dart';

/// 音频焦点状态（与 MOTION 状态机逐一对应）。
enum AudioFocusState {
  /// IDLE：无任何播放会话（App 冷启动即此态）。
  idle,

  /// USER_PLAYING：用户显式点播（环境床）进行中。
  userPlaying,

  /// DUCKED_BY_TTS：TTS 抢占——环境床压低（duck），提示音照常。
  duckedByTts,

  /// PAUSED_BY_RECORDING：录音抢占——**全部**输出抑制（录音不回录提示音
  /// 与环境床）。
  pausedByRecording,

  /// PAUSED_BY_CALL：系统通话/音频中断——全部输出暂停。
  pausedByCall,

  /// STOPPED_BY_USER：用户/系统停止（含耳机拔出）——**不自续**，须用户
  /// 显式再点播。
  stoppedByUser,
}

/// 焦点被抢占的原因（结束抢占时决定恢复语义）。
enum AudioFocusInterruption {
  /// TTS 播放中（结束：解除压低）。
  tts,

  /// 录音进行中（结束：瞬时抢占，平台惯例恢复到抢占前会话态）。
  recording,

  /// 系统来电/音频中断（结束：Android 瞬时焦点失而复得 → 恢复；iOS
  /// AVAudioSession interruption option 配 shouldResume。调用级证据，
  /// 真机未验证——DEVICE_UNVERIFIED）。
  call,

  /// 耳机拔出（**不恢复**：不转扬声器大声续播，须用户显式再点播）。
  headphoneUnplug,
}

/// TTS 抢占期间环境床的目标压低系数（duck 语义：压低不消除，TTS 结束回 1.0）。
const double kTtsAmbientDuckFactor = 0.25;

/// 焦点状态变化的裁决快照（播放面据此调整输出；本控制器不发命令）。
@immutable
class AudioFocusDecision {
  const AudioFocusDecision({
    required this.state,
    required this.previousState,
    required this.interruption,
  });

  /// 迁移后的状态。
  final AudioFocusState state;

  /// 迁移前的状态（恢复语义的还原点）。
  final AudioFocusState previousState;

  /// 造成本次迁移的抢占类型（进入/结束抢占时非空）。
  final AudioFocusInterruption? interruption;

  /// 提示音是否被抑制（录音/通话中全输出静默——「录音不回录提示音」；
  /// 成功回执、任务流不受影响）。
  bool get promptsSuppressed =>
      state == AudioFocusState.pausedByRecording ||
      state == AudioFocusState.pausedByCall;

  /// 环境床输出系数（乘在用户环境音量上）：TTS duck 压低；录音/通话/停止
  /// 为 0。
  double get ambientFactor => switch (state) {
        AudioFocusState.duckedByTts => kTtsAmbientDuckFactor,
        AudioFocusState.pausedByRecording ||
        AudioFocusState.pausedByCall ||
        AudioFocusState.stoppedByUser =>
          0,
        _ => 1,
      };

  /// 环境床是否处于暂停（非停止）语义：录音/通话是瞬时抢占，结束后按平台
  /// 惯例可恢复。
  bool get ambientPausedTemporarily =>
      state == AudioFocusState.pausedByRecording ||
      state == AudioFocusState.pausedByCall;
}

/// 音频焦点控制器（静态门面，状态在实例内，便于测试隔离与 dispose 复位）。
class AudioFocusController {
  AudioFocusController._();
  static final AudioFocusController instance = AudioFocusController._();

  AudioFocusState _state = AudioFocusState.idle;

  /// 当前在场的抢占登记（多抢占并存时，最后一个结束才裁决恢复）。
  final Set<AudioFocusInterruption> _activeInterruptions = {};

  /// 进入「暂停」态之前的会话态（userPlaying / duckedByTts / idle）——
  /// 抢占全部结束时的恢复目标。
  AudioFocusState _resumeTarget = AudioFocusState.idle;

  final List<void Function(AudioFocusDecision)> _listeners = [];

  /// 当前状态（只读观测面）。
  AudioFocusState get state => _state;

  /// 最近一次裁决（含迁移前后状态与原因；测试/呈现用）。
  AudioFocusDecision? get lastDecision => _lastDecision;
  AudioFocusDecision? _lastDecision;

  /// 提示音是否被抑制（SensoryFeedbackService.emit 消费）。
  bool get promptsSuppressed => _decisionFor(_state).promptsSuppressed;

  /// 环境床输出系数（SensoryFeedbackService 消费）。
  double get ambientFactor => _decisionFor(_state).ambientFactor;

  /// 注册输出面监听（SensoryFeedbackService init 时注册；返回解绑函数）。
  VoidCallback addListener(void Function(AudioFocusDecision) listener) {
    _listeners.add(listener);
    return () => _listeners.remove(listener);
  }

  // ---------------------------------------------------------------------------
  // 用户显式点播会话
  // ---------------------------------------------------------------------------

  /// 用户显式开始播放（选环境场景/开始专注）。录音/通话抢占期间的点播请求
  /// 被拒（返回 false）——录音不回录，通话中不抢焦点。
  bool beginUserPlaybackSession() {
    if (_state == AudioFocusState.pausedByRecording ||
        _state == AudioFocusState.pausedByCall) {
      _emit(_state);
      return false;
    }
    _activeInterruptions.remove(AudioFocusInterruption.headphoneUnplug);
    _resumeTarget = AudioFocusState.userPlaying;
    _transition(AudioFocusState.userPlaying);
    return true;
  }

  /// 用户显式停止播放 → STOPPED_BY_USER（重开不自续的锚点：任何自动恢复
  /// 路径在 STOPPED_BY_USER 前必须止步）。
  void stopByUser() {
    _activeInterruptions.clear();
    _resumeTarget = AudioFocusState.idle;
    _transition(AudioFocusState.stoppedByUser);
  }

  /// 用户会话自然结束（路由离开/专注完成等，非「停止」意愿）→ 回 IDLE。
  void endUserPlaybackSession() {
    if (_state == AudioFocusState.stoppedByUser) return;
    _activeInterruptions.clear();
    _resumeTarget = AudioFocusState.idle;
    _transition(AudioFocusState.idle);
  }

  // ---------------------------------------------------------------------------
  // 抢占（TTS / 录音 / 来电 / 耳机拔出）
  // ---------------------------------------------------------------------------

  /// TTS 开始说话：USER_PLAYING → DUCKED_BY_TTS（环境床压低不消除；提示音
  /// 不抑制——MOTION 的回录约束只落在录音面，TTS 与短提示音无回录关系）。
  void beginTts() {
    _activeInterruptions.add(AudioFocusInterruption.tts);
    if (_state == AudioFocusState.userPlaying) {
      _resumeTarget = AudioFocusState.userPlaying;
      _transition(
        AudioFocusState.duckedByTts,
        interruption: AudioFocusInterruption.tts,
      );
    } else {
      // 无播放会话时 duck 无对象：保持现态，只登记 TTS 活动。
      _emit(_state, interruption: AudioFocusInterruption.tts);
    }
  }

  /// TTS 结束：解除压低，回到 USER_PLAYING（若曾处于播放会话）。
  void endTts() {
    final hadTts = _activeInterruptions.remove(AudioFocusInterruption.tts);
    if (!hadTts) return;
    if (_state == AudioFocusState.duckedByTts) {
      _transition(
        AudioFocusState.userPlaying,
        interruption: AudioFocusInterruption.tts,
      );
    } else {
      _emit(_state, interruption: AudioFocusInterruption.tts);
    }
  }

  /// 录音开始：任何态 → PAUSED_BY_RECORDING（全输出抑制，录音不回录）。
  void beginRecording() {
    _activeInterruptions.add(AudioFocusInterruption.recording);
    if (_state != AudioFocusState.pausedByRecording) {
      _captureResumeTarget();
      _transition(
        AudioFocusState.pausedByRecording,
        interruption: AudioFocusInterruption.recording,
      );
    }
  }

  /// 录音结束：瞬时抢占按平台惯例恢复到抢占前会话态（无会话回 IDLE；
  /// STOPPED_BY_USER 不经过本路径——用户停止已清登记并改写目标）。
  void endRecording() {
    _settleAfterInterruption(AudioFocusInterruption.recording);
  }

  /// 系统来电/音频中断开始：任何态 → PAUSED_BY_CALL。
  void beginCallInterruption() {
    _activeInterruptions.add(AudioFocusInterruption.call);
    if (_state != AudioFocusState.pausedByCall) {
      _captureResumeTarget();
      _transition(
        AudioFocusState.pausedByCall,
        interruption: AudioFocusInterruption.call,
      );
    }
  }

  /// 来电结束：Android 瞬时焦点失而复得 → 恢复播放（平台惯例；调用级证据，
  /// 真机未验证——DEVICE_UNVERIFIED，见 limitations）。
  void endCallInterruption() {
    _settleAfterInterruption(AudioFocusInterruption.call);
  }

  /// 耳机拔出：→ STOPPED_BY_USER（**不转扬声器大声续播**；唯一再播路径是
  /// 用户显式 [beginUserPlaybackSession]）。其他抢占登记保留，其结束回调
  /// 不得越过 STOPPED_BY_USER 自续。
  void handleHeadphoneUnplugged() {
    _activeInterruptions.remove(AudioFocusInterruption.headphoneUnplug);
    _resumeTarget = AudioFocusState.idle;
    _transition(
      AudioFocusState.stoppedByUser,
      interruption: AudioFocusInterruption.headphoneUnplug,
    );
  }

  // ---------------------------------------------------------------------------
  // 内部
  // ---------------------------------------------------------------------------

  void _captureResumeTarget() {
    if (_state == AudioFocusState.pausedByRecording ||
        _state == AudioFocusState.pausedByCall) {
      return; // 已在暂停态：保留最早的恢复目标。
    }
    _resumeTarget = _state;
  }

  void _settleAfterInterruption(AudioFocusInterruption kind) {
    final had = _activeInterruptions.remove(kind);
    if (!had) return;
    // 其余抢占仍在（如录音+通话并存）→ 不得恢复。
    if (_activeInterruptions.isNotEmpty) {
      _emit(_state, interruption: kind);
      return;
    }
    if (_state == AudioFocusState.stoppedByUser) {
      // 耳机拔出/用户停止后，抢占结束**不自续**（MOTION：耳机拔出不转
      // 扬声器大声续播）。保持 STOPPED_BY_USER。
      _emit(_state, interruption: kind);
      return;
    }
    // 恢复语义按平台惯例：回到抢占前会话态（userPlaying / duckedByTts /
    // idle）。恢复目标若依赖 TTS duck，而 TTS 已先结束 → 直接回播放态。
    var target = _resumeTarget;
    if (target == AudioFocusState.duckedByTts &&
        !_activeInterruptions.contains(AudioFocusInterruption.tts)) {
      target = AudioFocusState.userPlaying;
    }
    _transition(target, interruption: kind);
  }

  void _transition(
    AudioFocusState next, {
    AudioFocusInterruption? interruption,
  }) {
    if (_state == next && interruption == null) {
      return;
    }
    _emit(next, interruption: interruption);
  }

  void _emit(AudioFocusState next, {AudioFocusInterruption? interruption}) {
    final decision = AudioFocusDecision(
      state: next,
      previousState: _state,
      interruption: interruption,
    );
    _state = next;
    _lastDecision = decision;
    for (final listener in List.of(_listeners)) {
      try {
        listener(decision);
      } catch (_) {
        // 焦点裁决是呈现策略：监听面异常绝不反噬任务流。
      }
    }
  }

  AudioFocusDecision _decisionFor(AudioFocusState state) => AudioFocusDecision(
        state: state,
        previousState: state,
        interruption: null,
      );

  /// 测试专用：回到冷启动等价态（App「重开」语义——会话态不持久化）。
  @visibleForTesting
  void debugReset() {
    _activeInterruptions.clear();
    _state = AudioFocusState.idle;
    _resumeTarget = AudioFocusState.idle;
    _lastDecision = null;
    _listeners.clear();
  }
}
