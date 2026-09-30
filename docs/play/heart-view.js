import { heartPoint } from "./heart-model.js";

// Geometry and the three small colour tables are reused by every frame and by
// PNG exports. No trails, particle sprites or frame-sized images accumulate.
const palettes = new WeakMap();
const contour = Array.from({length: 161}, (_, index) => heartPoint(index * Math.PI * 2 / 160));
const orbit = angle => [310 * Math.cos(angle), -28 + 60 * Math.sin(angle) + 68.2 * Math.cos(angle)];
const orbitBack = Array.from({length: 71}, (_, index) => orbit(index * Math.PI / 70));
const orbitFront = Array.from({length: 71}, (_, index) => orbit(Math.PI + index * Math.PI / 70));

function mix(a, b, amount) {
  const channel = index => Math.round(parseInt(a.slice(index, index + 2), 16) * (1 - amount)
    + parseInt(b.slice(index, index + 2), 16) * amount);
  return `rgb(${channel(1)},${channel(3)},${channel(5)})`;
}

function colorsFor(config) {
  if (!palettes.has(config)) {
    palettes.set(config, config.themes.map(([, core, light, accent]) => ({
      core, light,
      dust: Array.from({length: 32}, (_, index) => mix("#28172F", core, index / 31)),
      lightDust: Array.from({length: 32}, (_, index) => mix(core, light, index / 31)),
      stars: Array.from({length: 32}, (_, index) => mix("#101329", accent, index / 31)),
      atmosphere: Array.from({length: 17}, (_, index) => mix("#100E22", core, .008 + index * .0022)),
      constellation: mix("#232438", accent, .55),
      orbitBack: mix("#14122A", accent, .34),
      orbitFront: mix("#15122A", accent, .37),
      glowOuter: mix("#26162E", core, .10),
      glowInner: mix("#26162E", core, .24),
      orbitGlow: [3, 2, 1].map(layer => mix("#15112A", accent, (1 - layer / 4) ** 2 * .65)),
    })));
  }
  return palettes.get(config);
}

function circle(context, x, y, radius, color) {
  context.fillStyle = color;
  context.beginPath(); context.arc(x, y, radius, 0, Math.PI * 2); context.fill();
}

function line(context, points, color, width = 1) {
  context.strokeStyle = color; context.lineWidth = width;
  context.beginPath();
  points.forEach(([x, y], index) => index ? context.lineTo(x, y) : context.moveTo(x, y));
  context.stroke();
}

function text(context, y, value, color, size) {
  context.save(); context.scale(1, -1);
  context.fillStyle = color;
  context.font = `${size}px "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif`;
  context.textAlign = "center"; context.textBaseline = "middle";
  context.fillText(value, 0, -y); context.restore();
}

export function drawHeart(canvas, model, config) {
  const context = canvas.getContext("2d", {alpha: false});
  if (!context) throw new Error("Canvas 2D unavailable");
  const [width, height] = config.view;
  const scale = canvas.width / width;
  const colors = colorsFor(config)[model.theme];
  const pose = model.pose();
  context.setTransform(scale, 0, 0, -scale, canvas.width / 2, canvas.height / 2);
  context.globalAlpha = 1; context.globalCompositeOperation = "source-over";
  context.lineCap = "round"; context.lineJoin = "round";

  const gradient = context.createLinearGradient(0, height / 2, 0, -height / 2);
  gradient.addColorStop(0, "#070D20"); gradient.addColorStop(1, "#180C23");
  context.fillStyle = gradient; context.fillRect(-width / 2, -height / 2, width, height);

  context.save(); context.translate(0, pose.groupY); context.scale(pose.groupScale, pose.groupScale);
  for (let index = 0; index < 17; index++) {
    const radius = 298 - index * 11;
    context.fillStyle = colors.atmosphere[index];
    context.beginPath(); context.ellipse(0, 5, radius, radius * .75, 0, 0, Math.PI * 2); context.fill();
  }
  context.restore();

  for (const star of model.stars) {
    const twinkle = .55 + .3 * Math.sin(model.time * .7 + star.phase);
    circle(context, star.x, star.y, star.radius, colors.stars[Math.round(twinkle * 31)]);
  }
  for (const side of [-1, 1]) {
    const dots = [[281, 132], [305, 81], [268, 20], [291, -49]].map(([x, y]) => [x * side, y]);
    line(context, dots, "#28243E");
    for (const [x, y] of dots) {
      circle(context, x, y, 2.3, colors.constellation);
      context.strokeStyle = "#302B46"; context.lineWidth = 1;
      context.beginPath(); context.arc(x, y, 6, 0, Math.PI * 2); context.stroke();
    }
  }

  // The entire heart and its orbit pull back together while the particles
  // scatter, retaining their proportions and keeping them inside the poster.
  context.save(); context.translate(0, pose.groupY); context.scale(pose.groupScale, pose.groupScale);
  line(context, orbitBack, colors.orbitBack);
  for (const [factor, tint, width] of [[1.025, .12, 4.5], [1, .30, 1.1], [.965, .09, 1]]) {
    const size = 13 * pose.pulse * factor;
    line(context, contour.map(([x, y]) => [x * size, y * size + 26]),
      mix("#23162F", colors.core, tint * (1 - pose.spread * .85)), width);
  }
  const pointScale = 1 + pose.beat * .12;
  model.particles.forEach((particle, index) => {
    const x = (particle.x * pose.turnCos + particle.depth * 17 * pose.turnSin) * pose.pulse
      + particle.scatterX * pose.spread;
    const y = particle.y * pose.pulse + 26
      + (pose.waveSin * particle.phaseCos + pose.waveCos * particle.phaseSin) * 1.4
      + particle.scatterY * pose.spread;
    let color;
    if (particle.depth > .55) {
      color = colors.lightDust[Math.min(31, Math.round((particle.depth - .55) * 50))];
    } else {
      const brightness = .48 + .28 * particle.depth
        + .14 * (pose.lightSin * particle.phaseCos + pose.lightCos * particle.phaseSin);
      color = colors.dust[Math.max(0, Math.min(31, Math.round(brightness * 31)))];
    }
    if (index % 59 === 0) {
      circle(context, x, y, particle.radius * 3, colors.glowOuter);
      circle(context, x, y, particle.radius * 1.7, colors.glowInner);
    }
    circle(context, x, y, particle.radius * pointScale, color);
  });
  line(context, orbitFront, colors.orbitFront);
  for (const shift of [0, Math.PI]) {
    const [x, y] = orbit(model.time * .27 + shift);
    colors.orbitGlow.forEach((color, index) => circle(context, x, y, 8 * (3 - index) / 3, color));
    circle(context, x, y, 2, colors.light);
  }
  context.restore();

  text(context, 278, "怦然心动", colors.light, 29);
  text(context, 234, "EVERY BEAT, A LITTLE UNIVERSE", "#77657F", 10);
  text(context, -266, "把一瞬的心动，写成漫长的星光。", "#A27D9F", 14);
  text(context, -299, "26  /  PARTICLE HEART", "#665974", 9);
}

export function resizeHeart(canvas) {
  const size = Math.max(1, Math.round(canvas.getBoundingClientRect().width
    * Math.min(2, window.devicePixelRatio || 1)));
  if (canvas.width !== size || canvas.height !== size) canvas.width = canvas.height = size;
}
