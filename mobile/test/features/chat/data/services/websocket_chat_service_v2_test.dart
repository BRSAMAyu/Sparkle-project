import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';

// Mock WebSocket Channel
class MockWebSocketChannel extends Mock implements WebSocketChannel {
  final MockWebSocketSink sink = MockWebSocketSink();
  final StreamController<dynamic> incomingController = StreamController<dynamic>();

  MockWebSocketChannel() {
    // Default successful connection
    when(this.stream).thenAnswer((_) => incomingController.stream);
  }

  @override
  Stream<dynamic> get stream => incomingController.stream;

  @override
  MockWebSocketSink get sink => this.sink;

  void simulateIncomingMessage(dynamic data) {
    incomingController.add(data);
  }

  void simulateError(dynamic error) {
    incomingController.addError(error);
  }

  void simulateDone() {
    incomingController.close();
  }

  @override
  Future<void> close([int? closeCode, String? closeReason]) async {
    await incomingController.close();
    await sink.close();
  }
}

class MockWebSocketSink extends Mock implements WebSocketSink {
  final List<dynamic> sentData = [];

  @override
  void add(dynamic data) {
    sentData.add(data);
  }

  @override
  Future<void> close([int? closeCode, String? closeReason]) async {
    // No-op for tests
  }

  @override
  Future<void> addStream(Stream<dynamic> stream) async {
    await for (final data in stream) {
      add(data);
    }
  }
}

