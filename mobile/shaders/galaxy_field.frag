#include <flutter/runtime_effect.glsl>

uniform vec2 u_resolution;
uniform float u_time;
uniform float u_strength;
uniform float u_noiseScale;

float hash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 34.345);
  return fract(p.x * p.y);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  float a = hash(i);
  float b = hash(i + vec2(1.0, 0.0));
  float c = hash(i + vec2(0.0, 1.0));
  float d = hash(i + vec2(1.0, 1.0));
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(a, b, u.x) + (c - a) * u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
}

float fbm(vec2 p) {
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 4; i++) {
    v += a * noise(p);
    p *= 2.0;
    a *= 0.5;
  }
  return v;
}

out vec4 fragColor;

void main() {
  vec2 coord = FlutterFragCoord().xy;
  vec2 uv = coord / u_resolution;
  vec2 centered = uv * 2.0 - 1.0;
  centered.x *= u_resolution.x / max(u_resolution.y, 1.0);

  float dist = length(centered);
  float field = smoothstep(1.2, 0.0, dist);

  vec2 flow = centered * (1.2 + u_strength * 0.4);
  flow += vec2(sin(u_time * 0.6), cos(u_time * 0.5)) * 0.15;
  float n = fbm(flow * u_noiseScale + u_time * 0.08);

  float glow = field * (0.4 + n * 0.6) * (0.6 + u_strength);
  vec3 base = vec3(0.02, 0.05, 0.1);
  vec3 accent = vec3(0.15, 0.35, 0.6);
  vec3 color = mix(base, accent, glow);

  fragColor = vec4(color, 1.0);
}
