import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {HeartModel, heartPoint, heartbeat, spreadAt} from '../../docs/play/heart-model.js';

const config = JSON.parse(await readFile(new URL('../../docs/play/heart-config.json', import.meta.url)));
const state = model => JSON.stringify(model);
const near = (actual, expected) => assert.ok(Math.abs(actual-expected)<1e-9, `${actual} != ${expected}`);

test('heart shape and both motion curves match Python fixtures and cardinal coordinates', () => {
  for (const [angle, point] of [[0,[0,5]],[Math.PI/2,[16,4]],[Math.PI,[0,-17]]])
    heartPoint(angle).forEach((value, index) => near(value,point[index]));
  for (const sample of config.fixtures.heart)
    heartPoint(sample.angle).forEach((value,index) => near(value,sample.result[index]));
  for (const sample of config.fixtures.beat) near(heartbeat(sample.time),sample.result);
  for (const sample of config.fixtures.spread) near(spreadAt(sample.age),sample.result);
  near(spreadAt(null),0); near(spreadAt(1.8),1);
  assert.ok(heartbeat(.279)>heartbeat(.527));
});

test('a seed gives stable sorted geometry and density never shifts the background stars', () => {
  const model = new HeartModel(config), twin = new HeartModel(config);
  assert.deepEqual(model.particles,twin.particles);
  assert.deepEqual(model.stars,twin.stars);
  assert.notDeepEqual(model.particles,new HeartModel(config,{seed:261}).particles);
  const original = structuredClone(model.particles), stars = model.stars;
  for (const count of [420,1000,680]) {
    assert.equal(model.setCount(count),true);
    assert.equal(model.particles.length,count);
    assert.equal(model.stars,stars);
    let depth = -Infinity;
    for (const particle of model.particles) {
      assert.ok(Object.values(particle).every(Number.isFinite));
      assert.ok(particle.depth>=depth && particle.depth<=1); depth = particle.depth;
      assert.ok(Math.abs(particle.x)<=208 && Math.abs(particle.y)<=221);
      assert.ok(particle.radius>=.85 && particle.radius<=2.15);
    }
  }
  assert.deepEqual(model.particles,original);
  assert.equal(stars.length,78);
  assert.ok(stars.every(s => Math.abs(s.x)<=302 && Math.abs(s.y)<=298));
});

test('time steps are bounded, rate affects only heartbeat, and bad inputs are atomic', () => {
  const model = new HeartModel(config);
  model.setRate(1.8); model.step(50);
  near(model.time,.05); near(model.beatTime,.09);
  const before = state(model);
  for (const value of [-1,NaN,Infinity,'1',null,undefined]) {
    assert.throws(() => model.step(value),/invalid/i);
    assert.equal(state(model),before);
  }
  model.step(0); assert.equal(state(model),before);
});

test('a burst returns to the heart in 3.6 seconds and repeat clicks reuse the fixed particle pool', () => {
  const model = new HeartModel(config), particles = model.particles, stars = model.stars;
  for (let i=0;i<100;i++) { model.burst(); model.step(.02); }
  assert.equal(model.particles,particles); assert.equal(model.stars,stars);
  model.burst(); near(model.burstAge,0);
  for (let i=0;i<36;i++) model.step(.05);
  near(model.pose().spread,1);
  for (let i=0;i<36;i++) model.step(.05);
  assert.equal(model.burstAge,null); near(model.pose().spread,0);
});

test('static scatter toggles two still compositions without changing time or particles', () => {
  const model = new HeartModel(config), particles = model.particles;
  model.burst(true); near(model.burstAge,1.8); near(model.pose().spread,1);
  model.burst(true); assert.equal(model.burstAge,null); near(model.pose().spread,0);
  near(model.time,0); near(model.beatTime,0); assert.equal(model.particles,particles);
});

