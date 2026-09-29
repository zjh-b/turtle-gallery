import { mirrorPoints } from "./kaleidoscope-model.js";

// One bounded backing image per destination. Completed model strokes are
// immutable; only the current stroke grows while the pointer moves.
const backgrounds = new WeakMap();

function mix(a,b,t) {
  const channel = index => Math.round(parseInt(a.slice(index,index+2),16)*(1-t)+parseInt(b.slice(index,index+2),16)*t);
  return `rgb(${channel(1)},${channel(3)},${channel(5)})`;
}

function transform(context, canvas, config) {
  const scale = canvas.width / config.view[0];
  context.setTransform(scale,0,0,-scale,canvas.width/2,canvas.height/2);
}

function background(context) {
  context.globalAlpha=1; context.lineCap="butt"; context.lineJoin="miter";
  const gradient = context.createLinearGradient(0,280,0,-280);
  gradient.addColorStop(0,"#0d1125"); gradient.addColorStop(1,"#181329");
  context.fillStyle = gradient;
  context.fillRect(-280,-280,560,560);
  function circle(radius, fill, stroke) {
    context.beginPath(); context.arc(0,0,radius,0,Math.PI*2);
    if (fill) { context.fillStyle=fill; context.fill(); }
    if (stroke) { context.strokeStyle=stroke; context.lineWidth=1; context.stroke(); }
  }
  circle(256,"#11152a","#393650");
  circle(249,null,"#5a4d67");
  for (let i=0;i<80;i++) {
    const angle=i*Math.PI*2/80, outer=i%5===0?258:255;
    context.strokeStyle=i%5===0?"#8b768c":"#454059";
    context.beginPath(); context.moveTo(Math.cos(angle)*253,Math.sin(angle)*253);
    context.lineTo(Math.cos(angle)*outer,Math.sin(angle)*outer); context.stroke();
  }
}

function strokes(context, paths, firstIndex, model, config) {
  context.save();
  context.beginPath(); context.arc(0,0,config.radius,0,Math.PI*2); context.clip();
  paths.forEach((stroke,offset) => {
    const index=firstIndex+offset;
    const phase=.48+index*.117;
    const tone=(1+Math.sin(phase*Math.PI*2))/2;
    const color=model.palette===1?mix("#5cb7c4","#e0f9d6",tone):model.palette===2?mix("#d47765","#ffe4a1",tone):`hsl(${phase*360%360} 65% 77%)`;
    context.lineWidth=1.5; context.lineCap="round"; context.lineJoin="round";
    for (const points of mirrorPoints(stroke,model.count)) {
      context.beginPath();
      points.forEach(([x,y],i) => i?context.lineTo(x,y):context.moveTo(x,y));
      if (model.isExample && points.length>20) {
        context.globalAlpha=.035; context.fillStyle=color; context.fill();
      }
      context.globalAlpha=.8; context.strokeStyle=color; context.stroke();
    }
  });
  context.restore(); context.globalAlpha=1;
}

export function drawKaleidoscope(canvas, model, config) {
  const context = canvas.getContext("2d", {alpha: false});
  if (!context) throw new Error("Canvas unavailable");
  let cached=backgrounds.get(canvas);
  if (!cached) {
    cached={canvas:canvas.ownerDocument.createElement("canvas"),paths:[]};
    backgrounds.set(canvas,cached);
  }
  const stale=cached.width!==canvas.width || cached.height!==canvas.height
    || cached.model!==model || cached.count!==model.count || cached.palette!==model.palette
    || cached.example!==model.isExample || cached.radius!==config.radius || cached.view!==config.view[0]
    || cached.paths.length!==model.strokes.length
    || cached.paths.some((path,index)=>path!==model.strokes[index]);
  if (stale) {
    if(cached.canvas.width!==canvas.width || cached.canvas.height!==canvas.height) {
      cached.canvas.width=canvas.width; cached.canvas.height=canvas.height;
    }
    const base=cached.canvas.getContext("2d",{alpha:false});
    if(!base) throw new Error("Canvas unavailable");
    transform(base,cached.canvas,config);
    background(base);
    strokes(base,model.strokes,0,model,config);
    Object.assign(cached,{width:canvas.width,height:canvas.height,model,count:model.count,
      palette:model.palette,example:model.isExample,radius:config.radius,view:config.view[0],
      paths:[...model.strokes]});
  }
  context.setTransform(1,0,0,1,0,0); context.globalAlpha=1;
  context.drawImage(cached.canvas,0,0);
  transform(context,canvas,config);
  if(model.current) strokes(context,[model.current],model.strokes.length,model,config);
  // Keep the center above both saved and unfinished ink, as in a full redraw.
  context.beginPath(); context.arc(0,0,3,0,Math.PI*2);
  context.fillStyle="#e4ccdb"; context.fill();
}

export function resizeKaleidoscope(canvas) {
  const size=Math.max(1,Math.round(canvas.getBoundingClientRect().width*Math.min(2,window.devicePixelRatio||1)));
  if (canvas.width!==size || canvas.height!==size) canvas.width=canvas.height=size;
}
