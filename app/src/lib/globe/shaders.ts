/**
 * GLSL for the globe. All three materials are ShaderMaterial (not Raw), so
 * three.js prepends cameraPosition, the matrices and the colour-space
 * helpers; each fragment shader ends with the tonemapping/colorspace chunks
 * so output is encoded to renderer.outputColorSpace (sRGB). Colour textures
 * use SRGBColorSpace and are decoded to linear by the GPU on sampling.
 */

export const globeVertexShader = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vNormalW;
  varying vec3 vPosW;
  void main() {
    vUv = uv;
    vec4 wp = modelMatrix * vec4(position, 1.0);
    vPosW = wp.xyz;
    vNormalW = normalize(mat3(modelMatrix) * normal);
    gl_Position = projectionMatrix * viewMatrix * wp;
  }
`;

export const globeFragmentShader = /* glsl */ `
  uniform sampler2D mapA;
  uniform sampler2D mapB;
  uniform sampler2D normalA;
  uniform sampler2D normalB;
  uniform float mixAmount;       // (t - a) / 5
  uniform float normalStrengthA; // 0 while slice a has no normal map yet
  uniform float normalStrengthB;
  uniform float normalAmount;    // global normal-map toggle / relief scale
  uniform float texturesReady;   // 0 = neutral shaded sphere, 1 = paleogeography
  uniform vec3 baseColor;
  uniform vec3 lightDir;         // world space, unit, surface -> light
  uniform float ambient;
  uniform float wrap;
  uniform vec3 rimColor;
  uniform float rimStrength;

  varying vec2 vUv;
  varying vec3 vNormalW;
  varying vec3 vPosW;

  void main() {
    vec3 N0 = normalize(vNormalW);
    vec3 V = normalize(cameraPosition - vPosW);

    // Always sample (no texture reads inside branches: keeps mip selection valid).
    vec3 ca = texture2D(mapA, vUv).rgb;
    vec3 cb = texture2D(mapB, vUv).rgb;
    vec3 albedo = mix(baseColor, mix(ca, cb, mixAmount), texturesReady);

    // Tangent-space normals. The pipeline (data/scripts/textures/render.py)
    // encodes green as +dz toward image-down (south); flip to north-up.
    vec3 na = texture2D(normalA, vUv).xyz * 2.0 - 1.0;
    vec3 nb = texture2D(normalB, vUv).xyz * 2.0 - 1.0;
    na.y = -na.y;
    nb.y = -nb.y;
    const vec3 flatN = vec3(0.0, 0.0, 1.0);
    vec3 nts = mix(mix(flatN, na, normalStrengthA), mix(flatN, nb, normalStrengthB), mixAmount);
    // render.py divides dz/dx by cos(lat) (clamped at 0.05), which exaggerates
    // relief toward the poles and draws a radial fan there: fade normals out
    // poleward of ~70 degrees (|sin lat| 0.94..0.995).
    float polarFade = 1.0 - smoothstep(0.94, 0.995, abs(N0.y));
    nts.xy *= normalAmount * texturesReady * polarFade;
    nts = normalize(nts);
    vec3 t = cross(vec3(0.0, 1.0, 0.0), N0);          // east
    float tl = length(t);
    vec3 T = tl > 1e-4 ? t / tl : vec3(0.0, 0.0, -1.0);
    vec3 B = cross(N0, T);                            // north
    vec3 N = normalize(T * nts.x + B * nts.y + N0 * nts.z);

    // Soft wrap diffuse: no hard terminator, relief stays readable.
    float diffuse = max(0.0, (dot(N, lightDir) + wrap) / (1.0 + wrap));
    vec3 color = albedo * (ambient + (1.0 - ambient) * diffuse);

    // Subtle fresnel rim toward the limb.
    float fres = pow(1.0 - clamp(dot(N0, V), 0.0, 1.0), 4.0);
    color = mix(color, rimColor, fres * rimStrength);

    gl_FragColor = vec4(color, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

/**
 * Atmosphere: back faces of a shell slightly larger than the Earth, additive.
 * Glow depends on how close the view ray passes to the Earth's centre, so it
 * is brightest at the limb and fades to exactly zero at the shell edge.
 */
export const atmosphereVertexShader = /* glsl */ `
  varying vec3 vPosW;
  void main() {
    vec4 wp = modelMatrix * vec4(position, 1.0);
    vPosW = wp.xyz;
    gl_Position = projectionMatrix * viewMatrix * wp;
  }
`;

export const atmosphereFragmentShader = /* glsl */ `
  uniform vec3 glowColor;
  uniform float intensity;
  uniform float innerRadius;
  uniform float outerRadius;
  uniform vec3 lightDir;
  varying vec3 vPosW;
  void main() {
    vec3 rd = normalize(vPosW - cameraPosition);
    float b = length(cross(cameraPosition, rd));      // ray distance to centre
    float x = clamp((outerRadius - b) / (outerRadius - innerRadius), 0.0, 1.0);
    float glow = x * x * x;
    vec3 closest = cameraPosition + rd * dot(-cameraPosition, rd);
    float lit = 0.55 + 0.45 * dot(normalize(closest), lightDir);
    gl_FragColor = vec4(glowColor * glow * intensity * lit, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

export const starsVertexShader = /* glsl */ `
  attribute float aSize;
  attribute float aBright;
  uniform float pixelRatio;
  varying float vBright;
  void main() {
    vBright = aBright;
    gl_PointSize = aSize * pixelRatio;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

export const starsFragmentShader = /* glsl */ `
  uniform float opacity;
  varying float vBright;
  void main() {
    float d = length(gl_PointCoord - 0.5);
    float a = smoothstep(0.5, 0.1, d);
    gl_FragColor = vec4(vec3(0.85, 0.9, 1.0) * vBright * a * opacity, 1.0);
    #include <colorspace_fragment>
  }
`;
