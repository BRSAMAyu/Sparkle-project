#include <flutter/runtime_effect.glsl>

uniform vec2 u_resolution;
uniform float u_time;

uniform vec4 u_burst0;
uniform vec4 u_burst1;
uniform vec4 u_burst2;
uniform vec4 u_burst3;

float ring(vec2 uv, vec2 origin, float age, float strength) {
  if (age < 0.0 || age > 1.2) return 0.0;
  float radius = age * (0.35 + strength * 0.3);
  float width = 0.08 + strength * 0.05;
  float d = distance(uv, origin);
  float wave = smoothstep(radius + width, radius, d) *
      smoothstep(radius - width, radius, d);
  return wave * (1.0 - age * 0.7);
}

float glow(vec2 uv, vec2 origin, float age, float strength) {
  if (age < 0.0 || age > 1.2) return 0.0;
  float d = distance(uv, origin);
  float falloff = exp(-d * (6.0 + strength * 2.0));
  return falloff * (1.0 - age * 0.8);
}

out vec4 fragColor;

void main() {
  vec2 coord = FlutterFragCoord().xy;
  vec2 uv = coord / u_resolution;

  float intensity = 0.0;

  vec2 origin = u_burst0.xy;
  float start = u_burst0.z;
  float strength = u_burst0.w;
  if (strength > 0.0) {
    float age = u_time - start;
    intensity += ring(uv, origin, age, strength);
    intensity += glow(uv, origin, age, strength) * 0.6;
  }

  origin = u_burst1.xy;
  start = u_burst1.z;
  strength = u_burst1.w;
  if (strength > 0.0) {
    float age = u_time - start;
    intensity += ring(uv, origin, age, strength);
    intensity += glow(uv, origin, age, strength) * 0.6;
  }

  origin = u_burst2.xy;
  start = u_burst2.z;
  strength = u_burst2.w;
  if (strength > 0.0) {
    float age = u_time - start;
    intensity += ring(uv, origin, age, strength);
    intensity += glow(uv, origin, age, strength) * 0.6;
  }

  origin = u_burst3.xy;
  start = u_burst3.z;
  strength = u_burst3.w;
  if (strength > 0.0) {
    float age = u_time - start;
    intensity += ring(uv, origin, age, strength);
    intensity += glow(uv, origin, age, strength) * 0.6;
  }

  vec3 color = vec3(0.9, 0.6, 0.2) * intensity;
  fragColor = vec4(color, intensity);
}
