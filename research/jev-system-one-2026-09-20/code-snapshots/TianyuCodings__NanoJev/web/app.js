'use strict';

// All model outputs come from recorded results or the live service.
const $ = id => document.getElementById(id);
const ui = { data: null, models: [], modelIndex: 0, episodeIndex: 0, stepIndex: 0, batchIndex: 0, timer: null, batches: [] };
const own = (obj, key) => obj != null && Object.hasOwn(obj, key);
const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const json = value => JSON.stringify(value, null, 2);
const number = value => typeof value === 'number' && Number.isFinite(value);
const labels = {
  north: '↑ North', south: '↓ South', east: '→ East', west: '← West', stop: 'Stop', STOP: 'Stop',
  true: 'Yes', false: 'No', success_rate: 'Success rate', completion_rate: 'Completion rate', win_rate: 'Win rate', loss_rate: 'Loss rate',
  draw_rate: 'Draw rate', accuracy: 'Accuracy', optimal_action_accuracy: 'Optimal-action accuracy',
  episodes: 'Episodes', episode_count: 'Episodes', mean_steps: 'Mean steps',
  mean_regret: 'Mean extra path steps', mean_latency_ms: 'Mean inference latency · ms',
  p50_latency_ms: 'Inference latency p50 · ms', p95_latency_ms: 'Inference latency p95 · ms',
  optimal_action_rate: 'Optimal-action rate', preserved_nonlosing_initial_value_rate: 'Non-losing initial-value preservation',
  preserved_minimax_value_rate: 'Initial minimax-value preservation', mean_path_efficiency: 'Mean path efficiency',
  mean_p_optimal: 'Probability mass on optimal actions', actual_optimal_action_rate: 'Actual optimal-action rate',
  goal: 'Goal reached', horizon_exhausted: 'Step limit reached', win: 'Win', draw: 'Draw', loss: 'Loss',
  student: 'NanoJev', random: 'Uniform random', oracle: 'Oracle upper bound', minimax_opponent: 'Optimal opponent', forced_legal_action: 'Only legal action',
  native_lm: 'Untuned Qwen', jev_api: 'Jev',
  greedy: 'Greedy · argmax', sample: 'Sample · T=1',
  grid_navigation: 'Grid navigation', tic_tac_toe: 'Tic-tac-toe', test: 'TEST', ood: 'OOD', dev: 'DEV', train: 'TRAIN',
};
const defaultSources = [
  { title: 'TypeSafe · Official Doom and Wikiracing demos', url: 'https://typesafe.ai/blog/introducing-system-one-models-and-jev' },
  { title: 'Diogo Almeida · Doom launch post', url: 'https://x.com/CompleteSkeptic/status/2099925687465570372' },
  { title: 'vinnylarouge / jevlike · Independent open experiment', url: 'https://github.com/vinnylarouge/jevlike' },
];

