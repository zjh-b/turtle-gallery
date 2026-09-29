import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {KaleidoscopeModel, mirrorPoints} from '../../docs/play/kaleidoscope-model.js';

const config = JSON.parse(await readFile(new URL('../../docs/play/kaleidoscope-config.json', import.meta.url)));
const state = model => JSON.stringify(model);
const empty = () => { const model = new KaleidoscopeModel(config); model.clear(); return model; };
const draw = (model, points) => {
  assert.equal(model.begin(...points[0]), true);
  for (const point of points.slice(1)) assert.equal(model.move(...point), true);
  assert.equal(model.end(), true);
};
const longStroke = Array.from({length: 400}, (_, index) => [index % 2 ? 10 : 0, 20]);

test('rotation and reflection match independent cardinal coordinates and Python fixtures', () => {
  const cardinal = mirrorPoints([[10, 20]], 4);
  const expected = [[10, -20], [10, 20], [20, 10], [-20, 10],
    [-10, 20], [-10, -20], [-20, -10], [20, -10]];
  cardinal.forEach((stroke, i) => stroke[0].forEach((value, axis) =>
    assert.ok(Math.abs(value - expected[i][axis]) < 1e-9)));
  for (const sample of config.fixtures) {
    const actual = mirrorPoints(sample.points, sample.count);
    assert.equal(actual.length, sample.count * 2);
    actual.forEach((stroke, i) => stroke.forEach((point, j) => point.forEach((value, axis) =>
      assert.ok(Math.abs(value - sample.result[i][j][axis]) < 1e-9))));
  }
});

test('initial static example is deterministic, drawable, and within the input budgets', () => {
  const model = new KaleidoscopeModel(config);
  assert.equal(model.count, 10);
  assert.equal(model.palette, 0);
  assert.equal(model.isExample, true);
  assert.equal(model.current, null);
  assert.ok(model.strokes.length >= 4 && model.strokes.length <= config.max_strokes);
  assert.ok(model.strokes.flat().length <= config.max_points);
  for (const stroke of model.strokes) {
    assert.ok(stroke.length >= 2 && stroke.length <= config.max_stroke_points);
    assert.ok(stroke.every(([x, y]) => Number.isFinite(x) && Number.isFinite(y) && Math.hypot(x, y) <= config.radius));
  }
  const initial = state(model);
  model.clear();
  model.example();
  assert.equal(state(model), initial);
});

test('invalid starts preserve the example and valid start replaces it', () => {
  const model = new KaleidoscopeModel(config);
  for (const point of [[NaN, 0], [0, Infinity], ['2', 0], [247, 0], [246, 1]]) {
    const before = state(model);
    assert.equal(model.begin(...point), false);
    assert.equal(state(model), before);
  }
  assert.equal(model.begin(246, 0), true);
  assert.equal(model.isExample, false);
  assert.deepEqual(model.strokes, []);
  assert.deepEqual(model.current, [[246, 0]]);
});

test('each completed gesture is one undoable stroke and a tap creates no stroke', () => {
  const model = empty();
  assert.equal(model.begin(0, 0), true);
  assert.equal(model.end(), false);
  assert.equal(model.strokes.length, 0);
  const first = [[0, 0], [10, 15], [30, 20]];
  draw(model, first);
  draw(model, [[-15, 0], [-30, 10]]);
  assert.deepEqual(model.strokes[0], first);
  assert.equal(model.undo(), true);
  assert.deepEqual(model.strokes, [first]);
  assert.equal(model.current, null);
  assert.equal(model.undo(), true);
  assert.equal(model.undo(), false);
});

test('tiny pointer jitter is ignored until it travels far enough from the last accepted point', () => {
  const model = empty();
  model.begin(0, 0);
  assert.equal(model.move(.5, .5), false);
  assert.equal(model.move(1, 0), false);
  assert.equal(model.move(1.5, 0), true);
  assert.deepEqual(model.current, [[0, 0], [1.5, 0]]);
  assert.equal(model.limitReached, false);
});

test('cancel and outside moves drop only the incomplete stroke and never bridge back', () => {
  const model = empty();
  const finished = [[0, 0], [5, 10]];
  draw(model, finished);
  for (const badPoint of [[247, 0], [NaN, 0], [0, Infinity], ['4', 0]]) {
    model.begin(30, 40);
    model.move(35, 45);
    assert.equal(model.move(...badPoint), false);
    assert.equal(model.current, null);
    assert.equal(model.move(40, 50), false);
    assert.equal(model.end(), false);
    assert.deepEqual(model.strokes, [finished]);
  }
  model.begin(30, 40);
  model.move(35, 45);
  model.cancel();
  assert.equal(model.current, null);
  assert.deepEqual(model.strokes, [finished]);
});

