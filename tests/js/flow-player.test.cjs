const test = require('node:test');
const assert = require('node:assert/strict');
const { FlowPlayer, initialize } = require('../../src/mkdocs_flow_player/assets/flow-player.js');

function element() {
  const classes = new Set();
  return {
    dataset: {}, isConnected: true, textContent: '', listeners: {},
    classList: { add: (...v) => v.forEach(x => classes.add(x)), remove: (...v) => v.forEach(x => classes.delete(x)), contains: x => classes.has(x) },
    classes, setAttribute(k, v) { this[k] = String(v); },
    addEventListener(type, handler) { this.listeners[type] = handler; },
    dispatch(type) { this.listeners[type]?.({ target: this }); },
    appendChild(child) { if (child) child.parentNode = this; return child; },
    remove() { this.isConnected = false; },
  };
}

function fixture(steps = [{ node: 'A', state: 'error' }, { node: 'A', state: 'success' }], extra = {}) {
  const root = element();
  const controls = ['reset', 'previous', 'next', 'play'].map(action => Object.assign(element(), { dataset: { action } }));
  // Mermaid >= 11 prefixes every element id with the render id passed to mermaid.render().
  const nodes = ['A', 'B'].map((id, i) => Object.assign(element(), { id: `flow-player-1-flowchart-${id}-${i}` }));
  // g.edgePaths inside the diagram root; the traveller layer is appended to the root
  // (last child) so it paints above edge labels and nodes.
  const diagramRoot = { children: [], appendChild(c) { this.children.push(c); }, querySelector: () => null };
  const path = { id: 'flow-player-1-L_A_B_0', parentNode: { appendChild() {}, parentNode: diagramRoot }, getTotalLength: () => 100, getPointAtLength: x => ({ x, y: 0 }) };
  const svg = { querySelectorAll: selector => selector === 'g.node' ? nodes : [path] };
  const fields = new Map();
  for (const name of ['scenario', 'mermaid', 'canvas', 'counter', 'step-title', 'description', 'payload']) fields.set(`.flow-player__${name}`, element());
  if (extra.select) fields.set('.flow-player__scenario-select', Object.assign(element(), { value: '0', tagName: 'SELECT' }));
  fields.get('.flow-player__scenario').textContent = JSON.stringify(extra.scenarios ?? { id: 'test', settings: { step_duration: 1000 }, steps });
  fields.get('.flow-player__mermaid').textContent = JSON.stringify('flowchart LR\nA --> B');
  root.querySelector = selector => selector === 'svg' ? svg : fields.get(selector);
  root.querySelectorAll = () => controls;
  let time = 0, id = 0;
  const pending = new Map();
  const clock = {
    now: () => time,
    request: cb => { pending.set(++id, cb); return id; },
    cancel: id => pending.delete(id),
    advance(ms) { time += ms; const callbacks = [...pending.values()]; pending.clear(); callbacks.forEach(cb => cb(time)); },
  };
  global.window = { matchMedia: () => ({ matches: false }), mermaid: { initialize() {}, async render() { return { svg: '<svg></svg>' }; } } };
  global.document = { createElementNS: () => element() };
  const player = new FlowPlayer(root, clock);
  player.svg = svg;
  player.ready = true;
  player.render(false);
  return { root, player, nodes, fields, controls, clock, pending, diagramRoot };
}

test('node and edge lookup tolerates the Mermaid >= 11 render-id prefix', () => {
  const { player } = fixture([{ node: 'A' }, { edge: { from: 'A', to: 'B' } }]);
  assert.equal(player.findNode('A').id, 'flow-player-1-flowchart-A-0');
  assert.equal(player.findNode('B').id, 'flow-player-1-flowchart-B-1');
  assert.equal(player.findNode('C'), undefined);
  assert.equal(player.findEdge('A', 'B').id, 'flow-player-1-L_A_B_0');
  assert.equal(player.findEdge('A', 'C'), undefined);
});

