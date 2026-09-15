import 'dart:async';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/documents/presentation/providers/document_library_provider.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_provider.dart';

enum GalaxyDocumentUploadPhase {
  idle,
  uploading,
  queued,
  extracting,
  findingKnowledge,
  buildingNodes,
  success,
  failed,
}

enum GalaxyDocumentUploadTargetKind {
  galaxyCore,
  worldPosition,
  node,
}

class GalaxyDocumentUploadTarget {
  const GalaxyDocumentUploadTarget._({
    required this.kind,
    required this.label,
    this.nodeId,
    this.worldPosition,
  });

  const GalaxyDocumentUploadTarget.galaxyCore({required String label})
      : this._(
          kind: GalaxyDocumentUploadTargetKind.galaxyCore,
          label: label,
        );

  const GalaxyDocumentUploadTarget.worldPosition({
    required String label,
    required Offset worldPosition,
  }) : this._(
          kind: GalaxyDocumentUploadTargetKind.worldPosition,
          label: label,
          worldPosition: worldPosition,
        );

  const GalaxyDocumentUploadTarget.node({
    required String label,
    required String nodeId,
    Offset? worldPosition,
  }) : this._(
          kind: GalaxyDocumentUploadTargetKind.node,
          label: label,
          nodeId: nodeId,
          worldPosition: worldPosition,
        );

  final GalaxyDocumentUploadTargetKind kind;
  final String label;
  final String? nodeId;
  final Offset? worldPosition;
}

class GalaxyDocumentUploadSession {
  const GalaxyDocumentUploadSession({
    required this.localSessionId,
    required this.fileName,
    required this.filePath,
    required this.fileSize,
    required this.mimeType,
    required this.originScreenPosition,
    required this.target,
    required this.phase,
    this.fileId,
    this.jobId,
    this.estimatedSeconds,
    this.uploadProgress = 0,
    this.processingProgressPercent = 0,
    this.nodesFound,
    this.errorMessage,
    this.isDismissing = false,
  });

  final String localSessionId;
  final String fileName;
  final String filePath;
  final int fileSize;
  final String mimeType;
  final Offset originScreenPosition;
  final GalaxyDocumentUploadTarget target;
  final GalaxyDocumentUploadPhase phase;
  final String? fileId;
  final String? jobId;
  final int? estimatedSeconds;
  final double uploadProgress;
  final int processingProgressPercent;
  final int? nodesFound;
  final String? errorMessage;
  final bool isDismissing;

  GalaxyDocumentUploadSession copyWith({
    String? localSessionId,
    String? fileName,
    String? filePath,
    int? fileSize,
    String? mimeType,
    Offset? originScreenPosition,
    GalaxyDocumentUploadTarget? target,
    GalaxyDocumentUploadPhase? phase,
    String? fileId,
    String? jobId,
    int? estimatedSeconds,
    double? uploadProgress,
    int? processingProgressPercent,
    int? Function()? nodesFound,
    String? Function()? errorMessage,
    bool? isDismissing,
  }) =>
      GalaxyDocumentUploadSession(
        localSessionId: localSessionId ?? this.localSessionId,
        fileName: fileName ?? this.fileName,
        filePath: filePath ?? this.filePath,
        fileSize: fileSize ?? this.fileSize,
        mimeType: mimeType ?? this.mimeType,
        originScreenPosition: originScreenPosition ?? this.originScreenPosition,
        target: target ?? this.target,
        phase: phase ?? this.phase,
        fileId: fileId ?? this.fileId,
        jobId: jobId ?? this.jobId,
        estimatedSeconds: estimatedSeconds ?? this.estimatedSeconds,
        uploadProgress: uploadProgress ?? this.uploadProgress,
        processingProgressPercent:
            processingProgressPercent ?? this.processingProgressPercent,
        nodesFound: nodesFound != null ? nodesFound() : this.nodesFound,
        errorMessage: errorMessage != null ? errorMessage() : this.errorMessage,
        isDismissing: isDismissing ?? this.isDismissing,
      );

  bool get isTerminal =>
      phase == GalaxyDocumentUploadPhase.success ||
      phase == GalaxyDocumentUploadPhase.failed;