function node(tag, className, text) {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (text !== undefined) item.textContent = String(text);
  return item;
}
function option(value, label) { const item = node('option', '', label); item.value = String(value); return item; }
function display(value) {
  if (value === null || value === undefined) return 'Not recorded';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (number(value)) return Number(value.toPrecision(5)).toString();
  return typeof value === 'object' ? JSON.stringify(value) : String(value);
}
function actionName(action) {
  const value = record(action) ? action.id ?? action.action ?? action.choice ?? JSON.stringify(action) : action;
  if (typeof value === 'string' && /^cell_[1-9]$/.test(value)) return `Cell ${value.slice(5)}`;
  return labels[value] ?? display(value);
}
function selectedModel() { return ui.models[ui.modelIndex] ?? null; }
function modelVersion(model) {
  if (String(model?.schema_version ?? '').startsWith('openjev-navigation-v3-')) return 'V3';
  if (record(model?.summary) && Object.keys(model.summary).some(key => key.includes('/'))) return 'V2';
  return 'Version unspecified';
}
function modelLabel(model, index) {
  const controller = model.controller ?? model.policy;
  const source = String(model.source_artifact ?? model.name ?? model.id ?? '');
  const arm = source.match(/v3_(gold|teacher)_(ascii|coords)_(single|multi)_seed\d+/);
  let name;
  if (source.includes('native_qwen')) name = 'Untuned Qwen';
  else if (source.includes('jev_api')) name = 'Jev';
  else if (arm) name = `NanoJev · ${arm[2] === 'ascii' ? 'ASCII' : 'coordinates'} · ${arm[3] === 'single' ? 'single start' : 'multiple starts'} · ${arm[1] === 'gold' ? 'variant A' : 'variant B'}`;
  else if (source.includes('game_teacher_v2')) name = 'NanoJev · variant B';
  else if (source.includes('game_gold_v2')) name = 'NanoJev · variant A';
  else if (controller === 'random') name = 'Uniform random';
  else if (controller === 'oracle') name = 'Oracle upper bound';
  else name = /\p{Script=Han}/u.test(source) ? `Model ${index + 1}` : source || `Model ${index + 1}`;
  const policyLabel = controller === 'student' ? 'Recorded policy' : labels[controller] ?? controller ?? 'Controller unspecified';
  return `${modelVersion(model)} · ${name} · ${policyLabel}`;
}
function modelIdentity(model) { return model ? `${model.name ?? model.id}|${model.policy}|${model.checkpoint_sha256}` : null; }
function episodes() { return Array.isArray(selectedModel()?.episodes) ? selectedModel().episodes : []; }
function selectedEpisode() { return episodes()[ui.episodeIndex] ?? null; }
function steps() { return Array.isArray(selectedEpisode()?.steps) ? selectedEpisode().steps : []; }
function currentStep() { return steps()[ui.stepIndex] ?? null; }
function stopPlayback() { if (ui.timer !== null) clearInterval(ui.timer); ui.timer = null; $('playButton').textContent = 'Play replay'; }
function notice(text) { $('notice').textContent = text; $('notice').hidden = !text; }
function empty(container, title, description) {
  const block = node('div', 'empty-state');
  block.append(node('span', 'empty-icon', '∷'), node('h3', '', title), node('p', '', description));
  container.replaceChildren(block);
}

function renderSources() {
  const supplied = Array.isArray(ui.data?.sources) ? ui.data.sources : [];
  const unique = new Map();
  for (const source of [...defaultSources, ...supplied]) {
    const value = typeof source === 'string' ? { url: source, title: source } : source;
    if (!record(value)) continue;
    try {
      const url = new URL(value.url ?? value.href);
      if (!['https:', 'http:'].includes(url.protocol)) continue;
      const known = defaultSources.find(source => new URL(source.url).origin + new URL(source.url).pathname === url.origin + url.pathname);
      const suppliedTitle = value.title ?? value.name ?? value.label ?? url.hostname;
      const title = known?.title ?? (/\p{Script=Han}/u.test(suppliedTitle) ? url.hostname + url.pathname : suppliedTitle);
      unique.set(url.href, { url: url.href, title });
    } catch { /* Invalid links never become executable HTML. */ }
  }
  $('sourceLinks').replaceChildren(...[...unique.values()].map(source => {
    const link = node('a', 'source-link');
    link.href = source.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
    link.append(node('span', '', source.title), node('span', '', '↗'));
    return link;
  }));
}

