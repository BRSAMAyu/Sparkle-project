/// Base model class for data models with JSON serialization
///
/// Provides a common interface for models that need to be
/// serialized to/from JSON
abstract class BaseModel {
  /// Convert the model to a JSON map
  Map<String, dynamic> toJson();
}