  bool get isBackgroundProcessing =>
      phase == GalaxyDocumentUploadPhase.queued ||
      phase == GalaxyDocumentUploadPhase.extracting ||
      phase == GalaxyDocumentUploadPhase.findingKnowledge ||
      phase == GalaxyDocumentUploadPhase.buildingNodes;

  double get overallProgress {
    switch (phase) {
      case GalaxyDocumentUploadPhase.idle:
        return 0;
      case GalaxyDocumentUploadPhase.uploading:
        return uploadProgress.clamp(0, 1) * 0.28;
      case GalaxyDocumentUploadPhase.queued:
        return 0.34;
      case GalaxyDocumentUploadPhase.extracting:
        return 0.34 + (processingProgressPercent / 100) * 0.18;
      case GalaxyDocumentUploadPhase.findingKnowledge:
        return 0.52 + (processingProgressPercent / 100) * 0.24;
      case GalaxyDocumentUploadPhase.buildingNodes:
        return 0.76 + (processingProgressPercent / 100) * 0.2;
      case GalaxyDocumentUploadPhase.success:
      case GalaxyDocumentUploadPhase.failed:
        return 1;
    }
  }
}

class GalaxyDocumentUploadState {
  const GalaxyDocumentUploadState({this.session});

  final GalaxyDocumentUploadSession? session;

  GalaxyDocumentUploadState copyWith({
    GalaxyDocumentUploadSession? Function()? session,
  }) =>
      GalaxyDocumentUploadState(
        session: session != null ? session() : this.session,
      );
}