function summaryEntries(summary, prefix = '', depth = 0) {
  if (!record(summary)) return [];
  const values = [];
  for (const [key, value] of Object.entries(summary)) {
    const title = `${prefix}${labels[key] ?? key}`;
    if (record(value) && depth < 1) values.push(...summaryEntries(value, `${title} · `, depth + 1));
    else if (['number', 'string', 'boolean'].includes(typeof value)) values.push([title, value, key]);
  }
  return values;
}
function renderSummary() {
  const model = selectedModel();
  const navigationGroups = record(model?.summary) ? ['test', 'ood'].filter(key => record(model.summary[key]) && own(model.summary[key], 'completion_rate')) : [];
  const grouped = record(model?.summary) ? Object.entries(model.summary).filter(([key, value]) => key.includes('/') && record(value)) : [];
  const entries = navigationGroups.length ? navigationGroups.flatMap(split => {
    const values = model.summary[split], prefix = `${labels[split]} · ${display(values.episodes)} episodes`;
    return ['completion_rate', 'mean_path_efficiency', 'mean_steps', 'mean_p_optimal']
      .map(metric => [`${prefix} · ${labels[metric]}`, values[metric], metric]);
  }) : grouped.length ? grouped.flatMap(([group, values]) => {
    const name = group.split('/').map(part => labels[part] ?? part).join(' · ');
    const metric = own(values, 'success_rate') ? 'success_rate' : own(values, 'preserved_nonlosing_initial_value_rate') ? 'preserved_nonlosing_initial_value_rate' : 'optimal_action_rate';
    return [[`${name} · ${labels[metric] ?? metric}`, values[metric], metric], [`${name} · Recorded episodes`, values.episodes, 'episode_count']];
  }).slice(0, 8) : summaryEntries(model?.summary).slice(0, 8);
  if (model && !entries.length) entries.push(['Recorded episodes', episodes().length, 'episode_count']);
  $('summaryCards').replaceChildren(...entries.map(([title, value, key]) => {
    const card = node('div', 'summary-card');
    const formatted = number(value) && (/(?:rate|accuracy)$/.test(key) || ['mean_path_efficiency', 'mean_p_optimal'].includes(key)) && value >= 0 && value <= 1
      ? `${(value * 100).toFixed(1)}%` : display(value);
    card.append(node('span', 'metric-label', title), node('span', `metric-value${number(value) ? '' : ' text-value'}`, formatted));
    return card;
  }));
  $('checkpointHash').textContent = model?.checkpoint_sha256 ? `${model.checkpoint_sha256.slice(0, 16)}…` : model ? 'Not provided / baseline' : 'Not loaded';
  $('checkpointHash').title = model?.checkpoint_sha256 ?? '';
  const cohortHash = model?.cohort?.initial_states_sha256;
  const controller = model?.controller ?? model?.policy;
  $('cohortScope').textContent = !model ? 'The evaluation cohort and controller appear here after loading.'
    : `${modelVersion(model)} · ${labels[controller] ?? controller ?? 'Controller unspecified'} · ${episodes().length} complete episodes${typeof cohortHash === 'string' ? ` · Cohort ${cohortHash.slice(0, 12)}` : ''}. V2 and V3 use different map cohorts; compare scores within the same cohort.`;
  $('cohortScope').title = typeof cohortHash === 'string' ? cohortHash : '';
  $('rawSummary').textContent = model ? json({ name: model.name, policy: model.policy, checkpoint_sha256: model.checkpoint_sha256,
    summary: model.summary, cohort: model.cohort, execution: model.execution }) : 'Not loaded';
}

