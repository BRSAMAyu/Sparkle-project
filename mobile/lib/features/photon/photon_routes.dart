import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/features/photon/presentation/screens/photon_redeem_pro_screen.dart';
import 'package:sparkle/features/photon/presentation/screens/photon_transfer_screen.dart';
import 'package:sparkle/features/photon/presentation/widgets/photon_balance_card.dart';

class PhotonRoutes {
  static const String transactionHistory = '/photon/history';
  static const String transfer = '/photon/transfer'; // 新增
  static const String redeemPro = '/photon/redeem-pro'; // D-COMM-2 兑换出口

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
        // D-COMM-2：光子兑 Pro（「学出会员」奖励出口）
        GoRoute(
          path: redeemPro,
          name: 'photonRedeemPro',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const PhotonRedeemProScreen(),
          ),
        ),
      ];
}
