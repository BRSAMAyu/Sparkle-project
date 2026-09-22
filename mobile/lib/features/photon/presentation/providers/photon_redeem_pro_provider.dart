import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/photon/data/models/photon_redeem_pro_model.dart';
import 'package:sparkle/features/photon/data/repositories/photon_redeem_pro_repository.dart';

/// D-COMM-2：光子兑 Pro provider（快照 autoDispose，重进即重取；动作经仓库直调）。
final photonRedeemProRepositoryProvider = Provider<PhotonRedeemProRepository>((
  ref,
) {
  final apiClient = ref.watch(apiClientProvider);
  return PhotonRedeemProRepository(apiClient);
});

class PhotonRedeemProOverviewNotifier
    extends AutoDisposeAsyncNotifier<PhotonRedeemProOverview> {
  @override
  Future<PhotonRedeemProOverview> build() =>
      ref.watch(photonRedeemProRepositoryProvider).getOverview();
}

final photonRedeemProOverviewProvider = AsyncNotifierProvider.autoDispose<
    PhotonRedeemProOverviewNotifier, PhotonRedeemProOverview>(
  PhotonRedeemProOverviewNotifier.new,
);