function environmentState(value, depth = 0) {
  if (depth > 4) return value;
  if (typeof value === 'string') { try { return environmentState(JSON.parse(value), depth + 1); } catch { return value; } }
  if (!record(value)) return value;
  if (value.game && (value.board !== undefined || value.position !== undefined)) return value;
  const nested = value.environment_state ?? value.metadata?.environment_state ?? value.state;
  return nested === undefined ? value : environmentState(nested, depth + 1);
}
function visibleState() {
  const episode = selectedEpisode(), list = steps(), step = currentStep();
  if (step) return environmentState(step.state ?? (ui.stepIndex === 0 ? episode.initial_state : list[ui.stepIndex - 1]?.next_state));
  return environmentState(list.at(-1)?.next_state ?? episode?.final_state ?? episode?.initial_state);
}
function legend(items) {
  $('boardLegend').replaceChildren(...items.map(([className, label]) => {
    const item = node('span', 'legend-item'); item.append(node('span', `legend-swatch ${className}`), node('span', '', label)); return item;
  }));
  $('boardLegend').hidden = false;
}
function renderBoard(state) {
  const board = $('gameBoard');
  board.replaceChildren(); board.className = 'game-board'; $('boardLegend').hidden = true;
  if (!state) { board.classList.add('empty-board'); empty(board, 'Waiting for experiment results', 'Reload once the recorded results are available.'); return; }
  const game = state?.game ?? selectedEpisode()?.game;
  if (game === 'grid_navigation' && Number.isInteger(state.size) && state.size >= 2 && state.size <= 32 && Array.isArray(state.position)) {
    const size = state.size;
    const walls = new Set((state.walls ?? []).map(cell => cell.join(',')));
    const trail = new Set(steps().slice(0, ui.stepIndex).map(step => environmentState(step.state)?.position?.join(',')).filter(Boolean));
    board.classList.add('grid-board'); board.style.setProperty('--board-size', size);
    board.setAttribute('role', 'img'); board.setAttribute('aria-label', `${size} by ${size} grid; position ${state.position.join(',')}; goal ${state.goal?.join(',')}`);
    for (let row = 0; row < size; row++) for (let col = 0; col < size; col++) {
      const key = `${row},${col}`, classes = ['grid-cell'];
      if (walls.has(key)) classes.push('wall');
      if (trail.has(key)) classes.push('trail');
      if (state.goal?.join(',') === key) classes.push('goal');
      if (state.position.join(',') === key) classes.push('agent');
      const cell = node('div', classes.join(' '));
      cell.title = `Row ${row}, column ${col}`;
      cell.append(node('span', 'coord', `${row},${col}`));
      if (classes.includes('agent')) cell.append(node('span', '', '●'));
      else if (classes.includes('goal')) cell.append(node('span', '', '◎'));
      board.append(cell);
    }
    legend([['agent', 'Current position'], ['goal', 'Goal'], ['wall', 'Wall']]);
  } else if (game === 'tic_tac_toe' && ((typeof state.board === 'string' && state.board.length === 9) || Array.isArray(state.board))) {
    const cells = Array.isArray(state.board) ? state.board.flat() : [...state.board];
    const lines = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]];
    const winning = lines.find(([a, b, c]) => ['X', 'O'].includes(cells[a]) && cells[a] === cells[b] && cells[b] === cells[c]);
    const turn = winning ? `${cells[winning[0]]} has three in a row` : cells.every(value => value !== '.') ? 'Board full' : `Turn: ${state.player ?? 'Not recorded'}`;
    board.classList.add('ttt-board'); board.setAttribute('role', 'img'); board.setAttribute('aria-label', `Tic-tac-toe,${turn}; board ${cells.join('')}`);
    cells.slice(0, 9).forEach((value, index) => {
      const token = value === '.' || value == null ? '' : String(value);
      const chosen = currentStep()?.action === `cell_${index + 1}`;
      const cell = node('div', `ttt-cell ${token.toLowerCase()}${chosen ? ' chosen' : ''}`);
      if (winning?.includes(index)) cell.style.borderColor = 'var(--green)';
      cell.append(node('span', 'cell-index', index + 1), node('span', '', token)); board.append(cell);
    });
    legend([['agent', 'Gold outline: selected cell'], ['goal', turn]]);
  } else {
    board.classList.add('empty-board'); board.removeAttribute('role'); board.removeAttribute('aria-label');
    const pre = node('pre', 'state-preview', typeof state === 'string' ? state : json(state));
    pre.style.cssText = 'white-space:pre-wrap;overflow-wrap:anywhere;max-height:350px;overflow:auto;font-size:11px;max-width:100%;';
    board.append(pre);
  }
}