test('node and edge lookup tolerates alternate Mermaid id shapes', () => {
  const { player } = fixture([{ node: 'A' }, { edge: { from: 'A', to: 'B' } }]);
  const nodes = [
    Object.assign(element(), { id: 'flowchart-A-0' }),
    Object.assign(element(), { id: 'render:flowchart-B-1' }),
    Object.assign(element(), { id: 'legacy-node', dataset: { id: 'C' } }),
  ];
  const paths = [
    Object.assign(element(), { id: 'L_A_B_0' }),
    Object.assign(element(), { id: 'render_L_B_C_0' }),
    Object.assign(element(), { id: 'legacy-edge', dataset: { id: 'L_C_A' } }),
  ];
  player.svg = { querySelectorAll: selector => selector === 'g.node' ? nodes : paths };

  assert.equal(player.findNode('A').id, 'flowchart-A-0');
  assert.equal(player.findNode('B').id, 'render:flowchart-B-1');
  assert.equal(player.findNode('C').id, 'legacy-node');
  assert.equal(player.findEdge('A', 'B').id, 'L_A_B_0');
  assert.equal(player.findEdge('B', 'C').id, 'render_L_B_C_0');
  assert.equal(player.findEdge('C', 'A').id, 'legacy-edge');
});

test('edge lookup can select parallel edges by nth', () => {
  const { player } = fixture([{ edge: { from: 'A', to: 'B', nth: 2 } }]);
  const paths = [
    Object.assign(element(), { id: 'flow-player-1-L_A_B_0' }),
    Object.assign(element(), { id: 'flow-player-1-L_A_B_1' }),
  ];
  player.svg = { querySelectorAll: selector => selector === 'g.node' ? [] : paths };

  assert.equal(player.findEdge('A', 'B', 1).id, 'flow-player-1-L_A_B_0');
  assert.equal(player.findEdge('A', 'B', 2).id, 'flow-player-1-L_A_B_1');
  assert.equal(player.findEdge('A', 'B', 3), undefined);
});

test('edge label is used as the title fallback', () => {
  const { player, fields } = fixture([{ edge: { from: 'A', to: 'B', nth: 1, label: 'retry' } }]);
  player.next();
  assert.equal(fields.get('.flow-player__step-title').textContent, 'retry');
});

test('scenario select switches scenarios and resets playback', () => {
  const scenarios = [
    { id: 'one', settings: { step_duration: 1000 }, steps: [{ node: 'A', title: 'First' }] },
    { id: 'two', settings: { step_duration: 2500 }, steps: [{ node: 'B', title: 'Second' }] },
  ];
  const { root, player, fields } = fixture([], { scenarios, select: true });
  player.next();
  assert.equal(player.currentStep, 0);
  fields.get('.flow-player__scenario-select').value = '1';
  fields.get('.flow-player__scenario-select').dispatch('change');

  assert.equal(player.scenario.id, 'two');
  assert.equal(player.duration, 2500);
  assert.equal(player.currentStep, -1);
  assert.equal(root.dataset.flowId, 'two');
  assert.equal(fields.get('.flow-player__counter').textContent, 'Ready');
});

test('keyboard events inside the scenario select are left to the browser', () => {
  const { player } = fixture([{ node: 'A' }]);
  let prevented = false;
  player.handleKey({ key: 'ArrowRight', target: { tagName: 'SELECT' }, preventDefault() { prevented = true; } });
  assert.equal(player.currentStep, -1);
  assert.equal(prevented, false);
});

test('latest node state wins; Previous and Reset replay deterministically', () => {
  const { player, nodes } = fixture();
  player.next();
  assert.deepEqual([...nodes[0].classes], ['flow-state-error']);
  player.next();
  assert.deepEqual([...nodes[0].classes], ['flow-state-success']);
  player.previous();
  assert.deepEqual([...nodes[0].classes], ['flow-state-error']);
  player.reset();
  assert.equal(nodes[0].classes.size, 0);
  assert.equal(player.currentStep, -1);
});

test('keyboard: arrows step, Home resets, End jumps to the last step', () => {
  const { player } = fixture([{ node: 'A' }, { node: 'A', state: 'success' }, { node: 'B' }]);
  const press = (key, extra = {}) => player.handleKey({ key, preventDefault() {}, ...extra });
  press('ArrowRight');
  assert.equal(player.currentStep, 0);
  press('ArrowDown');
  assert.equal(player.currentStep, 1);
  press('ArrowLeft');
  assert.equal(player.currentStep, 0);
  press('End');
  assert.equal(player.currentStep, 2);
  press('ArrowRight');
  assert.equal(player.currentStep, 2);
  press('Home');
  assert.equal(player.currentStep, -1);
});

