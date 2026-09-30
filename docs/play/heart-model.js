/** Bounded, deterministic particle geometry; no DOM or animation scheduling. */
const finite = value => typeof value === "number" && Number.isFinite(value);
const invalid = label => new TypeError(`Invalid ${label}`);
const tau = Math.PI * 2;

export function heartPoint(angle) {
  if (!finite(angle)) throw invalid("heart angle");
  angle %= tau;
  return [16 * Math.sin(angle) ** 3, 13 * Math.cos(angle) - 5 * Math.cos(2*angle)
    - 2 * Math.cos(3*angle) - Math.cos(4*angle)];
}
export function heartbeat(time) {
  if (!finite(time) || time < 0) throw invalid("heartbeat time");
  const phase = (time % 1.55) / 1.55;
  return Math.exp(-(((phase-.18)/.06)**2)) + .58*Math.exp(-(((phase-.34)/.09)**2));
}
export function spreadAt(age) {
  if (age === null) return 0;
  if (!finite(age) || age < 0) throw invalid("spread age");
  return Math.sin(Math.PI*Math.min(age,3.6)/3.6)**2;
}

function checkedConfig(config) {
  const expected = {version:1,default_count:680,max_step:.05,burst_duration:3.6,rate_min:.45,rate_max:1.8};
  if (!config || Object.entries(expected).some(([key,value]) => config[key] !== value)
      || !Array.isArray(config.view) || config.view.length !== 2 || !config.view.every(value => value === 640)
      || !Array.isArray(config.densities) || config.densities.length !== 3
      || config.densities.some((value,index) => value !== [420,680,1000][index])
      || !Array.isArray(config.themes) || config.themes.length !== 3
      || !config.themes.every(theme => Array.isArray(theme) && theme.length === 4
        && typeof theme[0] === "string" && theme[0].length > 0 && theme[0].length <= 40
        && theme.slice(1).every(color => typeof color === "string" && /^#[0-9a-f]{6}$/i.test(color)))) {
    throw invalid("heart config");
  }
  return Object.freeze({...expected,view:Object.freeze([...config.view]),
    densities:Object.freeze([...config.densities]),
    themes:Object.freeze(config.themes.map(theme => Object.freeze([...theme])))});
}

function randomStream(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6D2B79F5) >>> 0;
    let value = state;
    value = Math.imul(value ^ value >>> 15, value | 1);
    value ^= value + Math.imul(value ^ value >>> 7, value | 61);
    return ((value ^ value >>> 14) >>> 0) / 4294967296;
  };
}

export class HeartModel {
  constructor(config, {seed=260}={}) {
    this.config = checkedConfig(config);
    if (!Number.isInteger(seed) || seed < 0 || seed > 0xffffffff) throw invalid("heart seed");
    this.seed = seed;
    this.theme = 0; this.rate = 1; this.count = this.config.default_count;
    this._makeParticles();
    const random = randomStream(seed ^ 0x5F3759DF);
    this.stars = Array.from({length:78},() => ({x:(random()*2-1)*302,
      y:(random()*2-1)*298,radius:.6+random()*1.1,phase:random()*tau}));
    this.reset();
  }
  _makeParticles() {
    const random = randomStream(this.seed);
    this.particles = Array.from({length:this.count},() => {
      const angle = random()*tau, fraction = 1-random()**2.3*.60;
      const [x,y] = heartPoint(angle);
      const depth = random()*2-1, phase = random()*tau;
      const radius = .85+random()*1.30, velocity = 40+random()*140;
      return {x:x*13*fraction,y:y*13*fraction,depth,radius,phase,velocity,angle,
        phaseSin:Math.sin(phase),phaseCos:Math.cos(phase),
        scatterX:Math.sin(angle)*velocity,scatterY:Math.cos(angle)*velocity*.65};
    }).sort((a,b) => a.depth-b.depth);
  }
  setTheme(theme) {
    if (!Number.isInteger(theme) || theme < 0 || theme >= this.config.themes.length) return false;
    this.theme = theme; return true;
  }
  setRate(rate) {
    if (!finite(rate) || rate < this.config.rate_min || rate > this.config.rate_max) return false;
    this.rate = rate; return true;
  }
  setCount(count) {
    if (!this.config.densities.includes(count)) return false;
    if (count !== this.count) { this.count = count; this._makeParticles(); }
    return true;
  }
  reset() { this.time = this.beatTime = 0; this.burstAge = null; }
  burst(staticMode=false) {
    if (typeof staticMode !== "boolean") throw invalid("burst mode");
    this.burstAge = staticMode ? (this.burstAge === null ? this.config.burst_duration/2 : null) : 0;
  }
  step(dt) {
    if (!finite(dt) || dt < 0) throw invalid("time step");
    if (dt === 0) return;
    dt = Math.min(dt,this.config.max_step);
    this.time += dt; this.beatTime += dt*this.rate;
    if (this.burstAge !== null) {
      this.burstAge += dt;
      // Allow the sub-nanosecond sum error of repeated finite time steps.
      if (this.burstAge >= this.config.burst_duration-1e-10) this.burstAge = null;
    }
  }
  pose() {
    const spread = spreadAt(this.burstAge), beat = heartbeat(this.beatTime);
    const rotation = .08*Math.sin(this.time*.38);
    return {spread,beat,pulse:1+beat*.055,turnCos:Math.cos(rotation),turnSin:Math.sin(rotation),
      waveSin:Math.sin(this.time*.75),waveCos:Math.cos(this.time*.75),
      lightSin:Math.sin(this.time*1.1),lightCos:Math.cos(this.time*1.1),
      groupScale:.9*(1-.16*spread),groupY:-4};
  }
}
