/**
 * Procedural star background. Positions come from a seeded LCG so they are
 * stable between visits; they are decoration and make no claim about the sky.
 */
import * as THREE from 'three';
import { starsVertexShader, starsFragmentShader } from './shaders';

export function createStars(count = 2600, radius = 40): THREE.Points {
  let seed = 20260906;
  const rand = () => (seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296;

  const pos = new Float32Array(count * 3);
  const size = new Float32Array(count);
  const bright = new Float32Array(count);
  for (let i = 0; i < count; i++) {
    const u = rand() * 2 - 1;
    const th = rand() * Math.PI * 2;
    const s = Math.sqrt(1 - u * u);
    pos[i * 3] = s * Math.cos(th) * radius;
    pos[i * 3 + 1] = u * radius;
    pos[i * 3 + 2] = s * Math.sin(th) * radius;
    const m = rand();
    bright[i] = 0.12 + 0.75 * m ** 6; // a few bright stars, many faint ones
    size[i] = 1.2 + 1.6 * m ** 3;
  }
  const geom = new THREE.BufferGeometry();
  geom.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geom.setAttribute('aSize', new THREE.BufferAttribute(size, 1));
  geom.setAttribute('aBright', new THREE.BufferAttribute(bright, 1));
  const mat = new THREE.ShaderMaterial({
    vertexShader: starsVertexShader,
    fragmentShader: starsFragmentShader,
    uniforms: { pixelRatio: { value: 1 }, opacity: { value: 0.8 } },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const points = new THREE.Points(geom, mat);
  points.frustumCulled = false;
  points.renderOrder = -2;
  return points;
}