test('keyboard: ignored before ready and when a modifier is held', () => {
  const { player } = fixture([{ node: 'A' }, { node: 'B' }]);
  player.ready = false;
  player.handleKey({ key: 'ArrowRight', preventDefault() {} });
  assert.equal(player.currentStep, -1);
  player.ready = true;
  let prevented = false;
  player.handleKey({ key: 'ArrowRight', metaKey: true, preventDefault() { prevented = true; } });
  assert.equal(player.currentStep, -1);
  assert.equal(prevented, false);
});

test('the traveller renders in an overlay layer so labels never occlude it', () => {
  const { player, diagramRoot } = fixture([{ edge: { from: 'A', to: 'B' } }, { node: 'B' }]);
  player.play();
  const layer = diagramRoot.children.at(-1); // appended last => painted above labels/nodes
  assert.equal(layer.class, 'flow-player__marker-layer');
  assert.equal(player.marker.parentNode, layer);
});

test('Pause freezes marker and Resume uses same step and remaining time', () => {
  const { player, clock, pending } = fixture([{ edge: { from: 'A', to: 'B' } }, { node: 'B' }]);
  player.play();
  clock.advance(250);
  assert.equal(player.marker.cx, '25');
  player.pause();
  assert.equal(pending.size, 0);
  clock.advance(5000);
  assert.equal(player.marker.cx, '25');
  assert.equal(player.elapsed, 250);
  player.play();
  assert.equal(player.currentStep, 0);
  clock.advance(250);
  assert.equal(player.marker.cx, '50');
  clock.advance(500);
  assert.equal(player.currentStep, 1);
  assert.equal(player.marker, null);
  clock.advance(1000);
  assert.equal(player.playing, false);
  assert.equal(pending.size, 0);
  player.play();
  assert.equal(player.currentStep, 0);
});

test('manual navigation cancels animation and pending playback', () => {
  const { player, clock, pending } = fixture([{ node: 'A' }, { edge: { from: 'A', to: 'B' } }]);
  player.play();
  clock.advance(1000);
  const marker = player.marker;
  player.previous();
  assert.equal(marker.isConnected, false);
  assert.equal(player.marker, null);
  assert.equal(pending.size, 0);
  clock.advance(5000);
  assert.equal(player.currentStep, 0);
});

test('false, zero and null payloads are displayed', () => {
  const { player, fields } = fixture([false, 0, null].map(payload => ({ node: 'A', payload })));
  for (const value of ['false', '0', 'null']) {
    player.next();
    assert.equal(fields.get('.flow-player__payload').hidden, false);
    assert.equal(fields.get('.flow-player__payload').textContent, value);
  }
});

test('invalid placeholders, malformed JSON and render errors do not block valid players', async () => {
  const warning = fixture().root;
  warning.classList.add('flow-player--invalid');
  const malformed = fixture();
  malformed.fields.get('.flow-player__scenario').textContent = '{broken';
  const badRender = fixture();
  badRender.fields.get('.flow-player__mermaid').textContent = JSON.stringify('bad');
  const valid = fixture();
  window.mermaid.render = async (_, source) => {
    if (source === 'bad') throw new Error('renderer failed');
    return { svg: '<svg></svg>' };
  };
  await initialize({ querySelectorAll: () => [warning, malformed.root, badRender.root, valid.root] });
  assert.equal(warning.dataset.initialized, undefined);
  assert.equal(malformed.root.classList.contains('flow-player--invalid'), true);
  assert.equal(badRender.root.classList.contains('flow-player--invalid'), true);
  assert.equal(valid.root.classList.contains('flow-player--invalid'), false);
  assert.equal(valid.controls.find(b => b.dataset.action === 'next').disabled, false);
  await initialize({ querySelectorAll: () => [valid.root] });
});

test('missing renderer disables controls without throwing past initializer', async () => {
  const { root, controls } = fixture();
  window.mermaid = undefined;
  await initialize({ querySelectorAll: () => [root] });
  assert.equal(root.classList.contains('flow-player--invalid'), true);
  assert.ok(controls.every(button => button.disabled));
});

test('detaching a player stops its playback clock', () => {
  const { player, root, clock, pending } = fixture();
  player.play();
  root.isConnected = false;
  clock.advance(250);
  assert.equal(player.playing, false);
  assert.equal(pending.size, 0);
});
