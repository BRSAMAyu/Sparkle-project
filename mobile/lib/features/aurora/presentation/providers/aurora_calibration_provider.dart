import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/aurora/data/models/aurora_calibration_card.dart';
import 'package:sparkle/features/aurora/data/repositories/aurora_calibration_repository.dart';

final auroraCalibrationSurfaceProvider =
    FutureProvider.autoDispose.family<AuroraCalibrationSurface, String?>(
  (ref, planId) async => ref
      .read(auroraCalibrationRepositoryProvider)
      .getCalibrationCards(planId: planId),
);
