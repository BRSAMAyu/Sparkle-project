import 'package:flutter/widgets.dart';
import 'package:sparkle/features/home/presentation/screens/openclaw_hub_screen.dart';

class OpenClawScreen extends StatelessWidget {
  const OpenClawScreen({
    super.key,
    this.initialSection = OpenClawHubSection.overview,
  });

  final OpenClawHubSection initialSection;

  @override
  Widget build(BuildContext context) => OpenClawHubScreen(
        initialSection: initialSection,
      );
}
