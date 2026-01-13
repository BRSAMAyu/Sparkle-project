import 'dart:isolate';
import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';
import 'package:llama_cpp_dart/llama_cpp_dart.dart';
import '../../analytics/services/local_feature_service.dart';
import '../models/edge_state_schema.dart';
import '../grammar/state_vector_grammar.dart';
import 'model_manager.dart';

// Placeholder for feature input
typedef FeatureVector = Map<String, dynamic>;

final edgeInferenceServiceProvider = Provider<EdgeInferenceService>((ref) {
  final featureService = ref.watch(localFeatureServiceProvider);
  return EdgeInferenceService(
    modelManager: ModelManager(),
    featureService: featureService,
  );
});

class _WorkerInitMessage {
  final String modelPath;
  _WorkerInitMessage(this.modelPath);
}

class _InferenceRequest {
  final FeatureVector features;
  final SendPort replyPort;
  _InferenceRequest(this.features, this.replyPort);
}

/// Manages the Edge AI lifecycle and communicates with the background worker.
class EdgeInferenceService {
  final Logger _logger = Logger();
  final ModelManager _modelManager;
  final LocalFeatureService _featureService;
  
  SendPort? _workerSendPort;
  bool _isReady = false;

  EdgeInferenceService({
    required ModelManager modelManager,
    required LocalFeatureService featureService,
  })  : _modelManager = modelManager,
        _featureService = featureService;

  /// Initializes the background isolate and loads the model.
  Future<void> initialize() async {
    if (_isReady) return;
    
    _logger.i('Initializing Edge Inference Service (Qwen3-0.6B)...');
    
    // Ensure model is present (Manual placement expected during dev)
    String modelPath;
    try {
      modelPath = await _modelManager.ensureModelDownloaded();
    } catch (e) {
      _logger.e('Qwen3-0.6B model not found. Edge AI waiting for manual file placement.', error: e);
      return;
    }
    
    // Spawn the worker isolate
    final receivePort = ReceivePort();
    await Isolate.spawn(_inferenceWorker, receivePort.sendPort);
    
    // Handshake
    final broadcastStream = receivePort.asBroadcastStream();
    final firstMsg = await broadcastStream.first;
    if (firstMsg is SendPort) {
      _workerSendPort = firstMsg;
      // Send Init Message with Model Path
      _workerSendPort!.send(_WorkerInitMessage(modelPath));
      _isReady = true;
      _logger.i('Edge Inference Worker Ready');
    }
  }

  /// Full JIT Cycle: Extract features -> Infer -> Map to State.
  Future<EdgeState?> runAnalysis() async {
    // Attempt lazy initialization
    if (!_isReady) {
      await initialize();
    }
    
    // Safety Guard: If init failed (e.g. model missing), abort gracefully.
    if (!_isReady || _workerSendPort == null) {
      _logger.w('Edge AI not ready (Worker Port is null). Skipping analysis.');
      return null;
    }

    try {
      // 1. Build Features from Isar
// ... existing code ...
      final features = await _featureService.buildFeatureVector();
      
      // 2. Inference
      final responsePort = ReceivePort();
      _workerSendPort!.send(_InferenceRequest(features, responsePort.sendPort));

      final response = await responsePort.first.timeout(const Duration(seconds: 10));
      responsePort.close();

      if (response is String && !response.startsWith('ERROR')) {
        // 3. Parse and Map
        final jsonMap = jsonDecode(response);
        final rawVector = RawStateVector.fromJson(jsonMap);
        return rawVector.toEdgeState();
      }
      
      _logger.e('Inference error: $response');
      return null;
    } catch (e) {
      _logger.e('Full analysis cycle failed', error: e);
      return null;
    }
  }

  /// The entry point for the background isolate.
  static void _inferenceWorker(SendPort mainSendPort) {
    final workerReceivePort = ReceivePort();
    mainSendPort.send(workerReceivePort.sendPort);

    Llama? llama;
    final logger = Logger();

    workerReceivePort.listen((message) {
      if (message is _WorkerInitMessage) {
        try {
          final params = ContextParams();
          params.context = 2048; 
          llama = Llama(message.modelPath, params);
          logger.i('Llama context initialized with Qwen3-0.6B');
        } catch (e) {
          logger.e('Failed to load Llama in worker isolate', error: e);
        }
      } else if (message is _InferenceRequest) {
        if (llama == null) {
          message.replyPort.send('ERROR: Model not loaded');
          return;
        }

        try {
          final featuresJson = jsonEncode(message.features);
          
          // Qwen3 Chat Format
          final prompt = '<|im_start|>system\nYou are a user state estimator. Given the JSON behavior data, predict the state vector.\n<|im_end|>\n'
              '<|im_start|>user\n$featuresJson\n<|im_end|>\n'
              '<|im_start|>assistant\n';

          final result = llama!.prompt(prompt, grammar: stateVectorGrammar);
          message.replyPort.send(result);
        } catch (e) {
          message.replyPort.send('ERROR: ${e.toString()}');
        }
      }
    });
  }
}
