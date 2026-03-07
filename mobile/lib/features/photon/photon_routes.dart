import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/photon/presentation/widgets/photon_balance_card.dart';

Page<dynamic> _buildTransitionPage({
  required GoRouterState state,
  required Widget child,
  SharedAxisTransitionType type = SharedAxisTransitionType.horizontal,
}) =>
    CustomTransitionPage<void>(
      key: state.pageKey,
      child: child,
      transitionsBuilder: (context, animation, secondaryAnimation, child) =>
          SharedAxisTransition(
        animation: animation,
        secondaryAnimation: secondaryAnimation,
        transitionType: type,
        child: child,
      ),
    );

class PhotonRoutes {
  static const String transactionHistory = '/photon/history';

  static List<RouteBase> get routes => [
        GoRoute(
          path: transactionHistory,
          name: 'photonTransactionHistory',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const TransactionHistoryScreen(),
          ),
        ),
      ];
}
