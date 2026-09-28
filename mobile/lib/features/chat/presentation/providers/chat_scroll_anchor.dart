import 'package:flutter/widgets.dart';

/// V4-U07「上滑后不自动拉回」：聊天列表滚动主权锚。
///
/// 适配 chat_screen 的 reversed 消息列表（`ListView.custom(reverse: true)`，
/// offset 0 = 最新一端）。语义（SCREEN_FAMILIES §对话：增量不抢滚动）：
/// - 视口停在最新端附近（pixels ≤ [followThreshold]）→ 跟随态，到达性
///   滚动（新消息/新组件/流式增量）继续跟随最新内容；
/// - 视口离开最新端（用户上滑阅读历史）→ 跟随态解除，此后一切到达性
///   滚动**不再**把视口拉回最新端（保留用户阅读位置与未读内容）；
/// - 仅显式用户动作（发送消息/跳最新）经 [forceFollow] 恢复跟随。
///
/// 纯阈值判定：手势、惯性、程序化滚动只有「最终停在哪里」一个事实，
/// 离开最新端即视为进入阅读态，不区分驱动来源（存在第二套方向状态机
/// 反而制造「滚动中态」歧义）。
class ChatScrollAnchor {
  ChatScrollAnchor({this.followThreshold = kChatFollowLatestThreshold});

  /// 距最新端 ≤ 240 逻辑像素视为贴底（与 `_handleScroll` 的历史预载
  /// 阈值同档，单一位移语义：这个窗口内用户仍在"看最新"）。
  static const double kChatFollowLatestThreshold = 240;

  final double followThreshold;

  bool _following = true;

  /// 当前是否允许到达性自动滚动。
  bool get shouldFollow => _following;

  /// 每帧滚动通知更新跟随态。reversed 列表：pixels 小 = 靠近最新端。
  void updateFromPosition(ScrollPosition position) {
    _following = position.pixels <= followThreshold;
  }

  /// 显式用户动作（发送/跳最新）强制恢复跟随。
  void forceFollow() {
    _following = true;
  }

  /// 测试与重置辅助：回到初始贴底跟随态。
  void reset() {
    _following = true;
  }
}
