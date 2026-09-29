import { KaleidoscopeModel } from "./kaleidoscope-model.js";
import { drawKaleidoscope, resizeKaleidoscope } from "./kaleidoscope-view.js";

const canvas=document.querySelector("#kaleidoscope-canvas");
const fallback=document.querySelector("#kaleidoscope-fallback");
const controls=document.querySelector("#play-controls");
const status=document.querySelector("#play-status");
const mode=document.querySelector("#draw-mode");
const count=document.querySelector("#symmetry");
const palette=document.querySelector("#palette");
const undo=document.querySelector("#undo");
const save=document.querySelector("#save-png");
const hint=document.querySelector("#draw-hint");

async function start() {
  const request=new AbortController(), timeout=setTimeout(()=>request.abort(),10000);
  let config;
  try {
    const response=await fetch("kaleidoscope-config.json",{signal:request.signal});
    if (!response.ok) throw new Error("Configuration unavailable");
    config=await response.json();
  } finally { clearTimeout(timeout); }
  const model=new KaleidoscopeModel(config);
  if (!canvas.getContext("2d")) throw new Error("Canvas unavailable");
  let drawing=false, active=null, frame=null, saving=false;
  const pointers=new Set();

  function say(text) { status.textContent=text; }
  function redraw() {
    if(frame!==null) cancelAnimationFrame(frame);
    frame=null;
    drawKaleidoscope(canvas,model,config);
    hint.hidden=Boolean(model.strokes.length || model.current?.length);
    undo.disabled=model.isExample || !model.strokes.length;
    document.querySelector("#stroke-count").textContent=model.isExample?"灵感示例":`${model.strokes.length} / ${config.max_strokes} 笔`;
  }
  function schedule() {
    if(frame===null && !document.hidden) frame=requestAnimationFrame(redraw);
  }
  function release() {
    const id=active; active=null;
    if(id!==null && canvas.hasPointerCapture(id)) canvas.releasePointerCapture(id);
  }
  function cancel() { model.cancel(); release(); redraw(); }
  function point(event) {
    const bounds=canvas.getBoundingClientRect();
    return [(event.clientX-bounds.left)/bounds.width*config.view[0]-config.view[0]/2,
      config.view[1]/2-(event.clientY-bounds.top)/bounds.height*config.view[1]];
  }
  function setDrawing(value) {
    cancel(); drawing=value;
    if(drawing && model.isExample) model.clear();
    canvas.classList.toggle("is-drawing",drawing);
    mode.setAttribute("aria-pressed",String(drawing));
    mode.textContent=drawing?"结束手绘 · 恢复滚动":"开始手绘 ↗";
    redraw();
    say(drawing?"画笔已准备好，在圆内拖动画一笔。":"已结束手绘，可以滑动页面或保存图案。");
  }
  mode.addEventListener("click",()=>setDrawing(!drawing));
  count.addEventListener("change",()=>{ cancel(); model.setCount(Number(count.value)); redraw(); say(`已变为 ${model.count} 份对称，已有笔迹也会重新排布。`); });
  palette.addEventListener("change",()=>{ cancel(); model.setPalette(Number(palette.value)); redraw(); say("整幅图案已换上新的颜色。"); });
  undo.addEventListener("click",()=>{ cancel(); model.undo(); redraw(); say("已撤销上一整笔。"); });
  document.querySelector("#clear").addEventListener("click",()=>{ cancel(); model.clear(); redraw(); say("画布已清空，开始新的创作吧。"); });
  document.querySelector("#example").addEventListener("click",()=>{ setDrawing(false); model.example(); count.value=String(model.count); palette.value=String(model.palette); redraw(); say("已换回示例，试试调整对称份数与配色。"); });

  document.addEventListener("pointerdown",event=>{
    pointers.add(event.pointerId);
    if(pointers.size>1 && active!==null) { cancel(); say("多点触摸已取消当前一笔，之前的笔迹保留。"); }
  },true);
  canvas.addEventListener("pointerdown",event=>{
    if(!drawing || event.button!==0 || !event.isPrimary || pointers.size!==1 || document.hidden) return;
    if(!model.begin(...point(event))) {
      if(model.limitReached) say("画布已达到上限，请先撤销或清空，再继续画。");
      return;
    }
    active=event.pointerId;
    canvas.setPointerCapture(active);
    canvas.focus({preventScroll:true});
    schedule();
  });
  canvas.addEventListener("pointermove",event=>{
    if(active!==event.pointerId) return;
    const [x,y]=point(event);
    if(Math.hypot(x,y)>config.radius) { cancel(); say("画笔离开圆形边界，已取消当前一笔。"); return; }
    const changed=model.move(x,y);
    if(model.limitReached) say("这一笔已达到点数上限，松手完成；可另起一笔或撤销。");
    if(changed) schedule();
  });
  document.addEventListener("pointerup",event=>{
    pointers.delete(event.pointerId);
    if(active!==event.pointerId) return;
    const [x,y]=point(event);
    if(Math.hypot(x,y)>config.radius) { cancel(); return; }
    model.move(x,y);
    const limited=model.limitReached;
    const completed=model.end();
    release(); redraw();
    say(limited?"已保留这一笔；达到上限后请撤销或清空再继续。":completed?"这一笔已留下，可以再画一笔，或换个对称份数。":"拖动一小段距离，就能画出线条。");
  });
  document.addEventListener("pointercancel",event=>{
    pointers.delete(event.pointerId);
    if(active===event.pointerId) { cancel(); say("已取消尚未完成的一笔。"); }
  });
  canvas.addEventListener("lostpointercapture",event=>{ if(active===event.pointerId) cancel(); });
  function interrupt() { pointers.clear(); cancel(); }
  window.addEventListener("blur",interrupt);
  window.addEventListener("pagehide",interrupt);
  document.addEventListener("visibilitychange",()=>{ if(document.hidden) interrupt(); });
  window.addEventListener("resize",()=>{ interrupt(); resizeKaleidoscope(canvas); redraw(); });

  save.addEventListener("click",()=>{
    if(saving) return;
    cancel();
    const picture=document.createElement("canvas");
    picture.width=picture.height=1080;
    saving=true; save.disabled=true;
    const finish=()=>{ saving=false; save.disabled=false; };
    try {
      drawKaleidoscope(picture,model,config);
      picture.toBlob(blob=>{
        try {
          if(!blob) throw new Error("PNG unavailable");
          const url=URL.createObjectURL(blob), link=document.createElement("a");
          link.href=url; link.download="turtle-gallery-kaleidoscope-1080.png";
          document.body.append(link); link.click(); link.remove();
          setTimeout(()=>URL.revokeObjectURL(url),1000);
          say("1080 × 1080 PNG 已交给浏览器下载，请查看下载列表。");
        } catch(_) { say("下载暂未成功，请重试或换一个浏览器。"); }
        finally { finish(); }
      },"image/png");
    } catch(_) { finish(); say("图片生成失败，请重试。"); }
  });
  canvas.hidden=false; resizeKaleidoscope(canvas); redraw();
  fallback.hidden=true; controls.disabled=false;
  say("示例已就绪；调整纹样，或点击开始手绘。");
}
start().catch(()=>{
  canvas.hidden=true; fallback.hidden=false; hint.hidden=true; controls.disabled=true;
  status.textContent="在线创作暂不可用，请刷新重试；也可欣赏预览或下载 Python 作品。";
});