function probabilityEntries(value) {
  if (Array.isArray(value)) return value.map((item, i) => record(item)
    ? [String(item.id ?? item.candidate_id ?? item.label ?? i), item.probability ?? item.p ?? item.value]
    : [String(i), item]).filter(([, p]) => number(p));
  if (!record(value)) return [];
  return Object.entries(value).filter(([, p]) => number(p));
}
function answerProbabilities(answer) {
  if (!record(answer)) return null;
  if (answer.probabilities) return answer.probabilities;
  const p = answer.p_true ?? (answer.type === 'boolean' ? answer.probability ?? answer.value : undefined);
  return number(p) ? { false: 1 - p, true: p } : null;
}
function renderProbabilities(container, probabilities, selected) {
  const entries = probabilityEntries(probabilities);
  container.replaceChildren();
  if (!entries.length) { container.append(node('p', 'muted-copy', 'No probability vector was recorded for this step.')); return null; }
  const sum = entries.reduce((total, [, p]) => total + p, 0);
  const subset = entries.slice(0, 255);
  for (const [id, p] of subset) {
    const row = node('div', `probability-row${String(selected) === id ? ' selected' : ''}`);
    row.dataset.candidateId = id;
    const label = node('div', 'probability-label');
    label.append(node('span', 'label', actionName(id)), node('span', 'value', `${(p * 100).toFixed(2)}%`));
    const track = node('div', 'probability-track'), fill = node('div', 'probability-fill');
    fill.style.width = `${Math.min(1, Math.max(0, p)) * 100}%`;
    track.append(fill); row.append(label, track); container.append(row);
  }
  if (entries.length > 255) container.append(node('p', 'fine-print', `Showing the first 255 of ${entries.length} entries; the full values are in JSON.`));
  return sum;
}
function actionDistribution(step) {
  if (!step) return null;
  if (probabilityEntries(step.probabilities).length) return step.probabilities;
  const answers = step.answers?.answers ?? step.answers;
  if (!record(answers)) return null;
  const choices = Object.values(answers).filter(answer => answer?.type === 'choice');
  const match = choices.find(answer => own(answer.probabilities, step.action)) ?? choices[0];
  return match?.probabilities ?? null;
}
function addFact(container, key, value) {
  const item = node('div'); item.append(node('dt', '', key), node('dd', '', display(value))); container.append(item);
}
function renderStep() {
  const episode = selectedEpisode(), list = steps(), step = currentStep(), final = Boolean(episode) && ui.stepIndex >= list.length;
  renderBoard(visibleState());
  $('gameName').textContent = labels[episode?.game ?? visibleState()?.game] ?? episode?.game ?? 'Waiting for game records';
  $('splitLabel').textContent = episode ? `${labels[episode.split] ?? episode.split ?? 'Split unspecified'} · Replay${episode.outcome ? ` · ${labels[episode.outcome] ?? display(episode.outcome)}` : ''}` : 'Replay';
  $('stepLabel').textContent = !episode ? 'Not loaded' : final ? `Final state · ${list.length} steps` : `Before action · step ${ui.stepIndex + 1} / ${list.length}`;
  $('actionLabel').textContent = step ? `${step.actor ? `${labels[step.actor] ?? step.actor} · ` : ''}${actionName(step.action)}` : final ? 'End of trajectory' : '—';
  const outcome = episode?.outcome ?? episode?.result;
  $('episodeOutcome').textContent = episode ? labels[outcome] ?? display(outcome) : 'Not loaded';
  const mass = renderProbabilities($('actionProbabilities'), actionDistribution(step), step?.action);
  const warning = mass !== null && Math.abs(mass - 1) > 1e-5;
  const controller = step?.controller ?? selectedModel()?.controller ?? selectedModel()?.policy;
  $('probabilityNote').textContent = mass === null ? (final ? 'There is no next-action distribution at the final state.' : 'Missing probabilities are not replaced with one-hot or uniform values.')
    : warning ? `The recorded probabilities sum to ${mass.toPrecision(6)} and are displayed without renormalization. Action probabilities are not final win probabilities.`
      : controller === 'sample' ? 'Gold marks the sampled action, which may differ from argmax. The T=1 distribution is not a final win probability.' : 'Probabilities are shown as recorded. Action-policy probabilities are not final win probabilities.';
  $('probabilityNote').classList.toggle('warning', warning);
  $('distributionType').textContent = step?.forced ? 'Forced / environment action' : 'Recorded values';
  const facts = $('executionFacts'); facts.replaceChildren();
  addFact(facts, 'Record type', episode ? 'Saved replay' : 'No execution record');
  addFact(facts, 'Model forward', step ? own(step, 'model_forward') ? step.model_forward : 'Not recorded' : '—');
  addFact(facts, 'Forced action', step ? own(step, 'forced') ? step.forced : 'Not recorded' : '—');
  if (step && ['greedy', 'sample', 'random', 'oracle'].includes(controller)) addFact(facts, 'Controller', labels[controller]);
  if (step?.distribution_argmax !== undefined) addFact(facts, 'Distribution argmax', actionName(step.distribution_argmax));
  if (number(step?.sample_uniform_draw)) addFact(facts, 'Sampling draw', step.sample_uniform_draw);
  const execution = step?.execution ?? step?.model_forward;
  if (record(execution)) for (const key of ['forward_passes', 'precision', 'autoregressive_decode_steps', 'total_paths']) if (own(execution, key)) addFact(facts, key, execution[key]);
  const latency = step?.latency_ms ?? step?.model_latency_ms ?? step?.timing?.model_ms;
  if (number(latency)) addFact(facts, 'Step latency · ms', latency);
  if (step?.actor) addFact(facts, 'Actor', step.actor);
  $('rawStep').textContent = step ? json(step) : episode ? json({ final_state: visibleState(), outcome: episode.outcome, total_steps: list.length }) : 'Not loaded';
  $('stepSlider').max = String(list.length); $('stepSlider').value = String(ui.stepIndex); $('stepSlider').disabled = !list.length;
  $('previousButton').disabled = !episode || ui.stepIndex <= 0;
  $('nextButton').disabled = !episode || ui.stepIndex >= list.length;
  $('playButton').disabled = !list.length;
  if (!ui.batches.length) renderParallel();
}
function renderEpisodes() {
  const list = episodes();
  $('episodeSelect').replaceChildren(...(list.length ? list.map((episode, i) => option(i, `${episode.id ?? `Episode ${i + 1}`} · ${labels[episode.game] ?? episode.game ?? 'Game'} · ${episode.split ?? 'Split unspecified'}`)) : [option('', 'No game trajectories for this model')]));
  $('episodeSelect').disabled = !list.length; $('episodeSelect').value = list.length ? String(ui.episodeIndex) : '';
  renderStep();
}