class GalaxyDocumentUploadNotifier
    extends StateNotifier<GalaxyDocumentUploadState> {
  GalaxyDocumentUploadNotifier(this._ref)
      : super(const GalaxyDocumentUploadState());

  final Ref _ref;
  Timer? _pollTimer;
  Timer? _dismissTimer;
  String? _activeSessionId;
  int _consecutivePollFailures = 0;

  @override
  void dispose() {
    _pollTimer?.cancel();
    _dismissTimer?.cancel();
    super.dispose();
  }

  bool get hasActiveUpload {
    final session = state.session;
    return session != null && !session.isTerminal;
  }

  Future<bool> uploadDocument(
    File file, {
    required GalaxyDocumentUploadTarget target,
    required Offset originScreenPosition,
  }) async {
    if (hasActiveUpload) {
      return false;
    }

    _pollTimer?.cancel();
    _dismissTimer?.cancel();
    _consecutivePollFailures = 0;

    final localSessionId = DateTime.now().microsecondsSinceEpoch.toString();
    _activeSessionId = localSessionId;
    state = GalaxyDocumentUploadState(
      session: GalaxyDocumentUploadSession(
        localSessionId: localSessionId,
        fileName: file.path.split('/').last,
        filePath: file.path,
        fileSize: await file.length(),
        mimeType: '',
        originScreenPosition: originScreenPosition,
        target: target,
        phase: GalaxyDocumentUploadPhase.uploading,
      ),
    );

    try {
      final ticket = await _ref.read(fileUploadServiceProvider).uploadDocument(
        file,
        onProgress: (progress) {
          _updateActiveSession(
            localSessionId,
            (session) => session.copyWith(
              uploadProgress: progress.clamp(0, 1),
            ),
          );
        },
      );

      _updateActiveSession(
        localSessionId,
        (session) => session.copyWith(
          fileId: ticket.fileId,
          jobId: ticket.jobId,
          estimatedSeconds: ticket.estimatedSeconds,
          mimeType: ticket.mimeType,
          phase: GalaxyDocumentUploadPhase.queued,
          uploadProgress: 1,
          processingProgressPercent: 0,
          errorMessage: () => null,
        ),
      );

      _startPolling(ticket.fileId, localSessionId);
      return true;
    } catch (error) {
      _setFailure(localSessionId, _friendlyErrorMessage(error));
      return false;
    }
  }

  Future<void> retryLastUpload() async {
    final session = state.session;
    if (session == null || session.filePath.isEmpty || hasActiveUpload) {
      return;
    }

    final file = File(session.filePath);
    if (!file.existsSync()) {
      _setFailure(
        session.localSessionId,
        'The document is no longer available on this device.',
      );
      return;
    }

    await uploadDocument(
      file,
      target: session.target,
      originScreenPosition: session.originScreenPosition,
    );
  }

  void clearSession() {
    _pollTimer?.cancel();
    _dismissTimer?.cancel();
    _activeSessionId = null;
    state = const GalaxyDocumentUploadState();
  }

  void _startPolling(String fileId, String localSessionId) {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (timer) async {
      if (_activeSessionId != localSessionId) {
        timer.cancel();
        return;
      }

      try {
        final status = await _ref
            .read(fileUploadServiceProvider)
            .getDocumentStatus(fileId);
        _consecutivePollFailures = 0;
        final nextPhase = _phaseForStatus(status);

        _updateActiveSession(
          localSessionId,
          (session) => session.copyWith(
            phase: nextPhase,
            processingProgressPercent: status.progressPercent,
            nodesFound: () => status.nodesFound,
            errorMessage: () => status.error,
          ),
        );

        if (status.isDone) {
          timer.cancel();
          await _handleSuccess(localSessionId);
        } else if (status.isFailed) {
          timer.cancel();
          _setFailure(
            localSessionId,
            status.error ?? 'We could not turn that document into stars yet.',
          );
        }
      } catch (_) {
        _consecutivePollFailures += 1;
        if (_consecutivePollFailures >= 4) {
          timer.cancel();
          _setFailure(
            localSessionId,
            'The signal from the galaxy is faint right now. Try again in a moment.',
          );
        }
      }
    });
  }

  Future<void> _handleSuccess(String localSessionId) async {
    _updateActiveSession(
      localSessionId,
      (session) => session.copyWith(
        phase: GalaxyDocumentUploadPhase.success,
        processingProgressPercent: 100,
        errorMessage: () => null,
      ),
    );
    _ref.read(galaxyRefreshTriggerProvider.notifier).state++;
    unawaited(_ref.read(documentLibraryProvider.notifier).refresh());
    _dismissTimer?.cancel();
    _dismissTimer = Timer(const Duration(seconds: 5), () {
      _updateActiveSession(
        localSessionId,
        (session) => session.copyWith(isDismissing: true),
      );
      Future<void>.delayed(const Duration(milliseconds: 500), clearSession);
    });
  }

  void _setFailure(String localSessionId, String message) {
    _pollTimer?.cancel();
    _dismissTimer?.cancel();
    _updateActiveSession(
      localSessionId,
      (session) => session.copyWith(
        phase: GalaxyDocumentUploadPhase.failed,
        errorMessage: () => message,
        isDismissing: false,
      ),
    );
  }

  void _updateActiveSession(
    String localSessionId,
    GalaxyDocumentUploadSession Function(GalaxyDocumentUploadSession session)
        transform,
  ) {
    final session = state.session;
    if (session == null || session.localSessionId != localSessionId) {
      return;
    }
    state = state.copyWith(session: () => transform(session));
  }

  GalaxyDocumentUploadPhase _phaseForStatus(DocumentProcessingStatus status) {
    if (status.isDone) {
      return GalaxyDocumentUploadPhase.success;
    }
    if (status.isFailed) {
      return GalaxyDocumentUploadPhase.failed;
    }
    switch (status.stage) {
      case 'extracting':
        return GalaxyDocumentUploadPhase.extracting;
      case 'embedding':
        return GalaxyDocumentUploadPhase.findingKnowledge;
      case 'building_nodes':
        return GalaxyDocumentUploadPhase.buildingNodes;
      case 'queued':
      default:
        return GalaxyDocumentUploadPhase.queued;
    }
  }

  String _friendlyErrorMessage(Object error) {
    if (error is UploadFailedException) {
      return error.message;
    }
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map<String, dynamic>) {
        final detail = data['detail']?.toString();
        if (detail != null && detail.trim().isNotEmpty) {
          return detail.trim();
        }
      }
      if (error.message != null && error.message!.trim().isNotEmpty) {
        return error.message!.trim();
      }
    }
    return 'The document slipped away before it reached the constellation.';
  }
}

final galaxyDocumentUploadProvider = StateNotifierProvider<
    GalaxyDocumentUploadNotifier, GalaxyDocumentUploadState>(
  GalaxyDocumentUploadNotifier.new,
);
