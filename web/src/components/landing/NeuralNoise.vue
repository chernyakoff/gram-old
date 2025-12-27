<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';

type NeuralNoiseProps = {
  opacity?: number;
  pointerStrength?: number;
  timeScale?: number;
};

const props = withDefaults(defineProps<NeuralNoiseProps>(), {
  opacity: 0.6,
  pointerStrength: 0.5,
  timeScale: 0.5,
});

const canvasRef = ref<HTMLCanvasElement | null>(null);
const glRef = ref<WebGLRenderingContext | null>(null);
const uniformsRef = ref<Record<string, WebGLUniformLocation | null>>({});
const rafRef = ref<number>(0);

const pointer = ref({ x: 0, y: 0, tx: 0, ty: 0 });
const scrollProgress = ref(0);
const startTS = ref(0);

const VERT = `
  precision mediump float;
  attribute vec2 a_position;
  varying vec2 vUv;
  void main() {
    vUv = 0.5 * (a_position + 1.0);
    gl_Position = vec4(a_position, 0.0, 1.0);
  }
`;

const FRAG = `
  precision mediump float;
  varying vec2 vUv;
  uniform float u_time;
  uniform float u_ratio;
  uniform vec2  u_pointer_position;
  uniform float u_scroll_progress;
  uniform float u_pointer_strength;
  uniform float u_time_scale;

  vec2 rotate(vec2 uv, float th) {
    return mat2(cos(th), sin(th), -sin(th), cos(th)) * uv;
  }

  float neuro_shape(vec2 uv, float t, float p) {
    vec2 sine_acc = vec2(0.0);
    vec2 res = vec2(0.0);
    float scale = 8.0;

    for (int j = 0; j < 15; j++) {
      uv = rotate(uv, 1.0);
      sine_acc = rotate(sine_acc, 1.0);
      vec2 layer = uv * scale + float(j) + sine_acc - t;
      sine_acc += sin(layer) + 2.4 * p;
      res += (0.5 + 0.5 * cos(layer)) / scale;
      scale *= 1.2;
    }
    return res.x + res.y;
  }

  void main() {
    vec2 uv = 0.5 * vUv;
    uv.x *= u_ratio;

    vec2 pointer = vUv - u_pointer_position;
    pointer.x *= u_ratio;
    float p = clamp(length(pointer), 0.0, 1.0);
    p = 0.5 * pow(1.0 - p, 2.0) * u_pointer_strength;

    float t = 0.001 * u_time * u_time_scale;

    float noise = neuro_shape(uv, t, p);
    noise = 1.2 * pow(noise, 3.0);
    noise += pow(noise, 10.0);
    noise = max(0.0, noise - 0.5);
    noise *= (1.0 - length(vUv - 0.5));

    vec3 base = normalize(vec3(
      0.2,
      0.5 + 0.4 * cos(3.0 * u_scroll_progress),
      0.5 + 0.5 * sin(3.0 * u_scroll_progress)
    ));

    vec3 color = base * noise;
    gl_FragColor = vec4(color, noise);
  }
`;

let cleanup: (() => void) | null = null;

onMounted(() => {
  const canvas = canvasRef.value;
  if (!canvas) return;

  const gl =
    (canvas.getContext('webgl') ||
      canvas.getContext('experimental-webgl')) as WebGLRenderingContext | null;

  if (!gl) {
    canvas.style.display = 'none';
    return;
  }

  glRef.value = gl;

  const compile = (src: string, type: number) => {
    const shader = gl.createShader(type);
    if (!shader) return null;
    gl.shaderSource(shader, src);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      console.error(gl.getShaderInfoLog(shader));
      gl.deleteShader(shader);
      return null;
    }
    return shader;
  };

  const vs = compile(VERT, gl.VERTEX_SHADER);
  const fs = compile(FRAG, gl.FRAGMENT_SHADER);
  if (!vs || !fs) return;

  const program = gl.createProgram();
  if (!program) return;
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    console.error(gl.getProgramInfoLog(program));
    return;
  }
  gl.useProgram(program);

  const vertices = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);
  const vbo = gl.createBuffer();
  if (!vbo) return;
  gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
  gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);

  const aPos = gl.getAttribLocation(program, 'a_position');
  gl.enableVertexAttribArray(aPos);
  gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

  const getU = (name: string) => gl.getUniformLocation(program, name);
  const uniforms = {
    u_time: getU('u_time'),
    u_ratio: getU('u_ratio'),
    u_pointer_position: getU('u_pointer_position'),
    u_scroll_progress: getU('u_scroll_progress'),
    u_pointer_strength: getU('u_pointer_strength'),
    u_time_scale: getU('u_time_scale'),
  };
  uniformsRef.value = uniforms;

  gl.uniform1f(uniforms.u_pointer_strength, props.pointerStrength);
  gl.uniform1f(uniforms.u_time_scale, props.timeScale);

  const resize = () => {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.floor(window.innerWidth * dpr);
    const h = Math.floor(window.innerHeight * dpr);
    canvas.width = w;
    canvas.height = h;
    canvas.style.width = `${window.innerWidth}px`;
    canvas.style.height = `${window.innerHeight}px`;
    gl.viewport(0, 0, w, h);
    gl.uniform1f(uniforms.u_ratio, w / h);
  };

  const updatePointer = (x: number, y: number) => {
    pointer.value.tx = x;
    pointer.value.ty = y;
  };

  const onPointerMove = (event: PointerEvent) => updatePointer(event.clientX, event.clientY);
  const onTouchMove = (event: TouchEvent) => {
    if (event.targetTouches?.[0]) {
      updatePointer(event.targetTouches[0].clientX, event.targetTouches[0].clientY);
    }
  };
  const onClick = (event: MouseEvent) => updatePointer(event.clientX, event.clientY);

  const onScroll = () => {
    scrollProgress.value = window.pageYOffset / (2 * window.innerHeight);
  };

  window.addEventListener('resize', resize);
  window.addEventListener('pointermove', onPointerMove);
  window.addEventListener('touchmove', onTouchMove, { passive: true });
  window.addEventListener('click', onClick);
  window.addEventListener('scroll', onScroll, { passive: true });

  resize();
  onScroll();

  startTS.value = performance.now();
  const loop = (now: number) => {
    rafRef.value = requestAnimationFrame(loop);

    const p = pointer.value;
    p.x += (p.tx - p.x) * 0.2;
    p.y += (p.ty - p.y) * 0.2;

    gl.uniform1f(uniforms.u_time, now - startTS.value);
    gl.uniform2f(uniforms.u_pointer_position, p.x / window.innerWidth, 1 - p.y / window.innerHeight);
    gl.uniform1f(uniforms.u_scroll_progress, scrollProgress.value);

    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  };
  rafRef.value = requestAnimationFrame(loop);

  cleanup = () => {
    cancelAnimationFrame(rafRef.value);
    window.removeEventListener('resize', resize);
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('touchmove', onTouchMove);
    window.removeEventListener('click', onClick);
    window.removeEventListener('scroll', onScroll);
    gl.deleteBuffer(vbo);
    gl.deleteProgram(program);
    gl.deleteShader(vs);
    gl.deleteShader(fs);
  };
});

onBeforeUnmount(() => {
  cleanup?.();
});
</script>

<template>
  <canvas
    ref="canvasRef"
    class="fixed inset-0 w-full h-full pointer-events-none z-0"
    :style="{ opacity: props.opacity }"
  />
</template>