function batchStates(batch) {
  if (Array.isArray(batch?.states)) return batch.states;
  if (Array.isArray(batch?.result?.states)) return batch.result.states;
  if (Array.isArray(batch?.response?.states)) return batch.response.states;
  return [];
}
function renderAnswers(container, states) {
  container.replaceChildren();
  for (const [index, state] of states.entries()) {
    const card = node('article', 'card state-card');
    card.append(node('h3', '', state.id ?? state.state_id ?? `State ${index + 1}`));
    if (state.state !== undefined) card.append(node('pre', 'state-preview', typeof state.state === 'string' ? state.state : json(state.state)));
    const answers = state.answers?.answers ?? state.answers;
    if (!record(answers) || !Object.keys(answers).length) card.append(node('p', 'muted-copy', 'No per-question answers were recorded for this state.'));
    else for (const [id, answer] of Object.entries(answers)) {
      const block = node('section', 'question-block'), heading = node('div', 'question-title');
      heading.append(node('span', '', id), node('span', 'pill muted', answer?.type ?? 'Type unspecified')); block.append(heading);
      const probabilities = node('div', 'probability-list');
      const selected = answer?.choice ?? (typeof answer?.value === 'string' ? answer.value : answer?.level);
      const mass = renderProbabilities(probabilities, answerProbabilities(answer), selected); block.append(probabilities);
      if (mass !== null && Math.abs(mass - 1) > 1e-5) block.append(node('p', 'fine-print warning', `Recorded sum ${mass.toPrecision(6)}; not normalized`));
      if (number(answer?.score)) block.append(node('p', 'question-summary', `Expected score: ${display(answer.score)}`));
      if (selected !== undefined) block.append(node('p', 'question-summary', `Selected: ${actionName(selected)}`));
      card.append(block);
    }
    container.append(card);
  }
}
function collectBatches() {
  const model = selectedModel();
  const candidates = model?.parallel_batches ?? ui.data?.parallel_batches ?? ui.data?.batch_examples ?? [];
  ui.batches = (Array.isArray(candidates) ? candidates : [candidates]).filter(batch => !batch.model || !model || batch.model === model.name || batch.model === model.id);
  ui.batchIndex = Math.min(ui.batchIndex, Math.max(0, ui.batches.length - 1));
  $('batchSelect').replaceChildren(...(ui.batches.length ? ui.batches.map((batch, index) => option(index, batch.id ?? `Batch ${index + 1}`)) : [option('', 'Current step · multiple questions, one state')]));
  $('batchSelect').value = ui.batches.length ? String(ui.batchIndex) : ''; $('batchSelect').disabled = !ui.batches.length;
}
function renderParallel() {
  const batch = ui.batches[ui.batchIndex];
  if (batch) {
    const states = batchStates(batch), execution = batch.execution ?? batch.result?.execution ?? batch.response?.execution;
    const measured = record(execution) && own(execution, 'forward_passes');
    $('batchEvidence').textContent = `${states.length} states from the same saved batch. ${measured ? `Execution record: ${execution.forward_passes} forward pass(es), ${execution.precision ?? 'precision unspecified'}. ` : 'The forward count was not recorded. '}${states.length < 2 ? 'This record does not demonstrate multi-state batching.' : ''}`;
    renderAnswers($('parallelStates'), states); $('rawBatch').textContent = json(batch);
    if (!states.length) empty($('parallelStates'), 'No readable states in this batch', 'See the raw JSON for the full record.');
  } else {
    const step = currentStep();
    $('batchEvidence').textContent = 'These are multiple answers for the current replay state. No multi-state batch was recorded; separate steps are not combined into one batch.';
    if (step?.answers) {
      renderAnswers($('parallelStates'), [{ id: selectedEpisode()?.id ?? 'Current state', state: step.state, answers: step.answers }]);
      $('rawBatch').textContent = json({ kind: 'single_state_step_not_multistate_batch', state: step.state, answers: step.answers });
    } else {
      empty($('parallelStates'), 'Waiting for parallel inference records', 'Results can provide parallel_batches or per-step answers.'); $('rawBatch').textContent = 'No batch record';
    }
  }
}
function changeModel() {
  stopPlayback(); ui.episodeIndex = 0; ui.stepIndex = 0; ui.batchIndex = 0;
  renderSummary(); collectBatches(); renderEpisodes(); renderParallel();
}

