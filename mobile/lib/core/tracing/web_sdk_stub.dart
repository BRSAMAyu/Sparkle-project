/// Stub file for web SDK when not on web platform
/// This avoids dart:html import issues on mobile platforms
library;

class WebTracerProvider {
  WebTracerProvider({required dynamic timeProvider});
}

class WebTimeProvider {}