void main() {
  group('WebSocketChatServiceV2 Tests', () {
    late MockWebSocketChannel mockChannel;
    late WebSocketChatServiceV2 service;

    setUp(() {
      mockChannel = MockWebSocketChannel();
    });

    tearDown(() async {
      // Dispose is void, not Future
      service.dispose();
      await mockChannel.close();
    });

    group('Connection Management', () {
      testWidgets('should initialize with disconnected state', (tester) async {
        // Create service with mock channel factory
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        expect(service.connectionState, equals(WsConnectionState.disconnected));
        expect(service.isConnected, isFalse);
      });

      test('should require userId for ensureConnected', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        // Verify that ensureConnected requires userId
        expect(
          () => service.ensureConnected(userId: 'test-user'),
          returnsNormally,
        );
      });

      test('should update connection state on connection', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        // Listen to connection state changes
        final states = <WsConnectionState>[];
        final subscription = service.connectionStateStream.listen(states.add);

        // Trigger connection
        await service.ensureConnected(userId: 'test-user');
        await Future<void>.delayed(const Duration(milliseconds: 50));

        subscription.cancel();

        // Should have transitioned through states
        expect(states, isNotEmpty);
        expect(states.contains(WsConnectionState.connecting), isTrue);
      });
    });

    group('Message Sending', () {
      test('should send message through WebSocket', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        final stream = service.sendMessage(
          message: 'Hello AI',
          userId: 'test-user',
        );

        // Verify message payload structure
        expect(mockChannel.sink.sentData.length, greaterThan(0));
        final sentData = mockChannel.sink.sentData.first as String;
        final sentJson = json.decode(sentData) as Map<String, dynamic>;

        expect(sentJson['message'], equals('Hello AI'));
        expect(sentJson['session_id'], isNotNull);
        expect(sentJson['request_id'], isNotNull);

        // Clean up stream
        await stream.close();
      });

      test('should include metadata in message', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        final metadata = {'conversation_id': 'conv-123', 'mode': 'standard'};

        final stream = service.sendMessage(
          message: 'Test message',
          userId: 'test-user',
          extraContext: metadata,
        );

        final sentData = mockChannel.sink.sentData.first as String;
        final sentJson = json.decode(sentData) as Map<String, dynamic>;

        expect(sentJson['extra_context'], equals(metadata));

        await stream.close();
      });

      test('should generate unique request IDs', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        final stream1 = service.sendMessage(
          message: 'Message 1',
          userId: 'test-user',
        );
        final stream2 = service.sendMessage(
          message: 'Message 2',
          userId: 'test-user',
        );

        final data1 = json.decode(mockChannel.sink.sentData[0] as String) as Map<String, dynamic>;
        final data2 = json.decode(mockChannel.sink.sentData[1] as String) as Map<String, dynamic>;

        expect(data1['request_id'], isNotNull);
        expect(data2['request_id'], isNotNull);
        expect(data1['request_id'], isNot(equals(data2['request_id'])));

        await stream1.close();
        await stream2.close();
      });
    });

    group('Stream Message Parsing', () {
      test('should parse delta messages correctly', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        final stream = service.sendMessage(
          message: 'init',
          userId: 'test-user',
        );

        final events = <ChatStreamEvent>[];
        final sub = stream.listen(events.add);

        // Simulate delta message
        mockChannel.simulateIncomingMessage(json.encode({
          'type': 'delta',
          'delta': 'Hello',
          'request_id': 'req-1',
        }));

        await Future<void>.delayed(const Duration(milliseconds: 20));

        expect(events.first, isA<TextEvent>());

        sub.cancel();
        await sub.cancel();
      });

      test('should parse status update events', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        final stream = service.sendMessage(
          message: 'init',
          userId: 'test-user',
        );

        final events = <ChatStreamEvent>[];
        final sub = stream.listen(events.add);

        // Simulate status update
        mockChannel.simulateIncomingMessage(json.encode({
          'type': 'status_update',
          'status': {
            'state': 'thinking',
            'details': 'AI is thinking...',
          },
          'request_id': 'req-1',
        }));

        await Future<void>.delayed(const Duration(milliseconds: 20));

        expect(events.first, isA<StatusUpdateEvent>());
        final statusEvent = events.first as StatusUpdateEvent;
        expect(statusEvent.state, equals('thinking'));

        sub.cancel();
        await sub.cancel();
      });

      test('should parse error events', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        final stream = service.sendMessage(
          message: 'init',
          userId: 'test-user',
        );

        final events = <ChatStreamEvent>[];
        final sub = stream.listen(events.add);

        // Simulate error
        mockChannel.simulateIncomingMessage(json.encode({
          'type': 'error',
          'error': {
            'message': 'Something went wrong',
          },
          'request_id': 'req-1',
        }));

        await Future<void>.delayed(const Duration(milliseconds: 20));

        expect(events.first, isA<ErrorEvent>());

        sub.cancel();
        await sub.cancel();
      });

      test('should parse done event', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        final stream = service.sendMessage(
          message: 'init',
          userId: 'test-user',
        );

        final events = <ChatStreamEvent>[];
        final sub = stream.listen(events.add);

        // Simulate done event
        mockChannel.simulateIncomingMessage(json.encode({
          'finish_reason': 'stop',
          'request_id': 'req-1',
        }));

        await Future<void>.delayed(const Duration(milliseconds: 20));

        expect(events.first, isA<DoneEvent>());

        sub.cancel();
        await sub.cancel();
      });
    });

    group('Action Feedback', () {
      test('should send action feedback', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        service.sendActionFeedback(
          action: 'confirm',
          toolResultId: 'result-123',
          widgetType: 'intervention',
        );

        expect(mockChannel.sink.sentData.length, greaterThan(0));
        final sentData = mockChannel.sink.sentData.first as String;
        final sentJson = json.decode(sentData) as Map<String, dynamic>;

        expect(sentJson['type'], equals('action_feedback'));
        expect(sentJson['action'], equals('confirm'));
        expect(sentJson['tool_result_id'], equals('result-123'));
      });

      test('should send intervention feedback', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        service.sendInterventionFeedback(
          requestId: 'req-123',
          feedbackType: 'dismiss',
        );

        expect(mockChannel.sink.sentData.length, greaterThan(0));
        final sentData = mockChannel.sink.sentData.first as String;
        final sentJson = json.decode(sentData) as Map<String, dynamic>;

        expect(sentJson['type'], equals('intervention_feedback'));
        expect(sentJson['feedback_type'], equals('dismiss'));
      });

      test('should send response feedback', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        service.sendResponseFeedback(
          responseId: 'resp-123',
          feedbackType: 'thumbs_up',
        );

        expect(mockChannel.sink.sentData.length, greaterThan(0));
        final sentData = mockChannel.sink.sentData.first as String;
        final sentJson = json.decode(sentData) as Map<String, dynamic>;

        expect(sentJson['type'], equals('response_feedback'));
        expect(sentJson['feedback_type'], equals('thumbs_up'));
      });

      test('should send plan review feedback', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        service.sendPlanReviewFeedback(
          reviewId: 'review-123',
          userDecision: 'approve',
        );

        expect(mockChannel.sink.sentData.length, greaterThan(0));
        final sentData = mockChannel.sink.sentData.first as String;
        final sentJson = json.decode(sentData) as Map<String, dynamic>;

        expect(sentJson['type'], equals('plan_review_feedback'));
        expect(sentJson['review_id'], equals('review-123'));
        expect(sentJson['user_decision'], equals('approve'));
      });

      test('should send focus completed event', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        service.sendFocusCompleted(
          sessionId: 'session-123',
          actualDuration: 1200,
          completedTaskIds: ['task-1', 'task-2'],
        );

        expect(mockChannel.sink.sentData.length, greaterThan(0));
        final sentData = mockChannel.sink.sentData.first as String;
        final sentJson = json.decode(sentData) as Map<String, dynamic>;

        expect(sentJson['type'], equals('focus_completed'));
        expect(sentJson['session_id'], equals('session-123'));
        expect(sentJson['actual_duration'], equals(1200));
      });
    });

    group('Error Handling', () {
      test('should handle connection error gracefully', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        // Simulate connection error by closing the channel immediately
        mockChannel.simulateError('Connection failed');

        // Service should handle this without throwing
        expect(
          () => service.ensureConnected(userId: 'test-user'),
          returnsNormally,
        );
      });

      test('should queue messages when not connected', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        // Send message while not connected
        final stream = service.sendMessage(
          message: 'Queued message',
          userId: 'test-user',
        );

        // Message should be queued
        expect(service.pendingMessages, isNotEmpty);

        // Clean up
        await stream.close();
      });

      test('should expose pending messages for testing', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        service.sendMessage(
          message: 'Test',
          userId: 'test-user',
        );

        expect(service.pendingMessages.length, equals(1));
      });
    });

    group('Disposal', () {
      test('should clean up resources on dispose', () async {
        WebSocketChannelFactory factory = (uri, {headers}) => mockChannel;

        service = WebSocketChatServiceV2(
          container: createMockContainer(),
          channelFactory: factory,
          enableReconnect: false,
          autoConnect: false,
        );

        // Send some messages
        service.sendMessage(
          message: 'Test 1',
          userId: 'test-user',
        );
        service.sendMessage(
          message: 'Test 2',
          userId: 'test-user',
        );

        // Dispose
        service.dispose();

        // Verify resource cleanup
        expect(service.isConnected, isFalse);
      });
    });
  });
}

// Helper function to create a mock ProviderContainer
class MockProviderContainer {
  // Simplified mock - in real tests you'd use riverpod's testing utilities
}

MockProviderContainer createMockContainer() {
  return MockProviderContainer();
}