async function loadData() {
  stopPlayback(); $('reloadButton').disabled = true; notice('');
  try {
    const response = await fetch('./demo_results.json', { cache: 'no-store' });
    if (!response.ok) throw new Error(response.status === 404 ? 'missing' : `HTTP ${response.status}`);
    const data = await response.json();
    if (!record(data) || !Array.isArray(data.models)) throw new Error('schema');
    if (data.models.some(model => !record(model) || (model.episodes !== undefined && !Array.isArray(model.episodes)))) throw new Error('schema');
    const previousIdentity = modelIdentity(selectedModel());
    ui.data = data; ui.models = data.models;
    const previousIndex = ui.models.findIndex(model => modelIdentity(model) === previousIdentity);
    // Use the predefined primary arm without reading scores. Preserve the user selection on reload.
    const primaryIndex = ui.models.findIndex(model => [model.name, model.source_artifact].some(value => String(value ?? '').includes('v3_gold_coords_multi_seed17')) && (model.controller ?? model.policy) === 'greedy');
    ui.modelIndex = previousIndex >= 0 ? previousIndex : primaryIndex >= 0 ? primaryIndex : 0;
    $('modelSelect').replaceChildren(...(ui.models.length ? ui.models.map((model, i) => option(i, modelLabel(model, i))) : [option('', 'No models in the results file')]));
    $('modelSelect').disabled = !ui.models.length; $('modelSelect').value = String(ui.modelIndex);
    $('dataStatus').className = `status-chip${ui.models.length ? ' ready' : ''}`;
    $('dataStatus').lastElementChild.textContent = ui.models.length ? `Loaded ${ui.models.length} models / baselines` : 'Results file is empty';
    $('artifactMeta').textContent = data.generated_at ? `Results generated at ${data.generated_at}` : 'Data: local demo_results.json';
    if (!ui.models.length) notice('No model records are available. The page does not insert simulated successes.');
    if (data.notes) notice(Array.isArray(data.notes) ? data.notes.join('\n') : String(data.notes));
    renderSources(); changeModel();
  } catch (error) {
    ui.data = null; ui.models = []; ui.modelIndex = 0;
    $('modelSelect').replaceChildren(option('', 'Waiting for experiment data')); $('modelSelect').disabled = true;
    $('dataStatus').className = 'status-chip error'; $('dataStatus').lastElementChild.textContent = 'Experiment records not loaded';
    const message = location.protocol === 'file:' ? 'Open this page through an HTTP server. Browsers cannot load the results JSON from file://.'
      : error.message === 'schema' ? 'The results JSON does not match the models / episodes schema. Check the data file; no simulated results are shown.'
        : error.message === 'missing' ? 'demo_results.json was not found. Put recorded results in the web directory, then select Reload records.'
          : 'Cannot read or parse demo_results.json. Check the local server and results file; no teacher API was called.';
    notice(message); renderSources(); changeModel();
  } finally { $('reloadButton').disabled = false; }
}

function setStep(value) { ui.stepIndex = Math.max(0, Math.min(steps().length, value)); renderStep(); }
function togglePlayback() {
  if (ui.timer !== null) { stopPlayback(); return; }
  if (!steps().length) return;
  if (ui.stepIndex >= steps().length) setStep(0);
  $('playButton').textContent = 'Pause';
  ui.timer = setInterval(() => { setStep(ui.stepIndex + 1); if (ui.stepIndex >= steps().length) stopPlayback(); }, Number($('speedSelect').value));
}

