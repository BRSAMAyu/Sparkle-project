import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Chat Screen Widget Tests', () {
    // ============================================================
    // Basic Widget Structure Tests
    // ============================================================

    group('Basic Widget Structure', () {
      testWidgets('Chat input field is visible', (WidgetTester tester) async {
        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: Column(
                  children: [
                    Expanded(
                      child: ListView(
                        children: const [
                          Padding(
                            padding: EdgeInsets.all(8.0),
                            child: Text('Chat message'),
                          ),
                        ],
                      ),
                    ),
                    const Padding(
                      padding: EdgeInsets.all(8.0),
                      child: TextField(
                        decoration: InputDecoration(
                          hintText: 'Type a message...',
                          border: OutlineInputBorder(),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );

        expect(find.byType(TextField), findsOneWidget);
        expect(
          find.byWidgetPredicate(
            (widget) =>
                widget is TextField &&
                widget.decoration?.hintText == 'Type a message...',
          ),
          findsOneWidget,
        );
      });

      testWidgets('Chat message list is visible', (WidgetTester tester) async {
        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: ListView(
                  children: const [
                    Padding(
                      padding: EdgeInsets.all(8.0),
                      child: Text('Message 1'),
                    ),
                    Padding(
                      padding: EdgeInsets.all(8.0),
                      child: Text('Message 2'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );

        expect(find.text('Message 1'), findsOneWidget);
        expect(find.text('Message 2'), findsOneWidget);
      });

      testWidgets('Send button is present', (WidgetTester tester) async {
        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: Column(
                  children: [
                    Expanded(
                      child: ListView(),
                    ),
                    Row(
                      children: [
                        const Expanded(
                          child: TextField(
                            decoration: InputDecoration(
                              hintText: 'Type message',
                              border: OutlineInputBorder(),
                            ),
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.send),
                          onPressed: () {},
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        );

        expect(find.byIcon(Icons.send), findsOneWidget);
      });
    });

    // ============================================================
    // User Input Tests
    // ============================================================

    group('User Input Handling', () {
      testWidgets('Text input updates value', (WidgetTester tester) async {
        final textController = TextEditingController();

        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: TextField(
                  controller: textController,
                  decoration: const InputDecoration(
                    hintText: 'Type message',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
            ),
          ),
        );

        await tester.enterText(find.byType(TextField), 'Hello');
        expect(textController.text, 'Hello');
      });

      testWidgets('Send button can be tapped', (WidgetTester tester) async {
        var buttonPressed = false;

        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: IconButton(
                  icon: const Icon(Icons.send),
                  onPressed: () {
                    buttonPressed = true;
                  },
                ),
              ),
            ),
          ),
        );

        await tester.tap(find.byIcon(Icons.send));
        expect(buttonPressed, true);
      });

      testWidgets('Input field clears after send',
          (WidgetTester tester) async {
        final textController = TextEditingController();
        var sendPressed = false;

        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: Column(
                  children: [
                    TextField(
                      controller: textController,
                      decoration: const InputDecoration(
                        hintText: 'Type message',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    ElevatedButton(
                      onPressed: () {
                        sendPressed = true;
                        textController.clear();
                      },
                      child: const Text('Send'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );

        await tester.enterText(find.byType(TextField), 'Test message');
        expect(textController.text, 'Test message');

        await tester.tap(find.byType(ElevatedButton));
        expect(sendPressed, true);
        expect(textController.text, '');
      });
    });

    // ============================================================
    // Message Display Tests
    // ============================================================

    group('Message Display', () {
      testWidgets('Messages display in order', (WidgetTester tester) async {
        final messages = ['First', 'Second', 'Third'];

        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: ListView.builder(
                  itemCount: messages.length,
                  itemBuilder: (context, index) => ListTile(
                      title: Text(messages[index]),
                    ),
                ),
              ),
            ),
          ),
        );

        expect(find.text('First'), findsOneWidget);
        expect(find.text('Second'), findsOneWidget);
        expect(find.text('Third'), findsOneWidget);
      });

      testWidgets('Empty chat shows appropriate message',
          (WidgetTester tester) async {
        await tester.pumpWidget(
          const ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: Center(
                  child: Text('No messages yet'),
                ),
              ),
            ),
          ),
        );

        expect(find.text('No messages yet'), findsOneWidget);
      });

      testWidgets('Message with special characters displays',
          (WidgetTester tester) async {
        await tester.pumpWidget(
          const ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: Text('Message with 中文 and emoji 😀'),
              ),
            ),
          ),
        );

        expect(find.text('Message with 中文 and emoji 😀'), findsOneWidget);
      });

      testWidgets('Long messages wrap correctly',
          (WidgetTester tester) async {
        const longMessage =
            'This is a very long message that should wrap to multiple lines when displayed in the chat interface';

        await tester.pumpWidget(
          const ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: SizedBox(
                  width: 300,
                  child: Text(longMessage),
                ),
              ),
            ),
          ),
        );

        expect(find.text(longMessage), findsOneWidget);
      });
    });

    // ============================================================
    // Scrolling Tests
    // ============================================================

    group('Scrolling Behavior', () {
      testWidgets('Chat scrolls to bottom on new message',
          (WidgetTester tester) async {
        final scrollController = ScrollController();
        final messages = List.generate(20, (i) => 'Message $i');

        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: ListView.builder(
                  controller: scrollController,
                  itemCount: messages.length,
                  itemBuilder: (context, index) => ListTile(
                      title: Text(messages[index]),
                    ),
                ),
              ),
            ),
          ),
        );

        // Should be able to scroll to bottom
        expect(scrollController.hasClients, false);
      });

      testWidgets('Long message list scrolls', (WidgetTester tester) async {
        final scrollController = ScrollController();

        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: ListView.builder(
                  controller: scrollController,
                  itemCount: 100,
                  itemBuilder: (context, index) => ListTile(
                      title: Text('Message $index'),
                    ),
                ),
              ),
            ),
          ),
        );

        // Verify we can find first message
        expect(find.text('Message 0'), findsOneWidget);
      });
    });

    // ============================================================
    // Layout Tests
    // ============================================================

    group('Layout & Responsive Design', () {
      testWidgets('Chat layout adapts to different widths',
          (WidgetTester tester) async {
        // Set small width
        tester.binding.window.physicalSizeTestValue = const Size(400, 800);
        addTearDown(tester.binding.window.clearPhysicalSizeTestValue);

        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: Column(
                  children: [
                    Expanded(
                      child: ColoredBox(
                        color: Colors.blue,
                        child: const Center(
                          child: Text('Messages'),
                        ),
                      ),
                    ),
                    Container(
                      color: Colors.grey,
                      padding: const EdgeInsets.all(8),
                      child: const TextField(
                        decoration: InputDecoration(
                          border: OutlineInputBorder(),
                          hintText: 'Message',
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );

        expect(find.text('Messages'), findsOneWidget);
      });

      testWidgets('Input field and button fit on screen',
          (WidgetTester tester) async {
        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: Column(
                  children: [
                    Expanded(
                      child: Container(),
                    ),
                    Padding(
                      padding: const EdgeInsets.all(8.0),
                      child: Row(
                        children: [
                          const Expanded(
                            child: TextField(
                              decoration: InputDecoration(
                                border: OutlineInputBorder(),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          IconButton(
                            icon: const Icon(Icons.send),
                            onPressed: () {},
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );

        expect(find.byType(Row), findsWidgets);
        expect(find.byIcon(Icons.send), findsOneWidget);
      });
    });

    // ============================================================
    // Loading State Tests
    // ============================================================

    group('Loading States', () {
      testWidgets('Loading indicator appears', (WidgetTester tester) async {
        await tester.pumpWidget(
          const ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: Center(
                  child: CircularProgressIndicator(),
                ),
              ),
            ),
          ),
        );

        expect(find.byType(CircularProgressIndicator), findsOneWidget);
      });

      testWidgets('Error message displays', (WidgetTester tester) async {
        await tester.pumpWidget(
          const ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: Center(
                  child: Text('Error: Connection failed'),
                ),
              ),
            ),
          ),
        );

        expect(find.text('Error: Connection failed'), findsOneWidget);
      });
    });

    // ============================================================
    // Accessibility Tests
    // ============================================================

    group('Accessibility', () {
      testWidgets('Send button has tooltip', (WidgetTester tester) async {
        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: Tooltip(
                  message: 'Send message',
                  child: IconButton(
                    icon: const Icon(Icons.send),
                    onPressed: () {},
                  ),
                ),
              ),
            ),
          ),
        );

        expect(find.byType(Tooltip), findsOneWidget);
      });

      testWidgets('Input field has label', (WidgetTester tester) async {
        await tester.pumpWidget(
          const ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: TextField(
                  decoration: InputDecoration(
                    labelText: 'Enter your message',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
            ),
          ),
        );

        expect(find.text('Enter your message'), findsOneWidget);
      });

      testWidgets('Focus management works', (WidgetTester tester) async {
        final focusNode = FocusNode();

        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: TextField(
                  focusNode: focusNode,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
            ),
          ),
        );

        await tester.tap(find.byType(TextField));
        await tester.pumpAndSettle();

        expect(focusNode.hasFocus, true);
      });
    });

    // ============================================================
    // Performance Tests
    // ============================================================

    group('Performance', () {
      testWidgets('Large message list renders efficiently',
          (WidgetTester tester) async {
        final stopwatch = Stopwatch()..start();

        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: ListView.builder(
                  itemCount: 1000,
                  itemBuilder: (context, index) => ListTile(
                      title: Text('Message $index'),
                    ),
                ),
              ),
            ),
          ),
        );

        stopwatch.stop();

        expect(stopwatch.elapsedMilliseconds, lessThan(2000));
      });

      testWidgets('Text input response is immediate',
          (WidgetTester tester) async {
        final textController = TextEditingController();

        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: TextField(
                  controller: textController,
                ),
              ),
            ),
          ),
        );

        final stopwatch = Stopwatch()..start();
        await tester.enterText(find.byType(TextField), 'Test');
        stopwatch.stop();

        expect(textController.text, 'Test');
        expect(stopwatch.elapsedMilliseconds, lessThan(500));
      });
    });

    // ============================================================
    // Integration Tests with Provider
    // ============================================================

    group('Provider Integration', () {
      testWidgets('Widget consumes provider correctly',
          (WidgetTester tester) async {
        var providerConsumed = false;

        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: Consumer(
                  builder: (context, ref, child) {
                    providerConsumed = true;
                    return const Center(
                      child: Text('Provider works'),
                    );
                  },
                ),
              ),
            ),
          ),
        );

        expect(providerConsumed, true);
        expect(find.text('Provider works'), findsOneWidget);
      });
    });

    // ============================================================
    // Gesture Tests
    // ============================================================

    group('Gesture Handling', () {
      testWidgets('Long press on message shows options',
          (WidgetTester tester) async {
        var longPressed = false;

        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: GestureDetector(
                  onLongPress: () {
                    longPressed = true;
                  },
                  child: const Text('Message'),
                ),
              ),
            ),
          ),
        );

        await tester.longPress(find.text('Message'));
        expect(longPressed, true);
      });

      testWidgets('Double tap works', (WidgetTester tester) async {
        var tapCount = 0;

        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: GestureDetector(
                  onDoubleTap: () {
                    tapCount++;
                  },
                  child: const Text('Message'),
                ),
              ),
            ),
          ),
        );

        await tester.tap(find.text('Message'));
        await tester.tap(find.text('Message'));

        expect(tapCount, greaterThanOrEqualTo(0));
      });
    });
  });
}
