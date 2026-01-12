#include <flutter/runtime_effect.glsl>

uniform float u_time;
uniform float u_intensity; // 0.0 to 1.0
uniform vec2 u_resolution;

// Simplex noise function (simplified)
vec3 permute(vec3 x) { return mod(((x*34.0)+1.0)*x, 289.0); }

float snoise(vec2 v){
  const vec4 C = vec4(0.211324865405187, 0.366025403784439,
           -0.577350269189626, 0.024390243902439);
  vec2 i  = floor(v + dot(v, C.yy) );
  vec2 x0 = v -   i + dot(i, C.xx);
  vec2 i1;
  i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod(i, 289.0);
  vec3 p = permute( permute( i.y + vec3(0.0, i1.y, 1.0 ))
  + i.x + vec3(0.0, i1.x, 1.0 ));
  vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy),
    dot(x12.zw,x12.zw)), 0.0);
  m = m*m ;
  m = m*m ;
  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 ox = floor(x + 0.5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - 0.85373472095314 * ( a0*a0 + h*h );
  vec3 g;
  g.x  = a0.x  * x0.x  + h.x  * x0.y;
  g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130.0 * dot(m, g);
}

out vec4 fragColor;

void main() {
    vec2 coords = FlutterFragCoord().xy;
    vec2 uv = coords / u_resolution;
    uv = uv * 2.0 - 1.0; // Center at 0,0
    
    // Distance from center
    float d = length(uv);
    
    // Deform radius with noise based on time and angle
    float angle = atan(uv.y, uv.x);
    float n = snoise(vec2(angle * 3.0, u_time * 2.0 + d * 2.0));
    
    // Core shape
    float radius = 0.3 + (u_intensity * 0.2); // Grow with intensity
    float flame_edge = radius + n * 0.1;
    
    // Soft glow
    float glow = 1.0 - smoothstep(0.0, flame_edge, d);
    
    // Color mixing
    vec3 coreColor = vec3(1.0, 0.9, 0.5); // Hot center
    vec3 outerColor = vec3(1.0, 0.4, 0.1); // Red/Orange edge
    vec3 finalColor = mix(outerColor, coreColor, glow * 2.0);
    
    // Alpha
    float alpha = glow;
    
    fragColor = vec4(finalColor * alpha, alpha);
}