$('reloadButton').addEventListener('click', loadData);
$('modelSelect').addEventListener('change', event => { ui.modelIndex = Number(event.target.value); changeModel(); });
$('episodeSelect').addEventListener('change', event => { stopPlayback(); ui.episodeIndex = Number(event.target.value); ui.stepIndex = 0; renderStep(); renderParallel(); });
$('previousButton').addEventListener('click', () => { stopPlayback(); setStep(ui.stepIndex - 1); });
$('nextButton').addEventListener('click', () => { stopPlayback(); setStep(ui.stepIndex + 1); });
$('stepSlider').addEventListener('input', event => { stopPlayback(); setStep(Number(event.target.value)); });
$('playButton').addEventListener('click', togglePlayback);
$('speedSelect').addEventListener('change', () => { if (ui.timer !== null) { stopPlayback(); togglePlayback(); } });
$('batchSelect').addEventListener('change', event => { ui.batchIndex = Number(event.target.value); renderParallel(); });
document.querySelectorAll('.tab').forEach(tab => tab.addEventListener('click', () => {
  stopPlayback();
  document.querySelectorAll('.tab').forEach(item => { const active = item === tab; item.classList.toggle('active', active); item.setAttribute('aria-pressed', String(active)); $(item.dataset.panel).hidden = !active; });
  if (tab.dataset.panel === 'parallelPanel') renderParallel();
}));
document.addEventListener('visibilitychange', () => { if (document.hidden) stopPlayback(); });

$('liveForm').addEventListener('submit', async event => {
  event.preventDefault();
  const status = $('liveStatus'); status.classList.remove('error');
  let request;
  try { request = JSON.parse($('liveInput').value); if (!record(request)) throw new Error('object_required'); }
  catch { status.textContent = 'The request must be a valid JSON object. Nothing was sent.'; status.classList.add('error'); return; }
  if (location.protocol === 'file:') { status.textContent = 'Start an HTTP model service before using the live endpoint.'; status.classList.add('error'); return; }
  $('evaluateButton').disabled = true; status.textContent = 'Waiting for local model inference…';
  $('liveAnswers').replaceChildren(node('p', 'muted-copy', 'Waiting for this request’s actual result…'));
  $('liveRaw').textContent = 'No response to this request yet'; $('liveLatency').textContent = 'Running';
  const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 120000), started = performance.now();
  try {
    const response = await fetch('/api/evaluate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request), signal: controller.signal });
    if ([404, 405, 501].includes(response.status)) throw new Error('service_missing');
    const text = await response.text();
    let result; try { result = JSON.parse(text); } catch { throw new Error('non_json_response'); }
    $('liveRaw').textContent = json(result);
    if (!response.ok) throw new Error(`http_${response.status}`);
    const elapsed = performance.now() - started;
    $('liveLatency').textContent = `${elapsed.toFixed(0)} ms · Browser round trip`;
    const states = Array.isArray(result.states) ? result.states : Array.isArray(result.result?.states) ? result.result.states
      : record(result.answers) ? [{ id: 'Response', answers: result.answers }] : [];
    if (states.length) renderAnswers($('liveAnswers'), states);
    else $('liveAnswers').replaceChildren(node('p', 'muted-copy', 'The service returned JSON with a structure not supported by this view. See the full response.'));
    status.textContent = 'Request complete. Round-trip time includes network and service processing, not just GPU compute.';
  } catch (error) {
    status.classList.add('error');
    status.textContent = error.message === 'service_missing' ? 'This server provides static pages only. Start a model service that supports POST /api/evaluate.'
      : error.name === 'AbortError' ? 'The browser canceled the request after 120 seconds. Check server logs to see whether processing continues.'
        : error.message === 'non_json_response' ? 'The service did not return JSON. Check that the request reaches the model service.'
          : error.message.startsWith('http_') ? `The service returned HTTP ${error.message.slice(5)}. See the response JSON.` : 'The live request did not complete. Check the local model service; no preset answer was used.';
    $('liveLatency').textContent = 'Request incomplete';
  } finally { clearTimeout(timeout); $('evaluateButton').disabled = false; }
});

renderSources();
loadData();
