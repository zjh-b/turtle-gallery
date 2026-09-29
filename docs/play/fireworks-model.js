/** Deterministic, DOM-free adaptation of artwork 01. Python exports the constants. */
const finite = value => typeof value === 'number' && Number.isFinite(value);
const invalid = label => new TypeError(`Invalid ${label}`);
const clamp = (value, low, high) => Math.max(low, Math.min(high, value));

function checkedConfig(config) {
  if (!config || config.version !== 1 || !Array.isArray(config.view) ||
      config.view.length !== 2 || !config.view.every(n => finite(n) && n > 0 && n <= 4096) ||
      !Array.isArray(config.shapes) || config.shapes.length !== 4 ||
      !config.shapes.every(name => typeof name === 'string' && name.length > 0) ||
      !Array.isArray(config.palettes) || config.palettes.length !== 4 ||
      !config.palettes.every(pair => Array.isArray(pair) && pair.length === 2 &&
        pair.every(color => typeof color === 'string' && /^#[0-9a-f]{6}$/i.test(color)))) {
    throw invalid('fireworks config');
  }
  const p = config.physics;
  const positive = ['particle_count', 'drag', 'gravity', 'willow_gravity', 'speed_min',
    'speed_max', 'life_min', 'life_max', 'rocket_duration', 'bloom_life',
    'particle_cap', 'rocket_cap', 'bloom_cap', 'max_step'];
  if (!p || positive.some(key => !finite(p[key]) || p[key] <= 0 || p[key] > 10000) ||
      ['particle_count', 'particle_cap', 'rocket_cap', 'bloom_cap'].some(key => !Number.isInteger(p[key])) ||
      p.particle_count > p.particle_cap || p.particle_cap > 600 || p.rocket_cap > 8 ||
      p.bloom_cap > 8 || p.max_step > .05 || p.speed_min > p.speed_max || p.life_min > p.life_max) {
    throw invalid('fireworks physics');
  }
  // Own the values so callers cannot change simulation rules after validation.
  return Object.freeze({version: 1, view: Object.freeze([...config.view]),
    shapes: Object.freeze([...config.shapes]),
    palettes: Object.freeze(config.palettes.map(pair => Object.freeze([...pair]))),
    physics: Object.freeze({...p})});
}

function velocity(kind, index, speed, config) {
  const angle = index * Math.PI * 2 / config.physics.particle_count;
  let vx = Math.cos(angle) * speed;
  let vy = Math.sin(angle) * speed;
  if (kind === 1) {
    vx *= 1.2;
    vy *= .65;
    if (index % 3 === 0) { vx *= .45; vy *= .45; }
  } else if (kind === 2) {
    vx = 9 * 16 * Math.sin(angle) ** 3;
    vy = 9 * (13 * Math.cos(angle) - 5 * Math.cos(2 * angle) -
      2 * Math.cos(3 * angle) - Math.cos(4 * angle));
  } else if (kind === 3) {
    vy = Math.abs(vy) * 1.2;
  } else if (index % 4 === 0) {
    vx *= .55;
    vy *= .55;
  }
  return [vx, vy];
}

export function location(particle, age, config) {
  if (!finite(age) || !particle || !finite(particle.x) || !finite(particle.y) ||
      !finite(particle.vx) || !finite(particle.vy) || !finite(particle.gravity) ||
      !finite(config?.physics?.drag) || config.physics.drag <= 0) throw invalid('particle location');
  age = Math.max(0, age);
  const drag = config.physics.drag;
  const travel = (1 - Math.exp(-drag * age)) / drag;
  return [particle.x + particle.vx * travel,
    particle.y + particle.vy * travel - particle.gravity * age * age / 2];
}

export class FireworksModel {
  constructor(config, {seed = 22} = {}) {
    this.config = checkedConfig(config);
    if (!Number.isInteger(seed) || seed < 0 || seed > 0xffffffff) throw invalid('seed');
    this._seed = seed;
    this.reset();
  }

  _random() {
    // Mulberry32: reproducible in JavaScript; not Python's random sequence.
    this._randomState = (this._randomState + 0x6D2B79F5) >>> 0;
    let value = this._randomState;
    value = Math.imul(value ^ value >>> 15, value | 1);
    value ^= value + Math.imul(value ^ value >>> 7, value | 61);
    return ((value ^ value >>> 14) >>> 0) / 4294967296;
  }

  _uniform(low, high) { return low + this._random() * (high - low); }

  _checkTarget(x, y, kind) {
    if (!finite(x) || !finite(y) || !Number.isInteger(kind) || kind < 0 || kind >= 4) {
      throw invalid('firework target or kind');
    }
  }

  _colors(kind) {
    if (!Number.isInteger(this.palette) || this.palette < -1 || this.palette >= 4) throw invalid('palette');
    return [...this.config.palettes[this.palette === -1 ? kind : this.palette]];
  }

  reset() {
    this._randomState = this._seed;
    this.time = 0;
    this._timer = .7;
    this.kind = 0;
    this.palette = -1;
    this.auto = false;
    this.clear();
    for (const [x, y, age, kind] of [[-210, 90, .72, 0], [95, 145, .55, 1], [295, 30, .48, 2]]) {
      this.burst(x, y, kind, age);
    }
  }

  clear() {
    this.particles = [];
    this.rockets = [];
    this.blooms = [];
  }

  launch(x, y, kind = this.kind) {
    this._checkTarget(x, y, kind);
    const colors = this._colors(kind);
    x = clamp(x, -420, 420);
    y = clamp(y, -50, 205);
    this.rockets.push({x: x * .7, target: [x, y], age: 0, kind, colors});
    this.rockets = this.rockets.slice(-this.config.physics.rocket_cap);
  }

  burst(x, y, kind = this.kind, age = 0) {
    this._checkTarget(x, y, kind);
    if (!finite(age) || age < 0) throw invalid('burst age');
    this._burst(x, y, kind, age, this._colors(kind));
  }

  _burst(x, y, kind, age, colors) {
    const p = this.config.physics;
    this.blooms.push({x, y, age, color: colors[0]});
    for (let index = 0; index < p.particle_count; index++) {
      const speed = this._uniform(p.speed_min, p.speed_max);
      const [vx, vy] = velocity(kind, index, speed, this.config);
      this.particles.push({x, y, vx, vy, age, life: this._uniform(p.life_min, p.life_max),
        color: colors[index % 2], gravity: kind === 3 ? p.willow_gravity : p.gravity,
        phase: index * Math.PI * 2 / p.particle_count});
    }
    this.particles = this.particles.slice(-p.particle_cap);
    this.blooms = this.blooms.slice(-p.bloom_cap);
  }

  finale() {
    // Validate the selected palette before adding any of the five rockets.
    this._colors(0);
    for (let index = 0; index < 5; index++) {
      this.launch(-320 + index * 160, 95 + (index % 2) * 70, index % 4);
    }
  }

  step(dt) {
    if (!finite(dt) || dt < 0) throw invalid('time step');
    if (dt === 0) return;
    if (typeof this.auto !== 'boolean') throw invalid('automatic playback');
    if (this.auto) this._colors(0);
    const p = this.config.physics;
    dt = Math.min(dt, p.max_step);
    this.time += dt;
    this._timer -= dt;
    if (this.auto && this._timer <= 0) {
      this.launch(this._uniform(-350, 350), this._uniform(55, 190), Math.floor(this._random() * 4));
      this._timer = this._uniform(.75, 1.1);
    }
    for (const rocket of this.rockets) {
      rocket.age += dt;
      if (rocket.age >= p.rocket_duration) this._burst(...rocket.target, rocket.kind, 0, rocket.colors);
    }
    this.rockets = this.rockets.filter(rocket => rocket.age < p.rocket_duration);
    for (const particle of this.particles) particle.age += dt;
    for (const bloom of this.blooms) bloom.age += dt;
    this.particles = this.particles.filter(particle => particle.age < particle.life);
    this.blooms = this.blooms.filter(bloom => bloom.age < p.bloom_life);
  }
}
