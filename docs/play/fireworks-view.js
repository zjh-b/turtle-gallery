import { location } from "./fireworks-model.js";

function scenery() {
  let seed = 22;
  const random = () => { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed / 4294967296; };
  const stars = Array.from({length: 85}, () => [-490 + random()*980, -85 + random()*345, .6 + random()*.9]);
  const buildings = [];
  for (let x = -520; x < 530; x += 27) buildings.push([x, 18 + random()*55, 17 + random()*16, random()]);
  return {stars, buildings};
}

export class FireworksView {
  constructor(canvas, config) {
    this.canvas = canvas;
    this.config = config;
    this.context = canvas.getContext("2d", {alpha: false});
    if (!this.context) throw new Error("Canvas 2D unavailable");
    this.backdrop = document.createElement("canvas");
    this.scenery = scenery();
    this.scale = 1;
  }

  resize() {
    const bounds = this.canvas.getBoundingClientRect();
    const ratio = Math.min(2, window.devicePixelRatio || 1);
    const width = Math.max(1, Math.round(bounds.width * ratio));
    const height = Math.max(1, Math.round(width * this.config.view[1] / this.config.view[0]));
    if (width === this.canvas.width && height === this.canvas.height && this.backdrop.width === width) return;
    this.canvas.width = this.backdrop.width = width;
    this.canvas.height = this.backdrop.height = height;
    this.scale = width / this.config.view[0];
    const context = this.backdrop.getContext("2d", {alpha: false});
    this.transform(context);
    this.background(context);
  }

  transform(context) {
    context.setTransform(this.scale, 0, 0, -this.scale, this.canvas.width/2, this.canvas.height/2);
  }

  circle(context, x, y, radius, color, alpha = 1) {
    if (radius <= 0 || alpha <= 0) return;
    context.globalAlpha = alpha;
    context.fillStyle = color;
    context.beginPath();
    context.arc(x, y, radius, 0, Math.PI*2);
    context.fill();
    context.globalAlpha = 1;
  }

  line(context, points, color, width = 1, alpha = 1) {
    context.globalAlpha = Math.max(0, Math.min(1, alpha));
    context.strokeStyle = color;
    context.lineWidth = width;
    context.lineCap = "round";
    context.beginPath();
    points.forEach(([x,y], index) => index ? context.lineTo(x,y) : context.moveTo(x,y));
    context.stroke();
    context.globalAlpha = 1;
  }

  glow(context, x, y, radius, color, alpha = .3) {
    for (let layer = 4; layer >= 1; layer--) this.circle(context, x, y, radius*layer/4, color, alpha/5);
  }

  background(context) {
    const [width, height] = this.config.view;
    const gradient = context.createLinearGradient(0, height/2, 0, -height/2);
    gradient.addColorStop(0, "#070e24");
    gradient.addColorStop(1, "#24304e");
    context.fillStyle = gradient;
    context.fillRect(-width/2, -height/2, width, height);
    for (const [x,y,r] of this.scenery.stars) this.circle(context, x, y, r, "#bacce7", .4 + r*.2);
    this.glow(context, 355, 198, 48, "#7186b3", .3);
    this.circle(context, 355, 198, 21, "#f6e7c4");
    this.circle(context, 365, 204, 20, "#0e172d");
    for (const [x, height, width, lit] of this.scenery.buildings) {
      context.fillStyle = "#10182c";
      context.fillRect(x, -153, width, height);
      if (lit < .3) continue;
      for (let y = 8; y < height-4; y += 13) {
        context.fillStyle = "#ad997d";
        context.fillRect(x+5, -153+y, 3, 3);
        if (lit > .6) { context.fillStyle = "#607b9d"; context.fillRect(x+14, -153+y, 3, 3); }
      }
    }
    context.fillStyle = "#0d1c32";
    context.fillRect(-width/2, -height/2, width, height/2-153);
    this.line(context, [[-width/2,-152],[width/2,-152]], "#48617a");
    for (let index = 0; index < 30; index++) {
      const y = -161-index*4.8, x = Math.sin(index*2.1)*440;
      this.line(context, [[x,y],[x+35+index%4*14,y]], "#22354d");
    }
  }

  draw(model) {
    const context = this.context;
    context.setTransform(1,0,0,1,0,0);
    context.globalAlpha = 1;
    context.drawImage(this.backdrop, 0, 0);
    this.transform(context);
    for (const bloom of model.blooms) {
      const fade = Math.max(0, 1 - bloom.age/this.config.physics.bloom_life);
      for (let index = 0; index < 15; index++) {
        const y = -161-index*8, width = (12+index*2.8)*fade;
        const x = bloom.x + Math.sin(index*1.8 + model.time*2)*(4+index);
        this.line(context, [[x-width,y],[x+width,y]], bloom.color, 2, fade*(.35-index*.015));
      }
      if (bloom.age < .3) this.glow(context, bloom.x, bloom.y, 38*(1-bloom.age/.3), bloom.color, .45);
    }
    for (const rocket of model.rockets) {
      const t = Math.min(1, rocket.age/this.config.physics.rocket_duration);
      const x = rocket.x+(rocket.target[0]-rocket.x)*t;
      const y = -150+(rocket.target[1]+150)*(1-(1-t)**1.5);
      this.line(context, [[x-5,y-42],[x-2,y-17],[x,y]], "#786256", 3);
      this.line(context, [[x-2,y-18],[x,y]], "#ffdfa0", 2);
      this.circle(context, x, y, 2, "#fff5db");
    }
    context.save();
    context.beginPath();
    context.rect(-this.config.view[0]/2, -148, this.config.view[0], this.config.view[1]/2+148);
    context.clip();
    for (const particle of model.particles) {
      const [x,y] = location(particle, particle.age, this.config);
      if (y <= -148) continue;
      const fade = Math.min(1, Math.max(0, (particle.life-particle.age)/.8));
      for (const segment of [3,2,1]) {
        this.line(context, [location(particle, particle.age-.065*segment, this.config),
          location(particle, particle.age-.065*(segment-1), this.config)], particle.color,
          segment === 1 ? 2 : 1, fade*(1-segment*.22));
      }
      this.circle(context, x, y, 3.5, particle.color, fade*.09);
      this.circle(context, x, y, 1.5, "#fff4df", fade);
    }
    context.restore();
  }
}
