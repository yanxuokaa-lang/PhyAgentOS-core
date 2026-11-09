/* All visible states and probabilities come from the supplied recordings. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const ORDER = ['jev', 'nanojev', 'base'];
  const ACCENTS = { jev: '#578d9a', nanojev: '#198875', base: '#8b77b1' };
  const DIRECTIONS = [['north', 'N', '↑'], ['east', 'E', '→'], ['south', 'S', '↓'], ['west', 'W', '←']];
  const state = { data: null, example: 0, step: 0, speed: 16, playing: false, trail: true, animation: null, tick: 0, panels: [] };
  const collisions = new WeakMap();
  const api = { ready: false, error: null, setFrame, getSnapshot };
  window.nanojevComparison = api;
  const currentExample = () => state.data.examples[state.example];
  const systems = () => ORDER.map((id) => currentExample().systems.find((item) => item.id === id));
  const lastStep = () => Math.max(...systems().map((item) => item.frames.length - 1));
  const coordinate = (value) => Array.isArray(value) && value.length === 2 && value.every(Number.isInteger);
  const collision = (frame) => Boolean(frame.collision) && frame.collision !== 'none';
  const forced = (frame) => frame.forced === true || /forced/i.test(frame.decision_source || '');
  const textValue = (value) => value == null ? '—' : String(value);

  function validateData(data) {
    if (!data || data.schema !== 'nanojev-arcade-v1' || !Array.isArray(data.examples) || data.examples.length !== 2 ||
        new Set(data.examples.map((item) => item.game)).size !== 2) throw new Error('The comparison needs both recorded games.');
    for (const example of data.examples) {
      if (!['maze', 'snake'].includes(example.game) || !Number.isInteger(example.size) || example.size < 2 || !example.initial ||
          !Array.isArray(example.systems) || example.systems.length !== 3 ||
          ORDER.some((id) => example.systems.filter((item) => item.id === id).length !== 1)) {
        throw new Error('Each game must contain Jev, NanoJev and the recorded baseline.');
      }
      if (example.game === 'maze' && (!Array.isArray(example.initial.walls) ||
          !example.initial.walls.every(coordinate) || !coordinate(example.initial.goal))) throw new Error('A maze has incomplete geometry.');
      for (const system of example.systems) {
        if (typeof system.name !== 'string' || !system.name.trim() || !Array.isArray(system.frames) || !system.frames.length) {
          throw new Error('A recorded system is missing its name or frames.');
        }
        let count = 0;
        const cumulative = [];
        system.frames.forEach((frame, index) => {
          if (example.game === 'maze' && !coordinate(frame.position)) throw new Error('A maze frame is missing its position.');
          if (example.game === 'snake' && (!Array.isArray(frame.body) || !frame.body.length || !frame.body.every(coordinate))) {
            throw new Error('A Snake frame is missing its ordered body.');
          }
          if (frame.food != null && !coordinate(frame.food)) throw new Error('A food position is invalid.');
          for (const probability of Object.values(frame.probabilities || {})) {
            if (typeof probability !== 'number' || !Number.isFinite(probability) || probability < 0 || probability > 1) {
              throw new Error('A recorded probability is invalid.');
            }
          }
          if (index > 0 && collision(frame)) count++;
          cumulative.push(count);
        });
        collisions.set(system, cumulative);
      }
    }
  }

  function pause() {
    state.playing = false;
    if (state.animation !== null) cancelAnimationFrame(state.animation);
    state.animation = null;
    $('playIcon').textContent = '▶';
    $('play').setAttribute('aria-label', 'Play all three recordings');
  }

  function getSnapshot() {
    if (!api.ready) return { ready: false, error: api.error };
    const example = currentExample();
    return JSON.parse(JSON.stringify({ ready: true, error: null, exampleIndex: state.example,
      exampleId: example.id, game: example.game, size: example.size, controller: example.controller,
      globalStep: state.step, step: state.step, totalSteps: lastStep(), playing: state.playing,
      stepsPerSecond: state.speed, showTrail: state.trail, synchronization: 'environment_step',
      decisionTemporalMeaning: 'decision_producing_this_frame',
      systems: systems().map((system) => {
        const localStep = Math.min(state.step, system.frames.length - 1);
        return { id: system.id, name: system.name, systemIndex: example.systems.indexOf(system),
          localStep, step: localStep, totalSteps: system.frames.length - 1,
          finished: localStep === system.frames.length - 1, frame: system.frames[localStep], summary: system.summary || {} };
      }),
    }));
  }

  function setFrame(exampleIndex, step) {
    if (!api.ready) throw new Error(api.error || 'Recorded games are still loading.');
    if (!Number.isInteger(exampleIndex) || !Number.isInteger(step)) throw new TypeError('Frame indices must be integers.');
    const example = state.data.examples[exampleIndex];
    if (!example || step < 0 || step > Math.max(...example.systems.map((item) => item.frames.length - 1))) {
      throw new RangeError('This recorded environment step does not exist.');
    }
    pause();
    const changed = exampleIndex !== state.example;
    state.example = exampleIndex; state.step = step;
    if (changed) renderScene();
    renderFrame();
    return getSnapshot();
  }

  function outcomeLabel(system, game) {
    const value = String(system.summary?.outcome || '').toLowerCase();
    if (game === 'snake' && /^(alive|survived|horizon_survived)$/.test(value)) return 'Survived';
    if (/^(win|won|success|goal|goal_reached|completed|complete)$/.test(value)) return game === 'maze' ? 'Goal reached' : 'Board cleared';
    if (/trapped/.test(value)) return 'Trapped';
    if (/collision|crash|dead|death/.test(value)) return 'Collision';
    if (/step|horizon|limit|timeout/.test(value)) return 'Step limit';
    return value ? value.replace(/[_-]/g, ' ').replace(/^./, (letter) => letter.toUpperCase()) : 'Recorded end';
  }

  function renderScene() {
    const example = currentExample();
    state.speed = example.game === 'maze' ? 256 : 16;
    $('speed').value = String(state.speed);
    state.tick = performance.now();
    $('sceneTag').textContent = example.game.toUpperCase();
    $('sceneTitle').textContent = example.title || (example.game === 'maze' ? 'Find the exit' : 'Keep growing');
    $('sceneSize').textContent = `${example.size} × ${example.size}`;
    $('sceneCaption').textContent = 'Recorded decisions + shared code planning';
    document.querySelectorAll('[data-game]').forEach((button) => {
      const active = button.dataset.game === example.game;
      button.classList.toggle('active', active); button.setAttribute('aria-pressed', String(active));
    });
    state.panels = systems().map((system) => {
      const card = $('modelTemplate').content.firstElementChild.cloneNode(true);
      card.dataset.system = system.id;
      card.style.setProperty('--accent', ACCENTS[system.id]);
      card.classList.toggle('primary', system.id === 'nanojev');
      card.querySelector('.model-name').textContent = system.name;
      card.querySelector('.model-name').title = system.detail || system.name;
      card.querySelector('.model-role').textContent = system.id === 'nanojev' ? '0.6B · PARALLEL DECISIONS' :
        system.id === 'jev' ? 'JEV · API' : 'COMPARISON MODEL';
      card.querySelector('.stat-label').textContent = example.game === 'maze' ? 'Attempts' : 'Steps';
      card.querySelector('.stat-secondary-label').textContent = example.game === 'snake' ? 'Food collected' : 'Collisions';
      const canvas = card.querySelector('canvas');
      canvas.setAttribute('aria-label', `${system.name}: ${example.game} recorded board`);
      // A consistent software raster path keeps captured replay pixels stable
      // across browser readbacks, which otherwise can switch GPU/CPU backends.
      const context = canvas.getContext('2d', {willReadFrequently: true});
      if (!context) throw new Error('This browser does not support a 2D game canvas.');
      const bars = DIRECTIONS.map(([id, label, arrow]) => {
        const item = document.createElement('div'); item.className = 'probability-item';
        const top = document.createElement('div'); top.className = 'probability-top';
        const direction = document.createElement('span'); direction.textContent = `${arrow} ${label}`;
        const value = document.createElement('span'); value.className = 'probability-value';
        top.append(direction, value);
        const track = document.createElement('div'); track.className = 'probability-track';
        const fill = document.createElement('div'); fill.className = 'probability-fill'; track.append(fill);
        item.append(top, track); card.querySelector('.probability-grid').append(item);
        return { id, item, value, fill };
      });
      return { system, card, canvas, context, bars };
    });
    $('modelPanels').replaceChildren(...state.panels.map((panel) => panel.card));
    $('timeline').max = lastStep();
  }

  function renderFrame() {
    const example = currentExample();
    for (const panel of state.panels) {
      const { system, card } = panel;
      const step = Math.min(state.step, system.frames.length - 1);
      const frame = system.frames[step]; const final = step === system.frames.length - 1;
      const label = final ? outcomeLabel(system, example.game) : step === 0 ? 'Ready' : 'Playing';
      const positive = ['Goal reached', 'Board cleared', 'Survived'].includes(label);
      card.querySelector('.stat-steps').textContent = step;
      card.querySelector('.stat-total').textContent = `/ ${system.frames.length - 1} recorded`;
      card.querySelector('.stat-secondary').textContent = example.game === 'snake' ? textValue(frame.score) : collisions.get(system)[step];
      card.querySelector('.stat-status').textContent = label;
      card.querySelector('.stat-outcome').textContent = final ? 'Final frame held' : example.game === 'snake' ? `${collisions.get(system)[step]} collisions` : 'Exploring the maze';
      const badge = card.querySelector('.board-status');
      badge.hidden = !final; badge.textContent = positive ? `✓ ${label}` : label;
      badge.classList.toggle('negative', !positive);
      const isForced = step > 0 && forced(frame);
      card.querySelector('.decision-title').textContent = step ? 'Last decision' : 'Initial state';
      card.querySelector('.decision-action').textContent = !step ? 'No action yet' :
        `${isForced ? 'Forced · ' : ''}${frame.action || 'No action'}`;
      for (const bar of panel.bars) {
        const value = step ? frame.probabilities?.[bar.id] : undefined;
        bar.value.textContent = value === undefined ? '—' : `${(value * 100).toFixed(1)}%`;
        bar.fill.style.width = `${value === undefined ? 0 : value * 100}%`;
        bar.item.classList.toggle('chosen', step > 0 && frame.action === bar.id);
      }
      const kind = frame.probability_kind || system.probability_kind || example.probability_kind;
      card.querySelector('.probability-kind').textContent = !step ? 'Awaiting the first recorded action' : isForced ? 'Code-forced move' :
        kind === 'independent_safety' ? 'Independent safety probabilities' : 'Action probabilities';
      card.querySelector('.decision-origin').textContent = step ? 'From the preceding state' : '';
      drawBoard(panel, step);
    }
    const end = lastStep();
    $('timeline').value = state.step;
    $('timeline').style.setProperty('--progress', `${end ? state.step / end * 100 : 0}%`);
    $('stepCounter').textContent = `${state.step} / ${end}`;
    $('previous').disabled = state.step === 0; $('restart').disabled = state.step === 0;
    $('next').disabled = state.step === end; $('play').disabled = end === 0;
  }

  function drawBoard(panel, step) {
    const { canvas, context: ctx, system } = panel;
    const rect = canvas.getBoundingClientRect();
    if (rect.width < 1 || rect.height < 1) return;
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    if (canvas.width !== Math.round(rect.width * ratio) || canvas.height !== Math.round(rect.height * ratio)) {
      canvas.width = Math.round(rect.width * ratio); canvas.height = Math.round(rect.height * ratio);
    }
    // Trails change line caps/joins. Keep every frame independent of prior draws.
    ctx.save();
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0); ctx.clearRect(0, 0, rect.width, rect.height);
    const example = currentExample(); const frame = system.frames[step]; const accent = ACCENTS[system.id];
    const margin = example.size >= 32 ? 11 : 15;
    const cell = (Math.min(rect.width, rect.height) - margin * 2) / example.size;
    const side = cell * example.size, left = (rect.width - side) / 2, top = (rect.height - side) / 2;
    const center = ([row, col]) => [left + (col + .5) * cell, top + (row + .5) * cell];
    ctx.fillStyle = '#fafbf7'; ctx.fillRect(left, top, side, side);
    const trail = () => {
      if (!state.trail || step === 0) return;
      ctx.strokeStyle = `${accent}55`; ctx.lineWidth = Math.max(1.2, cell * .18);
      ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.beginPath();
      system.frames.slice(0, step + 1).forEach((value, index) => {
        const [x, y] = center(example.game === 'maze' ? value.position : value.body[0]);
        if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }); ctx.stroke();
    };
    const round = (x, y, width, height, radius) => {
      ctx.beginPath(); ctx.roundRect(x, y, width, height, Math.min(radius, width / 2)); ctx.fill();
    };
    if (example.game === 'maze') {
      ctx.fillStyle = '#ccd5c9';
      for (const [row, col] of example.initial.walls) ctx.fillRect(left + col * cell, top + row * cell, cell + .1, cell + .1);
      trail();
      const [gx, gy] = center(example.initial.goal);
      ctx.fillStyle = '#df816c'; ctx.shadowColor = '#df816c66'; ctx.shadowBlur = 7;
      round(gx - cell * .3, gy - cell * .3, cell * .6, cell * .6, cell * .09); ctx.shadowBlur = 0;
      const [sx, sy] = center(system.frames[0].position);
      ctx.strokeStyle = '#99ada0'; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(sx, sy, Math.max(1.5, cell * .23), 0, Math.PI * 2); ctx.stroke();
      const [x, y] = center(frame.position);
      ctx.fillStyle = accent; ctx.shadowColor = `${accent}80`; ctx.shadowBlur = 8;
      ctx.beginPath(); ctx.arc(x, y, Math.max(2.1, cell * .34), 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0;
      ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(x, y, Math.max(.65, cell * .1), 0, Math.PI * 2); ctx.fill();
      if (collision(frame)) { ctx.strokeStyle = '#d67a61'; ctx.lineWidth = 1.4; ctx.beginPath(); ctx.arc(x, y, Math.max(3.8, cell * .6), 0, Math.PI * 2); ctx.stroke(); }
    } else {
      ctx.strokeStyle = '#e6ece1'; ctx.lineWidth = .6; ctx.beginPath();
      for (let n = 1; n < example.size; n++) {
        ctx.moveTo(left + n * cell, top); ctx.lineTo(left + n * cell, top + side);
        ctx.moveTo(left, top + n * cell); ctx.lineTo(left + side, top + n * cell);
      } ctx.stroke(); trail();
      if (frame.food) {
        const [x, y] = center(frame.food); ctx.fillStyle = '#df816c';
        ctx.beginPath(); ctx.arc(x, y, Math.max(2, cell * .235), 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#ffe8d6'; ctx.beginPath(); ctx.arc(x - cell * .06, y - cell * .07, Math.max(.7, cell * .065), 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = '#7da58a'; ctx.lineWidth = Math.max(.8, cell * .06); ctx.beginPath(); ctx.moveTo(x, y - cell * .28); ctx.lineTo(x + cell * .09, y - cell * .37); ctx.stroke();
      }
      for (let index = frame.body.length - 1; index >= 0; index--) {
        const [x, y] = center(frame.body[index]); const width = cell * .7;
        ctx.globalAlpha = index === 0 ? 1 : Math.max(.55, .86 - index * .006); ctx.fillStyle = accent;
        if (index + 1 < frame.body.length) {
          const previous = frame.body[index + 1]; const [px, py] = center(previous);
          if (Math.abs(frame.body[index][0] - previous[0]) + Math.abs(frame.body[index][1] - previous[1]) === 1) {
            ctx.fillRect(Math.min(x, px) - width / 2, Math.min(y, py) - width / 2, Math.abs(x - px) + width, Math.abs(y - py) + width);
          }
        }
        round(x - width / 2, y - width / 2, width, width, cell * .16);
      }
      ctx.globalAlpha = 1;
      const [hx, hy] = center(frame.body[0]);
      let [dr, dc] = frame.body.length > 1 ? [frame.body[0][0] - frame.body[1][0], frame.body[0][1] - frame.body[1][1]] : [0, 1];
      if (Math.abs(dr) + Math.abs(dc) !== 1) [dr, dc] = [0, 1];
      ctx.fillStyle = '#fff';
      for (const sign of [-1, 1]) { ctx.beginPath(); ctx.arc(hx + dc * cell * .18 + dr * sign * cell * .135,
        hy + dr * cell * .18 - dc * sign * cell * .135, Math.max(.9, cell * .055), 0, Math.PI * 2); ctx.fill(); }
    }
    ctx.strokeStyle = '#d7e1d2'; ctx.lineWidth = .7; ctx.strokeRect(left, top, side, side);
    ctx.restore();
  }

  function play() {
    if (!api.ready || lastStep() === 0) return;
    if (state.playing) { pause(); return; }
    if (state.step === lastStep()) { state.step = 0; renderFrame(); }
    state.playing = true; state.tick = performance.now();
    $('playIcon').textContent = 'Ⅱ'; $('play').setAttribute('aria-label', 'Pause all three recordings');
    function advance(now) {
      if (!state.playing) return;
      const interval = 1000 / state.speed; const count = Math.floor((now - state.tick) / interval);
      if (count > 0) {
        state.tick += count * interval; state.step = Math.min(lastStep(), state.step + count); renderFrame();
        if (state.step === lastStep()) { pause(); return; }
      }
      state.animation = requestAnimationFrame(advance);
    }
    state.animation = requestAnimationFrame(advance);
  }

  function selectHash() {
    if (!api.ready) return;
    const game = location.hash.toLowerCase() === '#snake' ? 'snake' : 'maze';
    const index = state.data.examples.findIndex((example) => example.game === game);
    setFrame(index, 0);
  }
  document.querySelectorAll('[data-game]').forEach((button) => button.addEventListener('click', () => {
    if (!api.ready) return;
    if (location.hash === `#${button.dataset.game}`) selectHash(); else location.hash = button.dataset.game;
  }));
  window.addEventListener('hashchange', selectHash);
  $('play').addEventListener('click', play);
  $('restart').addEventListener('click', () => setFrame(state.example, 0));
  $('previous').addEventListener('click', () => setFrame(state.example, Math.max(0, state.step - 1)));
  $('next').addEventListener('click', () => setFrame(state.example, Math.min(lastStep(), state.step + 1)));
  $('timeline').addEventListener('input', (event) => setFrame(state.example, Number(event.target.value)));
  $('speed').addEventListener('change', (event) => { state.speed = Number(event.target.value); state.tick = performance.now(); });
  $('showTrail').addEventListener('change', (event) => { state.trail = event.target.checked; if (api.ready) renderFrame(); });
  new ResizeObserver(() => { if (api.ready) state.panels.forEach((panel) => drawBoard(panel, Math.min(state.step, panel.system.frames.length - 1))); }).observe($('modelPanels'));
  document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });

  async function init() {
    try {
      const response = await fetch('./side_by_side_results.json', { cache: 'no-store' });
      if (!response.ok) throw new Error(`The recording file could not be loaded (HTTP ${response.status}).`);
      state.data = await response.json(); validateData(state.data);
      const game = location.hash.toLowerCase() === '#snake' ? 'snake' : 'maze';
      state.example = state.data.examples.findIndex((example) => example.game === game);
      $('loadState').hidden = true; $('viewer').hidden = false;
      renderScene(); api.ready = true; renderFrame();
    } catch (error) {
      pause(); api.ready = false; api.error = error.message;
      $('viewer').hidden = true; $('loadState').hidden = false; $('loadState').classList.add('error');
      $('loadState').querySelector('h2').textContent = 'The recordings are not available yet';
      $('loadState').querySelector('p').textContent = `${error.message} Serve this page alongside its side_by_side_results.json file to view the real comparisons.`;
    }
  }
  init();
})();