test('second begin cannot overwrite an unfinished gesture', () => {
  const model = empty();
  model.begin(0, 0);
  model.move(20, 20);
  const before = state(model);
  assert.equal(model.begin(30, 30), false);
  assert.equal(state(model), before);
});

test('count and palette settings preserve point data and reject malformed values atomically', () => {
  const model = empty();
  draw(model, [[0, 0], [10, 20]]);
  const strokes = structuredClone(model.strokes);
  for (const count of [3, 16, 10]) assert.equal(model.setCount(count), true);
  for (const palette of [0, 1, 2]) assert.equal(model.setPalette(palette), true);
  assert.deepEqual(model.strokes, strokes);
  for (const action of [() => model.setCount(2), () => model.setCount(17),
    () => model.setCount(4.5), () => model.setCount('10'), () => model.setCount(NaN),
    () => model.setPalette(-1), () => model.setPalette(3), () => model.setPalette('1'),
    () => model.setPalette(.5), () => model.setPalette(Infinity)]) {
    const before = state(model);
    assert.equal(action(), false);
    assert.equal(state(model), before);
  }
  model.clear();
  assert.equal(model.count, 10);
  assert.equal(model.palette, 2);
  assert.equal(model.isExample, false);
});

test('stroke limit rejects new work without evicting earlier drawings and undo restores capacity', () => {
  const model = empty();
  for (let i = 0; i < 60; i++) draw(model, [[i, 0], [i, 10]]);
  const before = structuredClone(model.strokes);
  assert.equal(model.begin(0, 20), false);
  assert.equal(model.limitReached, true);
  assert.equal(model.current, null);
  assert.deepEqual(model.strokes, before);
  assert.equal(model.undo(), true);
  assert.equal(model.limitReached, false);
  draw(model, [[0, 30], [10, 40]]);
  assert.equal(model.strokes.length, 60);
  assert.deepEqual(model.strokes[0], [[0, 0], [0, 10]]);
});

test('per-stroke point limit retains accepted points and allows committing them', () => {
  const model = empty();
  model.begin(...longStroke[0]);
  for (const point of longStroke.slice(1)) assert.equal(model.move(...point), true);
  assert.equal(model.current.length, 400);
  assert.equal(model.move(30, 40), false);
  assert.equal(model.limitReached, true);
  assert.deepEqual(model.current, longStroke);
  assert.equal(model.end(), true);
  assert.deepEqual(model.strokes, [longStroke]);
  assert.equal(model.begin(20, 30), true);
  assert.equal(model.limitReached, false);
});

test('total point cap includes the unfinished gesture and preserves all completed work', () => {
  const model = empty();
  for (let i = 0; i < 5; i++) draw(model, longStroke);
  draw(model, longStroke.slice(0, 399));
  const before = structuredClone(model.strokes);
  assert.equal(model.begin(0, 0), true);
  assert.equal(model.move(20, 20), false);
  assert.equal(model.limitReached, true);
  assert.deepEqual(model.current, [[0, 0]]);
  model.cancel();
  assert.deepEqual(model.strokes, before);
  model.undo();
  draw(model, longStroke);
  assert.equal(model.strokes.flat().length, 2400);
  assert.equal(model.begin(0, 0), false);
  assert.equal(model.limitReached, true);
  assert.equal(model.current, null);
  model.clear();
  assert.equal(model.limitReached, false);
  assert.equal(model.strokes.length, 0);
});

test('malformed fetched config is rejected and later caller mutations cannot change budgets', () => {
  for (const edit of [c => { c.version = 2; }, c => { c.view = [0, 560]; },
    c => { c.radius = Infinity; }, c => { c.radius = 600; },
    c => { c.min_count = 2; }, c => { c.max_count = 100; },
    c => { c.max_strokes = 100000; }, c => { c.max_points = 2401; },
    c => { c.max_stroke_points = 401; }]) {
    const broken = structuredClone(config);
    edit(broken);
    assert.throws(() => new KaleidoscopeModel(broken), /invalid/i);
  }
  const input = structuredClone(config);
  const model = new KaleidoscopeModel(input);
  input.radius = 5000;
  input.max_points = 1000000;
  assert.equal(model.begin(300, 0), false);
  assert.equal(model.config.max_points, 2400);
});

test('mirror formula rejects invalid count and coordinates before producing corrupt geometry', () => {
  for (const args of [[[[0, 0]], 0], [[[0, 0]], 17], [[[0, 0]], 3.5],
    [[[NaN, 0]], 3], [[[1, Infinity]], 3], [[['3', 0]], 3], [[[2]], 3]]) {
    assert.throws(() => mirrorPoints(...args), /invalid/i);
  }
});
