import { FireworksModel } from "./fireworks-model.js";
import { FireworksView } from "./fireworks-view.js";

const canvas = document.querySelector("#fireworks-canvas");
const fallback = document.querySelector("#fireworks-fallback");
const controls = document.querySelector("#play-controls");
const status = document.querySelector("#play-status");
const shape = document.querySelector("#shape");
const palette = document.querySelector("#palette");
const pause = document.querySelector("#pause");
const auto = document.querySelector("#auto");
const reduced = document.querySelector("#reduced-motion");

async function start() {
  const request = new AbortController();
  const timeout = setTimeout(() => request.abort(), 10000);
  let config;
  try {
    const response = await fetch("fireworks-config.json", {signal: request.signal});
    if (!response.ok) throw new Error("Configuration unavailable");
    config = await response.json();
  } finally { clearTimeout(timeout); }

  const model = new FireworksModel(config);
  const view = new FireworksView(canvas, config);
  const media = window.matchMedia("(prefers-reduced-motion: reduce)");
  let paused = true, frameId = null, lastTime = null, pageActive = true;
  let candidate = null;
  const pointers = new Set();
  reduced.checked = media.matches;

  function say(message) { status.textContent = message; }
  function updateControls() {
    pause.textContent = reduced.checked ? "静态模式" : paused ? "播放动画" : "暂停动画";
    pause.setAttribute("aria-pressed", String(paused));
    pause.disabled = reduced.checked;
    auto.disabled = reduced.checked;
    auto.setAttribute("aria-pressed", String(model.auto));
    auto.textContent = model.auto ? "关闭自动" : "自动表演";
  }
  function stopFrame() {
    if (frameId !== null) cancelAnimationFrame(frameId);
    frameId = lastTime = null;
  }
  function running() { return !paused && !reduced.checked && !document.hidden && pageActive; }
  function schedule() {
    if (running() && frameId === null) frameId = requestAnimationFrame(tick);
  }
  function tick(now) {
    frameId = null;
    if (!running()) { lastTime = null; return; }
    const dt = lastTime === null ? 0 : Math.min((now-lastTime)/1000, config.physics.max_step);
    lastTime = now;
    model.step(dt);
    view.draw(model);
    if (!model.auto && !model.rockets.length && !model.particles.length && !model.blooms.length) {
      paused = true;
      lastTime = null;
      updateControls();
      say("夜空静下来了，再点一下，为它添一束光。");
    }
    schedule();
  }
  function play() { paused = false; updateControls(); schedule(); }
  function fire(x = 0, y = 135, multiple = false) {
    if (reduced.checked) {
      if (multiple) {
        for (let index = 0; index < 5; index++) model.burst(-320+index*160,95+index%2*70,index%4,.75);
      } else model.burst(x,y,model.kind,.75);
      view.draw(model);
      say("静态绽放已呈现；可以换个位置，再放一束。");
    } else {
      if (multiple) model.finale(); else model.launch(x,y);
      play();
      say(multiple ? "五束烟花，一起点亮夜空。" : "烟花已升空，等它为你绽放。");
    }
  }
  function togglePause() {
    if (reduced.checked) return;
    paused = !paused;
    if (paused) stopFrame(); else schedule();
    updateControls();
    say(paused ? "动画已暂停，眼前这一刻为你停留。" : "动画继续播放。");
  }
  function toggleAuto() {
    if (reduced.checked) return;
    model.auto = !model.auto;
    if (model.auto) play();
    updateControls();
    say(model.auto ? "自动表演已开启，也可以点击加入自己的烟花。" : "自动表演已关闭，当前烟花将继续落下。");
  }
  function reset() {
    stopFrame();
    model.reset();
    shape.value = String(model.kind);
    palette.value = String(model.palette);
    paused = true;
    candidate = null;
    pointers.clear();
    updateControls();
    view.draw(model);
    say(reduced.checked ? "夜空已重置，点击呈现静态烟花。" : "夜空已重置，点击开始新的表演。");
  }
  function changeMotion() {
    stopFrame();
    paused = true;
    model.auto = false;
    updateControls();
    say(reduced.checked ? "减少动态已开启：点击直接呈现静态烟花。" : "动态效果已恢复，点击或播放按钮开始。");
  }

  document.querySelector("#launch").addEventListener("click", () => fire());
  document.querySelector("#finale").addEventListener("click", () => fire(0,135,true));
  document.querySelector("#reset").addEventListener("click", reset);
  pause.addEventListener("click", togglePause);
  auto.addEventListener("click", toggleAuto);
  shape.addEventListener("change", () => { model.kind = Number(shape.value); say("已选择"+config.shapes[model.kind]+"，下一束烟花就会用上。"); });
  palette.addEventListener("change", () => { model.palette = Number(palette.value); say("配色已选好，放一束看看。"); });
  reduced.addEventListener("change", changeMotion);
  media.addEventListener("change", event => { reduced.checked = event.matches; changeMotion(); });
  canvas.addEventListener("keydown", event => {
    if (event.altKey || event.ctrlKey || event.metaKey || event.repeat) return;
    const actions = {Enter: () => fire(), " ": togglePause, f: () => fire(0,135,true), a: toggleAuto, r: reset};
    const action = actions[event.key.length === 1 ? event.key.toLowerCase() : event.key];
    if (action) { event.preventDefault(); action(); }
  });

  // Observe all pointers so a second finger outside the canvas cancels a tap.
  document.addEventListener("pointerdown", event => {
    pointers.add(event.pointerId);
    if (pointers.size > 1) candidate = null;
  }, true);
  canvas.addEventListener("pointerdown", event => {
    if (event.button !== 0 || !event.isPrimary || pointers.size !== 1) return;
    candidate = {id: event.pointerId, x: event.clientX, y: event.clientY, time: event.timeStamp};
  });
  document.addEventListener("pointermove", event => {
    if (candidate && candidate.id === event.pointerId
      && Math.hypot(event.clientX-candidate.x, event.clientY-candidate.y) > 12) candidate = null;
  }, {passive: true});
  canvas.addEventListener("pointerleave", () => { candidate = null; });
  document.addEventListener("pointerup", event => {
    const tap = candidate;
    const single = pointers.size === 1;
    pointers.delete(event.pointerId);
    candidate = null;
    if (!tap || tap.id !== event.pointerId || !single || event.timeStamp-tap.time > 700
      || Math.hypot(event.clientX-tap.x,event.clientY-tap.y) > 12) return;
    const bounds = canvas.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) return;
    const x = (event.clientX-bounds.left)/bounds.width*config.view[0]-config.view[0]/2;
    const y = config.view[1]/2-(event.clientY-bounds.top)/bounds.height*config.view[1];
    if (y < -148) { say("点一下城市上方的夜空，就能发射烟花。"); return; }
    canvas.focus({preventScroll: true});
    fire(Math.max(-420,Math.min(420,x)),Math.max(-50,Math.min(205,y)));
  });
  document.addEventListener("pointercancel", event => { pointers.delete(event.pointerId); candidate = null; });
  function clearInput() { candidate = null; pointers.clear(); }
  window.addEventListener("blur", clearInput);
  document.addEventListener("visibilitychange", () => {
    clearInput();
    if (document.hidden) stopFrame(); else schedule();
  });
  window.addEventListener("pagehide", () => { pageActive = false; clearInput(); stopFrame(); });
  window.addEventListener("pageshow", () => { pageActive = true; schedule(); });
  window.addEventListener("resize", () => { clearInput(); view.resize(); view.draw(model); });

  canvas.hidden = false;
  view.resize();
  view.draw(model);
  fallback.hidden = true;
  controls.disabled = false;
  updateControls();
  say(reduced.checked ? "减少动态已开启：点击直接呈现静态烟花。" : "夜空已就绪，点击放出第一束烟花。");
}

start().catch(() => {
  canvas.hidden = true;
  fallback.hidden = false;
  controls.disabled = true;
  status.textContent = "在线试玩暂不可用，请刷新重试；也可以欣赏预览或下载 Python 作品。";
});
