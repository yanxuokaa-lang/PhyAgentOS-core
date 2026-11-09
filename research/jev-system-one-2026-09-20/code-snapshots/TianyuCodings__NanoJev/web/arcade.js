/* Recorded-state playback only. The data file owns every action and outcome. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const DIRECTIONS = [
    ['north', 'North', '↑'], ['east', 'East', '→'],
    ['south', 'South', '↓'], ['west', 'West', '←'],
  ];
  const palette = { mint: '#7df6c8', cyan: '#48d8fa', coral: '#ff817a' };
  const ui = { data: null, example: 0, system: 0, step: 0, playing: false,
    speed: 16, tick: 0, animation: null, canvasWidth: 0, canvasHeight: 0 };
  const canvas = $('gameCanvas');
  const ctx = canvas.getContext('2d');
  const api = { ready: false, error: null, setFrame, getSnapshot, duration };
  window.nanojevArcade = api;

  const example = () => ui.data.examples[ui.example];
  const system = () => example().systems[ui.system];
  const frame = () => system().frames[ui.step];
  const lastStep = () => system().frames.length - 1;
  const isCoordinate = (value) => Array.isArray(value) && value.length === 2 && value.every(Number.isInteger);
  const sameCell = (a, b) => a && b && a[0] === b[0] && a[1] === b[1];
  const colorFor = (value) => /^#[\da-f]{6}$/i.test(value || '') ? value : palette.mint;
  const display = (value, fallback = '—') => value === undefined || value === null ? fallback : String(value);
  const words = (value) => String(value || '').replace(/[_-]+/g, ' ');
  const forced = (item) => item.forced === true || /forced/i.test(item.decision_source || '');
  const collided = (item) => Boolean(item.collision) && item.collision !== 'none';

  function validateData(data) {
    if (!data || data.schema !== 'nanojev-arcade-v1' || !Array.isArray(data.examples) || !data.examples.length) {
      throw new Error('The recording file does not contain a supported arcade dataset.');
    }
    for (const item of data.examples) {
      if (!['maze', 'snake'].includes(item.game) || !Number.isInteger(item.size) || item.size < 2 ||
          !item.initial || !Array.isArray(item.systems) || !item.systems.length) {
        throw new Error('A recorded example has an invalid game, board or system list.');
      }
      if (item.game === 'maze' && (!Array.isArray(item.initial.walls) ||
          !item.initial.walls.every(isCoordinate) || !isCoordinate(item.initial.goal))) {
        throw new Error('A maze recording is missing its geometry.');
      }
      for (const model of item.systems) {
        if (!Array.isArray(model.frames) || !model.frames.length) throw new Error('A system has no recorded frames.');
        for (const state of model.frames) {
          if (item.game === 'maze' && !isCoordinate(state.position)) throw new Error('A maze frame has no position.');
          if (item.game === 'snake' && (!Array.isArray(state.body) || !state.body.length || !state.body.every(isCoordinate))) {
            throw new Error('A Snake frame has no ordered body.');
          }
          if (state.food != null && !isCoordinate(state.food)) throw new Error('A food coordinate is invalid.');
          for (const value of Object.values(state.probabilities || {})) {
            if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1) {
              throw new Error('A recorded probability is outside [0, 1].');
            }
          }
        }
      }
    }
  }

  function defaultSystem(item) {
    const index = item.systems.findIndex((model) => /nanojev/i.test(`${model.id} ${model.name}`) &&
      !/starting|start_|initial/i.test(`${model.id} ${model.name}`));
    return index >= 0 ? index : 0;
  }

  function stop() {
    ui.playing = false;
    if (ui.animation !== null) cancelAnimationFrame(ui.animation);
    ui.animation = null;
    $('playIcon').textContent = '▶';
    $('playButton').setAttribute('aria-label', ui.data && ui.step === lastStep() ? 'Replay recorded run' : 'Play recorded run');
  }

  function duration(exampleIndex = ui.example, systemIndex = ui.system) {
    if (!ui.data) return 0;
    const model = ui.data.examples[exampleIndex]?.systems[systemIndex];
    if (!model) throw new RangeError('Unknown example or system index.');
    return (model.frames.length - 1) / ui.speed;
  }

  function getSnapshot() {
    if (!api.ready) return { ready: false, error: api.error };
    return JSON.parse(JSON.stringify({
      ready: true, error: api.error, exampleIndex: ui.example, systemIndex: ui.system,
      exampleId: example().id, systemId: system().id, systemName: system().name,
      game: example().game, size: example().size, controller: example().controller,
      step: ui.step, totalSteps: lastStep(), playing: ui.playing, stepsPerSecond: ui.speed,
      durationSeconds: duration(), frame: frame(), summary: system().summary || {},
      probabilityKind: probabilityKind(), decisionTemporalMeaning: 'decision_producing_this_frame',
    }));
  }

  function setFrame(exampleIndex, systemIndex, step) {
    if (!api.ready) throw new Error(api.error || 'Arcade recordings are still loading.');
    if (![exampleIndex, systemIndex, step].every(Number.isInteger)) throw new TypeError('Frame indices must be integers.');
    const target = ui.data.examples[exampleIndex]?.systems[systemIndex];
    if (!target || step < 0 || step >= target.frames.length) throw new RangeError('Requested recorded frame does not exist.');
    stop();
    const changed = ui.example !== exampleIndex || ui.system !== systemIndex;
    ui.example = exampleIndex; ui.system = systemIndex; ui.step = step;
    if (changed) renderSelection();
    renderFrame();
    return getSnapshot();
  }

  function selectExample(index) {
    setFrame(index, defaultSystem(ui.data.examples[index]), 0);
  }

  function probabilityKind() {
    return frame().probability_kind || system().probability_kind || example().probability_kind ||
      (example().game === 'maze' ? 'independent_safety' : 'action_distribution');
  }

  function resultLabel(outcome, game, success) {
    const value = String(outcome || '').toLowerCase();
    if (game === 'snake' && /^(alive|survived|horizon_survived)$/.test(value)) return 'Survived';
    if (success === true || /^(win|won|success|goal|goal_reached|goal reached|completed|complete)$/.test(value)) {
      return game === 'maze' ? 'Goal reached' : 'Board cleared';
    }
    if (/collision|crash|dead|death/.test(value)) return 'Collision';
    if (/step|horizon|limit|timeout/.test(value)) return 'Step limit';
    if (value === 'alive' || value === 'survived') return 'Survived';
    return value ? words(outcome).replace(/^./, (letter) => letter.toUpperCase()) : 'Recorded end';
  }

  function isSuccess(model, game) {
    const label = resultLabel(model.summary?.outcome, game, model.summary?.success);
    return label === 'Goal reached' || label === 'Board cleared' || (game === 'snake' && label === 'Survived');
  }

  function renderSelection() {
    const item = example();
    document.documentElement.style.setProperty('--system', colorFor(system().color));
    $('exampleTitle').textContent = item.title || (item.game === 'maze' ? 'Find the way through.' : 'Every move matters.');
    $('exampleSubtitle').textContent = item.subtitle || 'A complete recorded run';
    $('gameEyebrow').textContent = item.game === 'maze' ? 'NAVIGATION LAB' : 'SURVIVAL LAB';
    $('boardSize').textContent = `${item.size} × ${item.size}`;
    $('systemDetail').textContent = system().detail || '';
    document.querySelectorAll('[data-game]').forEach((button) => {
      const active = button.dataset.game === item.game;
      button.classList.toggle('active', active); button.setAttribute('aria-pressed', String(active));
      button.disabled = !ui.data.examples.some((value) => value.game === button.dataset.game);
    });
    const choices = ui.data.examples.map((value, index) => ({ value, index })).filter(({ value }) => value.game === item.game);
    $('exampleSelect').replaceChildren(...choices.map(({ value, index }) => {
      const option = document.createElement('option'); option.value = index;
      option.textContent = value.title || `${value.size} × ${value.size}`; option.selected = index === ui.example;
      return option;
    }));
    $('exampleSelect').hidden = choices.length < 2;
    $('systemTabs').replaceChildren(...item.systems.map((model, index) => {
      const button = document.createElement('button'); button.type = 'button'; button.textContent = model.name;
      button.className = index === ui.system ? 'active' : '';
      button.setAttribute('aria-pressed', String(index === ui.system));
      button.addEventListener('click', () => setFrame(ui.example, index, Math.min(ui.step, model.frames.length - 1)));
      return button;
    }));
    const legend = item.game === 'maze' ? [['Agent', colorFor(system().color)], ['Trail', palette.cyan], ['Goal', palette.coral]] :
      [['Head', colorFor(system().color)], ['Body', '#3b978a'], ['Food', palette.coral]];
    $('boardLegend').replaceChildren(...legend.map(([label, color]) => {
      const span = document.createElement('span'); const dot = document.createElement('i'); dot.style.background = color;
      span.append(dot, document.createTextNode(label)); return span;
    }));
    $('resultsComparison').replaceChildren(...item.systems.map((model, index) => {
      const row = document.createElement('div'); row.className = 'comparison-row' + (index === ui.system ? ' selected' : '');
      const name = document.createElement('span'); name.textContent = model.name;
      const count = document.createElement('span'); const summary = model.summary || {};
      count.textContent = item.game === 'snake' ? `${display(summary.score)} food · ${display(summary.steps)} moves` : `${display(summary.steps)} attempts`;
      const outcome = document.createElement('span'); outcome.textContent = resultLabel(summary.outcome, item.game, summary.success);
      outcome.className = isSuccess(model, item.game) ? 'success' : '';
      row.append(name, count, outcome); return row;
    }));
    $('metricSecondaryLabel').textContent = item.game === 'snake' ? 'Food eaten' : 'Grid size';
    $('timeline').max = lastStep();
    canvas.setAttribute('aria-label', `${item.game === 'maze' ? 'Maze' : 'Snake'} recorded state, ${item.size} by ${item.size} board`);
  }

  function renderFrame() {
    const current = frame(); const item = example(); const model = system();
    const final = ui.step === lastStep(); const hasDecision = ui.step > 0;
    const kind = probabilityKind(); const isForced = hasDecision && forced(current);
    $('probabilityTitle').textContent = isForced ? 'Forced move' : kind === 'independent_safety' ? 'Safety probabilities' : 'Action probabilities';
    $('decisionEyebrow').textContent = hasDecision ? 'LAST DECISION' : 'INITIAL STATE';
    $('actionBadge').textContent = hasDecision ? display(current.action, 'NO ACTION').toUpperCase() : 'NO DECISION YET';
    $('probabilityBars').replaceChildren(...DIRECTIONS.map(([id, label, arrow]) => {
      const row = document.createElement('div'); row.className = 'probability-row' + (hasDecision && current.action === id ? ' chosen' : '');
      const icon = document.createElement('span'); icon.className = 'direction-icon'; icon.textContent = arrow;
      const title = document.createElement('span'); title.className = 'direction-label'; title.textContent = label;
      const track = document.createElement('div'); track.className = 'bar-track';
      const fill = document.createElement('div'); fill.className = 'bar-fill';
      const probability = hasDecision ? current.probabilities?.[id] : undefined;
      fill.style.width = `${probability === undefined ? 0 : probability * 100}%`; track.append(fill);
      const text = document.createElement('span'); text.className = 'probability-value';
      text.textContent = probability === undefined ? '—' : `${(probability * 100).toFixed(1)}%`;
      row.append(icon, title, track, text); return row;
    }));
    $('probabilityNote').textContent = !hasDecision ? 'No action has been taken in this frame.' : isForced ?
      'Code-selected move · this action produced the displayed state.' : kind === 'independent_safety' ?
        'Independent direction checks · decision from the preceding state.' : 'Recorded distribution · decision from the preceding state.';
    $('metricSteps').textContent = ui.step;
    $('metricStepsTotal').textContent = `of ${lastStep()} recorded attempts`;
    $('metricSecondary').textContent = item.game === 'snake' ? display(current.score, 0) : `${item.size}×${item.size}`;
    $('metricSecondaryNote').textContent = item.game === 'snake' ? `${current.body.length} body segments` : `${item.size * item.size} board cells`;
    $('metricCollisions').textContent = model.frames.slice(1, ui.step + 1).filter(collided).length;
    const outcome = final ? resultLabel(model.summary?.outcome, item.game, model.summary?.success) : ui.step === 0 ? 'Ready' : 'In progress';
    $('metricStatus').textContent = outcome;
    $('metricStatusNote').textContent = final ? 'Final recorded state' : ui.step === 0 ? 'Initial state' : 'Playback in progress';
    $('decisionSource').textContent = !hasDecision ? 'Explore the recorded run, one step at a time.' : isForced ?
      'Last action: forced by code.' : current.decision_source ? `Last action source: ${words(current.decision_source)}.` : 'Last action: recorded decision.';
    $('timelineLabel').textContent = final ? 'FINAL RECORDED STATE' : hasDecision ? `STEP ${String(ui.step).padStart(3, '0')}` : 'INITIAL STATE';
    $('timelineCount').textContent = `${ui.step} / ${lastStep()} steps`;
    $('timeline').value = ui.step; $('timeline').style.setProperty('--progress', `${lastStep() ? ui.step / lastStep() * 100 : 0}%`);
    $('previousButton').disabled = ui.step === 0; $('nextButton').disabled = final;
    $('playButton').disabled = lastStep() === 0;
    const banner = $('terminalBanner'); banner.hidden = !final || lastStep() === 0;
    banner.classList.toggle('failure', final && !isSuccess(model, item.game));
    $('terminalTitle').textContent = final && outcome === 'Step limit' ? 'Step limit reached' : outcome;
    $('terminalDetail').textContent = item.game === 'snake' ? `${display(current.score, 0)} food · ${ui.step} moves` : `${ui.step} recorded attempts`;
    banner.querySelector('.terminal-symbol').textContent = isSuccess(model, item.game) ? '✓' : '■';
    draw();
  }

  function roundedRect(x, y, width, height, radius) {
    ctx.beginPath(); ctx.roundRect(x, y, width, height, Math.min(radius, width / 2, height / 2)); ctx.fill();
  }

  function draw() {
    if (!api.ready || !ctx) return;
    const bounds = canvas.getBoundingClientRect();
    const width = Math.max(1, bounds.width), height = Math.max(1, bounds.height);
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    if (canvas.width !== Math.round(width * ratio) || canvas.height !== Math.round(height * ratio)) {
      canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
    }
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0); ctx.clearRect(0, 0, width, height);
    const size = example().size; const margin = size >= 32 ? 20 : 29;
    const cell = Math.min((width - margin * 2) / size, (height - margin * 2) / size);
    const side = cell * size, left = (width - side) / 2, top = (height - side) / 2;
    const center = ([row, column]) => [left + (column + .5) * cell, top + (row + .5) * cell];
    ctx.fillStyle = '#0b1721'; roundedRect(left - 6, top - 6, side + 12, side + 12, 5);
    if (example().game === 'maze') drawMaze({ cell, side, left, top, center });
    else drawSnake({ cell, side, left, top, center });
    ctx.strokeStyle = '#4563784a'; ctx.lineWidth = 1; ctx.strokeRect(left - .5, top - .5, side + 1, side + 1);
  }

  function drawMaze({ cell, side, left, top, center }) {
    const item = example(); const current = frame(); const color = colorFor(system().color);
    ctx.fillStyle = '#8eabb72c'; ctx.fillRect(left, top, side, side);
    const inset = Math.min(.45, cell * .025);
    ctx.fillStyle = '#0a1420';
    for (const [row, col] of item.initial.walls) {
      ctx.fillRect(left + col * cell + inset, top + row * cell + inset, cell - 2 * inset, cell - 2 * inset);
    }
    const trace = system().frames.slice(0, ui.step + 1).map((value) => value.position);
    if (trace.length > 1) {
      ctx.lineJoin = 'round'; ctx.lineCap = 'round'; ctx.lineWidth = Math.max(1.4, cell * .24);
      ctx.strokeStyle = `${palette.cyan}80`; ctx.beginPath();
      trace.forEach((position, index) => { const [x, y] = center(position); if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); });
      ctx.stroke();
      ctx.strokeStyle = color; ctx.lineWidth = Math.max(1.5, cell * .26); ctx.beginPath();
      trace.slice(-8).forEach((position, index) => { const [x, y] = center(position); if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); });
      ctx.stroke();
    }
    const [sx, sy] = center(system().frames[0].position);
    ctx.strokeStyle = '#c3d5e285'; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.arc(sx, sy, Math.max(2, cell * .23), 0, 2 * Math.PI); ctx.stroke();
    const [gx, gy] = center(item.initial.goal);
    ctx.shadowColor = palette.coral; ctx.shadowBlur = 10; ctx.fillStyle = palette.coral;
    roundedRect(gx - cell * .27, gy - cell * .27, cell * .54, cell * .54, cell * .1); ctx.shadowBlur = 0;
    ctx.strokeStyle = '#ffbdb89c'; ctx.lineWidth = 1; ctx.strokeRect(gx - cell * .39, gy - cell * .39, cell * .78, cell * .78);
    const [x, y] = center(current.position);
    ctx.shadowColor = color; ctx.shadowBlur = 15; ctx.fillStyle = color;
    ctx.beginPath(); ctx.arc(x, y, Math.max(2.6, cell * .32), 0, 2 * Math.PI); ctx.fill(); ctx.shadowBlur = 0;
    ctx.fillStyle = '#ecfff5'; ctx.beginPath(); ctx.arc(x, y, Math.max(.8, cell * .12), 0, 2 * Math.PI); ctx.fill();
    if (collided(current)) { ctx.strokeStyle = palette.coral; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(x, y, Math.max(5, cell * .62), 0, Math.PI * 2); ctx.stroke(); }
  }

  function drawSnake({ cell, side, left, top, center }) {
    const current = frame(); const color = colorFor(system().color); const size = example().size;
    ctx.fillStyle = '#0b1a27'; ctx.fillRect(left, top, side, side);
    ctx.strokeStyle = '#314e632f'; ctx.lineWidth = .65; ctx.beginPath();
    for (let n = 1; n < size; n++) {
      ctx.moveTo(left + n * cell, top); ctx.lineTo(left + n * cell, top + side);
      ctx.moveTo(left, top + n * cell); ctx.lineTo(left + side, top + n * cell);
    } ctx.stroke();
    if (current.food) {
      const [x, y] = center(current.food); ctx.fillStyle = palette.coral; ctx.shadowColor = palette.coral; ctx.shadowBlur = 17;
      ctx.beginPath(); ctx.arc(x, y, Math.max(2.5, cell * .25), 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0;
      ctx.fillStyle = '#ffd2ba'; ctx.beginPath(); ctx.arc(x - cell * .055, y - cell * .07, Math.max(.8, cell * .07), 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#8ef3c6'; ctx.lineWidth = Math.max(1, cell * .055); ctx.beginPath(); ctx.moveTo(x, y - cell * .29); ctx.lineTo(x + cell * .09, y - cell * .39); ctx.stroke();
    }
    const body = current.body;
    for (let index = body.length - 1; index >= 0; index--) {
      const [x, y] = center(body[index]); const segmentWidth = cell * .72;
      ctx.fillStyle = index === 0 ? color : `hsl(${162 + Math.min(index, 30)}, ${49 + 20 / (index + 1)}%, ${Math.max(30, 57 - index * .55)}%)`;
      if (index + 1 < body.length) {
        const [px, py] = center(body[index + 1]);
        if (Math.abs(body[index][0] - body[index + 1][0]) + Math.abs(body[index][1] - body[index + 1][1]) === 1) {
          ctx.fillRect(Math.min(x, px) - segmentWidth / 2, Math.min(y, py) - segmentWidth / 2,
            Math.abs(x - px) + segmentWidth, Math.abs(y - py) + segmentWidth);
        }
      }
      if (index === 0) { ctx.shadowColor = color; ctx.shadowBlur = 12; }
      roundedRect(x - segmentWidth / 2, y - segmentWidth / 2, segmentWidth, segmentWidth, cell * .2); ctx.shadowBlur = 0;
    }
    const [hx, hy] = center(body[0]);
    let [dr, dc] = body.length > 1 ? [body[0][0] - body[1][0], body[0][1] - body[1][1]] : [0, 1];
    if (Math.abs(dr) + Math.abs(dc) !== 1) [dr, dc] = [0, 1];
    ctx.fillStyle = '#092d27';
    for (const sign of [-1, 1]) {
      ctx.beginPath(); ctx.arc(hx + dc * cell * .19 + dr * sign * cell * .14,
        hy + dr * cell * .19 - dc * sign * cell * .14, Math.max(1, cell * .06), 0, 2 * Math.PI); ctx.fill();
    }
    if (collided(current)) { ctx.strokeStyle = palette.coral; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(hx, hy, cell * .58, 0, Math.PI * 2); ctx.stroke(); }
  }

  function play() {
    if (!api.ready || lastStep() === 0) return;
    if (ui.playing) { stop(); return; }
    if (ui.step === lastStep()) { ui.step = 0; renderFrame(); }
    ui.playing = true; ui.tick = performance.now();
    $('playIcon').textContent = 'Ⅱ'; $('playButton').setAttribute('aria-label', 'Pause recorded run');
    function advance(now) {
      if (!ui.playing) return;
      const elapsed = now - ui.tick; const interval = 1000 / ui.speed;
      if (elapsed >= interval) {
        const count = Math.floor(elapsed / interval); ui.tick += count * interval;
        ui.step = Math.min(lastStep(), ui.step + count); renderFrame();
        if (ui.step === lastStep()) { stop(); return; }
      }
      ui.animation = requestAnimationFrame(advance);
    }
    ui.animation = requestAnimationFrame(advance);
  }

  $('playButton').addEventListener('click', play);
  $('timeline').addEventListener('input', (event) => setFrame(ui.example, ui.system, Number(event.target.value)));
  $('previousButton').addEventListener('click', () => setFrame(ui.example, ui.system, Math.max(0, ui.step - 1)));
  $('nextButton').addEventListener('click', () => setFrame(ui.example, ui.system, Math.min(lastStep(), ui.step + 1)));
  $('speedSelect').addEventListener('change', (event) => { ui.speed = Number(event.target.value); ui.tick = performance.now(); });
  $('exampleSelect').addEventListener('change', (event) => selectExample(Number(event.target.value)));
  document.querySelectorAll('[data-game]').forEach((button) => button.addEventListener('click', () => {
    if (!api.ready) return;
    const candidates = ui.data.examples.map((value, index) => ({ value, index })).filter(({ value }) => value.game === button.dataset.game);
    const target = candidates.find(({ value }) => value.game === 'maze' && value.size === 50) || candidates[0];
    if (target) selectExample(target.index);
  }));
  new ResizeObserver(() => draw()).observe($('canvasWrap'));
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });

  async function init() {
    try {
      if (!ctx) throw new Error('This browser does not support a 2D game canvas.');
      const response = await fetch('./arcade_results.json', { cache: 'no-store' });
      if (!response.ok) throw new Error(`The recording file could not be loaded (HTTP ${response.status}).`);
      const data = await response.json(); validateData(data); ui.data = data;
      const maze50 = data.examples.findIndex((item) => item.game === 'maze' && item.size === 50);
      ui.example = maze50 >= 0 ? maze50 : 0; ui.system = defaultSystem(example());
      api.ready = true;
      $('loadMessage').hidden = true; $('workspace').hidden = false; $('transport').hidden = false;
      renderSelection(); renderFrame();
    } catch (error) {
      stop(); api.error = error.message; api.ready = false;
      $('workspace').hidden = true; $('transport').hidden = true; $('loadMessage').hidden = false;
      $('loadMessage').classList.add('error'); $('loadMessage').querySelector('h1').textContent = 'Recordings are not available yet';
      $('loadMessage').querySelector('p').textContent = `${error.message} Serve this page with its arcade_results.json file to open the real game replays.`;
    }
  }
  init();
})();