test('parameters reject malformed values and reset preserves settings and stable geometry', () => {
  const model = new HeartModel(config);
  for (const value of [0,1,2]) assert.equal(model.setTheme(value),true);
  for (const value of [.45,1.8,1.2]) assert.equal(model.setRate(value),true);
  model.setCount(1000); model.burst(); model.step(.05);
  for (const action of [() => model.setTheme(3),() => model.setTheme(-1),() => model.setTheme('1'),
    () => model.setTheme(.5),() => model.setRate(.44),() => model.setRate(1.81),
    () => model.setRate(NaN),() => model.setRate('1'),() => model.setCount(999),
    () => model.setCount('680'),() => model.setCount(Infinity)]) {
    const before = state(model); assert.equal(action(),false); assert.equal(state(model),before);
  }
  const particles = model.particles, stars = model.stars;
  model.reset();
  assert.equal(model.time,0); assert.equal(model.beatTime,0); assert.equal(model.burstAge,null);
  assert.equal(model.theme,2); assert.equal(model.rate,1.2); assert.equal(model.count,1000);
  assert.equal(model.particles,particles); assert.equal(model.stars,stars);
  model.setCount(1000); assert.equal(model.particles,particles);
});

test('pose is a pure finite snapshot of the square desktop composition', () => {
  const model = new HeartModel(config);
  for (let i=0;i<100;i++) {
    if (i===20) model.burst();
    model.step(.05);
    const before = state(model), pose = model.pose();
    assert.ok(Object.values(pose).every(Number.isFinite));
    assert.ok(pose.spread>=0 && pose.spread<=1);
    near(pose.groupScale,.9*(1-.16*pose.spread)); near(pose.groupY,-4);
    near(pose.turnCos**2+pose.turnSin**2,1);
    assert.deepEqual(model.pose(),pose); assert.equal(state(model),before);
    for (const particle of model.particles) {
      const x = ((particle.x*pose.turnCos+particle.depth*17*pose.turnSin)*pose.pulse
        +particle.scatterX*pose.spread)*pose.groupScale;
      const y = (particle.y*pose.pulse+26+(pose.waveSin*particle.phaseCos+pose.waveCos*particle.phaseSin)*1.4
        +particle.scatterY*pose.spread)*pose.groupScale+pose.groupY;
      assert.ok(Math.abs(x)+particle.radius*3*pose.groupScale<320);
      assert.ok(Math.abs(y)+particle.radius*3*pose.groupScale<320);
    }
  }
});

test('malformed config and seed cannot create unbounded or corrupt geometry', () => {
  for (const edit of [c => {c.version=2;},c => {c.view=[640,0];},c => {c.themes[0][1]='bad';},
    c => {c.themes=[];},c => {c.densities=[420,680,1e6];},c => {c.default_count=600;},
    c => {c.max_step=1;},c => {c.burst_duration=NaN;},c => {c.rate_min=0;},c => {c.rate_max=Infinity;}]) {
    const broken = structuredClone(config); edit(broken);
    assert.throws(() => new HeartModel(broken),/invalid/i);
  }
  for (const seed of [-1,2**32,NaN,.5,'260',null]) assert.throws(() => new HeartModel(config,{seed}),/invalid/i);
  const input = structuredClone(config), model = new HeartModel(input);
  input.max_step=100; input.densities.push(1e6); input.themes[0][1]='broken';
  model.step(100); near(model.time,.05);
  assert.equal(model.setCount(1e6),false);
  assert.match(model.config.themes[0][1],/^#[0-9a-f]{6}$/i);
});

test('numerical helpers reject malformed arguments before producing invalid coordinates', () => {
  for (const value of [NaN,Infinity,-Infinity,'0',undefined]) {
    assert.throws(() => heartPoint(value),/invalid/i);
    assert.throws(() => heartbeat(value),/invalid/i);
    assert.throws(() => spreadAt(value),/invalid/i);
  }
  assert.throws(() => heartbeat(-1),/invalid/i);
  assert.throws(() => spreadAt(-1),/invalid/i);
});
