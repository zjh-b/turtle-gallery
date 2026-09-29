import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {FireworksModel, location} from '../../docs/play/fireworks-model.js';

const config = JSON.parse(await readFile(new URL('../../docs/play/fireworks-config.json', import.meta.url)));
const state = model => JSON.stringify(model);
const close = (actual, expected) => expected.forEach((value, index) =>
  assert.ok(Math.abs(actual[index] - value) < 1e-9, `${actual[index]} != ${value}`));

test('trajectories match Python fixtures including negative ages', () => {
  for (const sample of config.fixtures.locations) {
    close(location(sample.particle, sample.age, config), sample.result);
  }
});

test('every flower shape matches exported Python velocity fixtures', () => {
  for (const sample of config.fixtures.velocities) {
    const custom = structuredClone(config);
    custom.physics.speed_min = custom.physics.speed_max = sample.speed;
    const model = new FireworksModel(custom);
    model.clear();
    model.burst(0, 0, sample.kind);
    const particle = model.particles[sample.index];
    close([particle.vx, particle.vy], sample.result);
  }
});

test('reset restores the same three static blooms and disables automatic playback', () => {
  const model = new FireworksModel(config, {seed: 22});
  const initial = state(model);
  assert.equal(model.auto, false);
  assert.equal(model.blooms.length, 3);
  assert.equal(model.particles.length, 252);
  assert.equal(model.rockets.length, 0);
  model.auto = true;
  model.palette = 2;
  model.kind = 3;
  model.finale();
  model.step(.05);
  model.reset();
  assert.equal(state(model), initial);
});

test('zero time step leaves every field unchanged even when auto timer is due', () => {
  const model = new FireworksModel(config);
  model.auto = true;
  const before = state(model);
  model.step(0);
  assert.equal(state(model), before);
});

test('time step clamps background delays and particles expire without auto playback', () => {
  const delayed = new FireworksModel(config);
  const normal = new FireworksModel(config);
  delayed.step(1000);
  normal.step(.05);
  assert.equal(state(delayed), state(normal));
  for (let i = 0; i < 100; i++) normal.step(.05);
  assert.equal(normal.particles.length, 0);
  assert.equal(normal.blooms.length, 0);
  assert.equal(normal.rockets.length, 0);
});

test('rapid launches and repeated bursts remain bounded', () => {
  const model = new FireworksModel(config);
  for (let i = 0; i < 100; i++) model.finale();
  assert.equal(model.rockets.length, 8);
  for (let i = 0; i < 100; i++) model.burst(i, 100, i % 4);
  assert.equal(model.particles.length, 600);
  assert.equal(model.blooms.length, 8);
  for (let i = 0; i < 20; i++) model.step(.05);
  assert.ok(model.particles.length <= 600);
  assert.ok(model.blooms.length <= 8);
  assert.equal(model.rockets.length, 0);
});

test('rockets clamp their target and keep launch-time colors until they bloom', () => {
  const model = new FireworksModel(config);
  model.clear();
  model.palette = 2;
  model.launch(5000, -5000, 0);
  assert.deepEqual(model.rockets[0].target, [420, -50]);
  assert.deepEqual(model.rockets[0].colors, config.palettes[2]);
  model.palette = 3;
  for (let i = 0; i < 18; i++) model.step(.05);
  assert.equal(model.rockets.length, 0);
  assert.equal(model.blooms[0].color, config.palettes[2][0]);
  assert.deepEqual([...new Set(model.particles.map(p => p.color))], config.palettes[2]);
});

test('same seeds and inputs reproduce bursts while different seeds vary them', () => {
  const first = new FireworksModel(config, {seed: 12});
  const second = new FireworksModel(config, {seed: 12});
  const other = new FireworksModel(config, {seed: 13});
  for (const model of [first, second, other]) {
    model.auto = true;
    model.finale();
    for (let i = 0; i < 40; i++) model.step(.05);
  }
  assert.equal(state(first), state(second));
  assert.notDeepEqual(first.particles, other.particles);
});

test('clear removes active objects without changing user settings', () => {
  const model = new FireworksModel(config);
  model.kind = 3;
  model.palette = 2;
  model.finale();
  model.clear();
  assert.deepEqual([model.particles.length, model.rockets.length, model.blooms.length], [0, 0, 0]);
  assert.equal(model.kind, 3);
  assert.equal(model.palette, 2);
});

test('invalid action values are rejected without changing model state', () => {
  const model = new FireworksModel(config);
  const invalid = [() => model.step(-1), () => model.step(NaN), () => model.step('1'),
    () => model.launch(Infinity, 0), () => model.launch(0, 0, 4),
    () => model.burst(0, NaN), () => model.burst(0, 0, 1.5),
    () => model.burst(0, 0, 1, -1), () => model.burst(0, 0, 1, Infinity)];
  for (const action of invalid) {
    const before = state(model);
    assert.throws(action, /invalid/i);
    assert.equal(state(model), before);
  }
});

test('invalid fetched config is rejected before creating particles', () => {
  for (const edit of [c => {c.version = 2;}, c => {c.palettes[0][0] = 'bad';},
    c => {c.physics.drag = 0;}, c => {c.physics.particle_cap = 600000;},
    c => {c.physics.life_min = c.physics.life_max + 1;}, c => {c.view = [0, 580];}]) {
    const broken = structuredClone(config);
    edit(broken);
    assert.throws(() => new FireworksModel(broken), /invalid/i);
  }
});
