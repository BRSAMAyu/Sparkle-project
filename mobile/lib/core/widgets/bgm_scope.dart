import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:sparkle/core/services/bgm_service.dart';

class BgmScope extends StatefulWidget {
  const BgmScope({
    required this.track,
    required this.child,
    super.key,
    this.priority = BgmPriority.route,
  });

  final BgmTrack track;
  final BgmPriority priority;
  final Widget child;

  @override
  State<BgmScope> createState() => _BgmScopeState();
}

class _BgmScopeState extends State<BgmScope> {
  late Object _token;

  @override
  void initState() {
    super.initState();
    _token = BgmService.activate(
      widget.track,
      priority: widget.priority,
    );
  }

  @override
  void didUpdateWidget(covariant BgmScope oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.track != widget.track ||
        oldWidget.priority != widget.priority) {
      unawaited(
        BgmService.update(
          _token,
          track: widget.track,
          priority: widget.priority,
        ),
      );
    }
  }

  @override
  void dispose() {
    unawaited(BgmService.deactivate(_token));
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
