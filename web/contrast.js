// Display-referred contrast for model materials, driven by one shared uniform (1 = unchanged).
const U = { value: 1 };
export const setContrast = v => { U.value = v; };
export const getContrast = () => U.value;
export function applyContrast(mat) {
  if (!mat || mat.userData.ctx_ct) return;
  mat.userData.ctx_ct = true;
  const prev = mat.onBeforeCompile;
  mat.onBeforeCompile = (sh, r) => {
    if (prev) prev(sh, r);
    sh.uniforms.uContrast = U;
    sh.fragmentShader = 'uniform float uContrast;\n' + sh.fragmentShader.replace('#include <dithering_fragment>', '#include <dithering_fragment>\n  gl_FragColor.rgb = clamp((gl_FragColor.rgb - 0.5) * uContrast + 0.5, 0.0, 1.0);');
  };
  const key = mat.customProgramCacheKey ? mat.customProgramCacheKey() : '';
  mat.customProgramCacheKey = () => key + '|ct';
  mat.needsUpdate = true;
}
