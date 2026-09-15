import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_motion.dart';

class DashboardCardCarousel extends StatefulWidget {
  const DashboardCardCarousel({
    required this.cards,
    this.cardIds,
    this.preferredInitialCardId,
    super.key,
  });

  static const double carouselCardHeight = 200;

  final List<Widget> cards;
  final List<String>? cardIds;
  final String? preferredInitialCardId;

  @override
  State<DashboardCardCarousel> createState() => _DashboardCardCarouselState();
}

class _DashboardCardCarouselState extends State<DashboardCardCarousel> {
  late final PageController _pageController;
  late int _currentPage;

  @override
  void initState() {
    super.initState();
    _currentPage = _resolveInitialPage();
    _pageController = PageController(
      viewportFraction: 0.92,
      initialPage: _currentPage,
    );
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => DashboardEntrance(
        index: 7,
        slideOffset: Offset.zero,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              height: DashboardCardCarousel.carouselCardHeight,
              child: PageView.builder(
                controller: _pageController,
                itemCount: widget.cards.length,
                onPageChanged: (page) {
                  setState(() {
                    _currentPage = page;
                  });
                },
                itemBuilder: (context, index) => Padding(
                  padding: const EdgeInsets.symmetric(horizontal: DS.spacing4),
                  child: widget.cards[index],
                ),
              ),
            ),
            if (widget.cards.length > 1) ...[
              const SizedBox(height: DS.spacing8),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(
                  widget.cards.length,
                  (index) => AnimatedContainer(
                    key: ValueKey('dashboard-carousel-indicator-$index'),
                    duration: DS.durationFast,
                    curve: DS.motionCurve(SparkleMotionToken.micro),
                    width: _currentPage == index ? 20 : 8,
                    height: 8,
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    decoration: BoxDecoration(
                      color: _currentPage == index
                          ? DS.brandPrimary
                          : DS.brandPrimary10,
                      borderRadius: DS.borderRadiusFull,
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
      );

  int _resolveInitialPage() {
    final preferredInitialCardId = widget.preferredInitialCardId;
    final cardIds = widget.cardIds;
    if (preferredInitialCardId == null ||
        cardIds == null ||
        cardIds.length != widget.cards.length) {
      return 0;
    }
    final index = cardIds.indexOf(preferredInitialCardId);
    return index < 0 ? 0 : index;
  }
}
