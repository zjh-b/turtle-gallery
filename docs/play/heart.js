import { HeartModel } from "./heart-model.js";
import { drawHeart, resizeHeart } from "./heart-view.js";

const canvas = document.querySelector("#heart-canvas");
const fallback = document.querySelector("#heart-fallback");
const controls = document.querySelector("#play-controls");
const status = document.querySelector("#play-status");
const theme = document.querySelector("#theme");
const rate = document.querySelector("#rate");
const density = document.querySelector("#density");
const pause = document.querySelector("#pause");
const burstButton = document.querySelector("#burst");
const reduced = document.querySelector("#reduced-motion");
const save = document.querySelector("#save-png");

async function start() {
  const request = new AbortController(), timeout = setTimeout(() => request.abort(),10000);
  let config;
  try {
    const response = await fetch("heart-config.json",{signal:request.signal});
    if (!response.ok) throw new Error("Configuration unavailable");
    config = await response.json();
  } finally { clearTimeout(timeout); }
  const model = new HeartModel(config);
  if (!canvas.getContext("2d")) throw new Error("Canvas unavailable");
  const media = window.matchMedia("(prefers-reduced-motion: reduce)");
  let paused = true, frame = null, lastTime = null, pageActive = true, saving = false;
  let candidate = null;
  const pointers = new Set();
  reduced.checked = media.matches;

  function say(message) { status.textContent = message; }
  function draw() { drawHeart(canvas,model,config); }
  function updateControls() {
    theme.value = String(model.theme); rate.value = String(model.rate); density.value = String(model.count);
    document.querySelector("#rate-value").textContent = `× ${model.rate.toFixed(2)}`;
    rate.setAttribute("aria-valuetext",`${model.rate.toFixed(2)} 倍`);
    document.querySelector("#particle-count").textContent = `${model.count} 粒星尘`;
    pause.textContent = reduced.checked ? "静态模式" : paused ? "播放心跳" : "暂停心跳";
    pause.setAttribute("aria-pressed",String(paused));
    pause.disabled = reduced.checked;
    burstButton.textContent = reduced.checked ? "切换散开 / 聚合" : "散成星尘，再相聚 ↗";
  }
  function running() { return !paused && !reduced.checked && !document.hidden && pageActive; }
  function stop() { if (frame !== null) cancelAnimationFrame(frame); frame = lastTime = null; }
  function schedule() { if (running() && frame === null) frame = requestAnimationFrame(tick); }
  function tick(now) {
    frame = null;
    if (!running()) { lastTime = null; return; }
    // Render up to 30 times per second; keep one native frame chain.
    if (lastTime === null || now-lastTime >= 1000/30) {
      model.step(lastTime === null ? 0 : (now-lastTime)/1000);
      lastTime = now; draw();
    }
    schedule();
  }
  function scatter() {
    model.burst(reduced.checked);
    if (!reduced.checked) paused = false;
    draw(); updateControls(); schedule();
    say(reduced.checked ? "静态构图已切换，可以换色或保存这一刻。" : "星尘已散开，片刻后会重新聚成一颗心。");
  }
  function togglePause() {
    if (reduced.checked) return;
    paused = !paused;
    if (paused) stop(); else schedule();
    updateControls(); say(paused ? "心跳已暂停，这一刻为你停留。" : "心跳继续，也可以轻触让星尘散开。");
  }
  function clearInput() { candidate = null; pointers.clear(); }
  function reset() {
    stop(); clearInput(); paused = true; model.reset(); updateControls(); draw();
    say("星尘已回到初始位置；保留配色、速度和密度，画面暂停。");
  }
  function changeMotion() {
    stop(); clearInput(); paused = true; updateControls(); draw();
    say(reduced.checked ? "减少动态已开启：点击切换静态散开与聚合。" : "动态效果已恢复，主动播放或点击后开始心跳。");
  }
  theme.addEventListener("change",() => { model.setTheme(Number(theme.value)); updateControls(); draw(); say("星尘已换上新的颜色。"); });
  rate.addEventListener("input",() => { model.setRate(Number(rate.value)); updateControls(); });
  density.addEventListener("change",() => { model.setCount(Number(density.value)); updateControls(); draw(); say(`现在有 ${model.count} 粒星尘，心跳阶段保持不变。`); });
  burstButton.addEventListener("click",scatter);
  pause.addEventListener("click",togglePause);
  document.querySelector("#reset").addEventListener("click",reset);
  reduced.addEventListener("change",changeMotion);
  media.addEventListener("change",event => { reduced.checked = event.matches; changeMotion(); });
  canvas.addEventListener("keydown",event => {
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || event.repeat) return;
    const actions = {Enter:scatter," ":togglePause,r:reset,c:() => {
      model.setTheme((model.theme+1)%config.themes.length); updateControls(); draw(); say("星尘已换色。");
    }};
    const action = actions[event.key.length === 1 ? event.key.toLowerCase() : event.key];
    if (action) { event.preventDefault(); action(); }
  });

  document.addEventListener("pointerdown",event => {
    pointers.add(event.pointerId);
    if (pointers.size > 1) candidate = null;
  },true);
  canvas.addEventListener("pointerdown",event => {
    if (event.button !== 0 || !event.isPrimary || pointers.size !== 1 || document.hidden || !pageActive) return;
    candidate = {id:event.pointerId,x:event.clientX,y:event.clientY,time:event.timeStamp};
  });
  document.addEventListener("pointermove",event => {
    if (candidate && candidate.id === event.pointerId && Math.hypot(event.clientX-candidate.x,event.clientY-candidate.y)>12) candidate = null;
  },{passive:true});
  canvas.addEventListener("pointerleave",() => { candidate = null; });
  document.addEventListener("pointerup",event => {
    const tap = candidate, single = pointers.size === 1;
    pointers.delete(event.pointerId); candidate = null;
    if (!tap || tap.id !== event.pointerId || !single || event.timeStamp-tap.time>700
        || Math.hypot(event.clientX-tap.x,event.clientY-tap.y)>12 || document.hidden || !pageActive) return;
    const bounds = canvas.getBoundingClientRect();
    if (event.clientX<bounds.left || event.clientX>bounds.right || event.clientY<bounds.top || event.clientY>bounds.bottom) return;
    canvas.focus({preventScroll:true}); scatter();
  });
  document.addEventListener("pointercancel",event => { pointers.delete(event.pointerId); candidate = null; });
  window.addEventListener("blur",clearInput);
  document.addEventListener("visibilitychange",() => { clearInput(); if (document.hidden) stop(); else schedule(); });
  window.addEventListener("pagehide",() => { pageActive = false; clearInput(); stop(); });
  window.addEventListener("pageshow",() => { pageActive = true; schedule(); });
  window.addEventListener("resize",() => { clearInput(); resizeHeart(canvas); draw(); });

  save.addEventListener("click",() => {
    if (saving) return;
    const picture = document.createElement("canvas");
    picture.width = picture.height = 1080;
    saving = true; save.disabled = true;
    const finish = () => { saving = false; save.disabled = false; };
    try {
      // Freeze pixels before the asynchronous encoder; model playback keeps its state.
      drawHeart(picture,model,config);
      picture.toBlob(blob => {
        try {
          if (!blob) throw new Error("PNG unavailable");
          const url = URL.createObjectURL(blob), link = document.createElement("a");
          link.href = url; link.download = "turtle-gallery-heart-1080.png";
          document.body.append(link); link.click(); link.remove();
          setTimeout(() => URL.revokeObjectURL(url),1000);
          say("1080 × 1080 PNG 已交给浏览器下载，请查看下载列表。");
        } catch (_) { say("下载暂未成功，请重试或换一个浏览器。"); }
        finally { finish(); }
      },"image/png");
    } catch (_) { finish(); say("图片生成失败，请重试。"); }
  });
  canvas.hidden = false; resizeHeart(canvas); draw();
  fallback.hidden = true; controls.disabled = false; updateControls();
  say(reduced.checked ? "减少动态已开启：点击切换静态构图。" : "星尘已就绪；播放心跳，或轻触让它散开。");
}
start().catch(() => {
  canvas.hidden = true; fallback.hidden = false; controls.disabled = true;
  status.textContent = "在线互动暂不可用，请刷新重试；也可以欣赏预览或下载 Python 作品。";
});
