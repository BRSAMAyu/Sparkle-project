import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/features/photon/presentation/screens/photon_transfer_screen.dart';
import 'package:sparkle/features/photon/presentation/widgets/photon_balance_card.dart';

class PhotonRoutes {
  static const String transactionHistory = '/photon/history';
  static const String transfer = '/photon/transfer'; // 新增

  static List<RouteBase> get routes => [
        GoRoute(
          path: transactionHistory,
          name: 'photonTransactionHistory',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const TransactionHistoryScreen(),
          ),
        ),
        // 新增转账路由
        GoRoute(
          path: transfer,
          name: 'photonTransfer',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const PhotonTransferScreen(),
          ),
        ),
      ];
}
