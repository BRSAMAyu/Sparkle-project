import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';

/// V4-U07 快慢反馈：I09 快慢分层移动端消费词表与呈现门的可失败钉。
///
/// 每面一正一反：
/// - lane 解析：快路标记（正）/ 集合外值与缺键（反）；
/// - 阶段胶囊门：慢路等待进三段胶囊（正，S18 既有语义保持）/
///   快路轮不进胶囊（反，不展示假检索/思考）；
/// - 消息模型 lane 判据：deterministic 消息标记（正）/ model 与
///   无键消息不标记（反）。
void main() {
  group('ChatLaneValues.parseFromMetadata（I09 帧 metadata 消费门）', () {
    test('正：快路状态帧 metadata → deterministic + 形态词', () {
      final (lane, kind) = ChatLaneValues.parseFromMetadata(const {
        'chat_lane': 'deterministic',
        'deterministic_lane_kind': 'greeting',
      });
      expect(lane, 'deterministic');
      expect(kind, 'greeting');
    });

    test('正：大小写与空白归一（网络帧冗余形态）', () {
      final (lane, kind) = ChatLaneValues.parseFromMetadata(const {
        'chat_lane': ' Deterministic ',
        'deterministic_lane_kind': '  acknowledgment  ',
      });
      expect(lane, 'deterministic');
      expect(kind, 'acknowledgment');
    });

    test('正：慢路终帧 chat_lane=model', () {
      final (lane, kind) = ChatLaneValues.parseFromMetadata(
        const {'chat_lane': 'model'},
      );
      expect(lane, 'model');
      expect(kind, isNull);
    });

    test('反：集合外 lane 值整体拒识（不猜不降级）', () {
      final (lane, kind) = ChatLaneValues.parseFromMetadata(const {
        'chat_lane': 'fast_lane',
        'deterministic_lane_kind': 'greeting',
      });
      expect(lane, isNull);
      expect(kind, isNull);
    });

    test('反：缺键 metadata（旧后端/开关关闭）→ 全 null', () {
      final (nullLane, nullKind) = ChatLaneValues.parseFromMetadata(null);
      expect(nullLane, isNull);
      expect(nullKind, isNull);
      final (lane, kind) = ChatLaneValues.parseFromMetadata(const {
        'ux_progress': <String, dynamic>{},
      });
      expect(lane, isNull);
      expect(kind, isNull);
    });

    test('反：快路无形态词 → kind 为 null（呈现层不臆造标签）', () {
      final (lane, kind) = ChatLaneValues.parseFromMetadata(
        const {'chat_lane': 'deterministic'},
      );
      expect(lane, 'deterministic');
      expect(kind, isNull);
    });
  });

  group('ChatState.shouldShowPhaseCapsule（S18 胶囊 × V4-U07 快路门）', () {
    ChatState activeRun({String? chatLane}) => ChatState(
          activeRunId: 'run-1',
          runPhase: ChatRunPhase.sending,
          isSending: true,
          chatLane: chatLane,
        );

    test('正：慢路/未携带 lane 的等待期照旧进三段胶囊（既有语义零变化）', () {
      expect(activeRun().shouldShowPhaseCapsule, isTrue);
      expect(
        activeRun(chatLane: ChatLaneValues.model).shouldShowPhaseCapsule,
        isTrue,
      );
    });

    test('反：零模型快路轮不进三段胶囊（检索/思考阶段不存在，不展示假进度）', () {
      expect(
        activeRun(chatLane: ChatLaneValues.deterministic)
            .shouldShowPhaseCapsule,
        isFalse,
      );
    });

    test('反门仍受既有条件约束：无活跃 run / 内容已到 → 不进胶囊', () {
      expect(
        ChatState(chatLane: ChatLaneValues.deterministic)
            .shouldShowPhaseCapsule,
        isFalse,
        reason: '无活跃 run 本就不进胶囊',
      );
      expect(
        ChatState(
          activeRunId: 'run-1',
          runPhase: ChatRunPhase.streaming,
          isSending: true,
          streamingContent: '首个有用内容已到达',
          chatLane: ChatLaneValues.model,
        ).shouldShowPhaseCapsule,
        isFalse,
        reason: '内容已到，胶囊让位流式正文',
      );
    });

    test('copyWith：clearChatLane 清 lane 与形态词；否则保留', () {
      final fast = activeRun(chatLane: ChatLaneValues.deterministic)
          .copyWith(deterministicLaneKind: 'farewell');
      expect(fast.chatLane, 'deterministic');
      expect(fast.deterministicLaneKind, 'farewell');

      final cleared = fast.copyWith(clearChatLane: true);
      expect(cleared.chatLane, isNull);
      expect(cleared.deterministicLaneKind, isNull);

      expect(
        fast.copyWith(isSending: false).deterministicLaneKind,
        'farewell',
        reason: '无关字段更新不丢失 lane 标记',
      );
    });
  });

  group('ChatMessageModel lane 判据（「即时回复」诚实标记的判据面）', () {
    ChatMessageModel messageWith(Map<String, dynamic>? rawMetadata) =>
        ChatMessageModel(
          conversationId: 'c-1',
          role: MessageRole.assistant,
          content: '你好！我是 Sparkle。',
          rawMetadata: rawMetadata,
        );

    test('正：快路模板消息判定为即时回复并携带形态词', () {
      final message = messageWith(const {
        'chat_lane': 'deterministic',
        'deterministic_lane_kind': 'greeting',
      });
      expect(message.isDeterministicLaneReply, isTrue);
      expect(message.chatLane, 'deterministic');
      expect(message.deterministicLaneKind, 'greeting');
    });

    test('反：真模型消息与无键消息不判定为即时回复', () {
      expect(
        messageWith(const {'chat_lane': 'model'}).isDeterministicLaneReply,
        isFalse,
      );
      expect(messageWith(null).isDeterministicLaneReply, isFalse);
      expect(messageWith(null).deterministicLaneKind, isNull);
    });

    test('反：集合外 lane 值不判定为即时回复（不把未知当快路）', () {
      expect(
        messageWith(const {
          'chat_lane': 'turbo',
          'deterministic_lane_kind': 'greeting',
        }).isDeterministicLaneReply,
        isFalse,
      );
    });

    test('正：用户消息带快路键也不参与判定语义混淆（判据只读 metadata）', () {
      final userMessage = ChatMessageModel(
        conversationId: 'c-1',
        role: MessageRole.user,
        content: '你好',
        rawMetadata: const {'chat_lane': 'deterministic'},
      );
      // 判据本身只反映 metadata 事实；呈现层只在助手气泡挂标记。
      expect(userMessage.isDeterministicLaneReply, isTrue);
      expect(userMessage.chatLane, 'deterministic');
    });
  });
}
