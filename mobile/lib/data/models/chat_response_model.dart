import 'package:json_annotation/json_annotation.dart';

part 'chat_response_model.g.dart';

@JsonSerializable()
class ChatResponseModel {
  ChatResponseModel({
    required this.message,
    required this.conversationId,
    this.widgets,
    this.toolResults,
    this.hasErrors = false,
  });

  factory ChatResponseModel.fromJson(Map<String, dynamic> json) =>
      _$ChatResponseModelFromJson(json);
  final String message;
  @JsonKey(name: 'conversation_id')
  final String conversationId;
  final List<Map<String, dynamic>>? widgets;
  @JsonKey(name: 'tool_results')
  final List<Map<String, dynamic>>? toolResults;
  @JsonKey(name: 'has_errors')
  final bool hasErrors;
  Map<String, dynamic> toJson() => _$ChatResponseModelToJson(this);
}
