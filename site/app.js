'use strict';
let study;
const $ = id => document.getElementById(id);
const names = {clear:'4 certain deaths vs 1',close:'2 certain deaths vs 1',equal_expected:'1 certain death vs 20% chance of 5',lower_expected_risk:'1 certain death vs 10% chance of 5'};
const conditionNames = {standard:'Standard',symmetric_restatement:'Restate both options first'};
function node(tag, text, className) {
  const result = document.createElement(tag);
  if (text !== undefined) result.textContent = text;
  if (className) result.className = className;
  return result;
}
function cell(frame) {
  return study.cells.find(row => row.scenario_id === $('scenario').value && row.condition === $('condition').value && row.frame === frame);
}
function outcomeText(rows) {
  return rows.map(row => `${100*row.probability}%: ${row.deaths} die, ${row.survivors} survive`).join('; ');
}
function showTrial(parent, trial) {
  parent.append(node('p',`Repeat ${trial.repeat}: ${trial.status === 'valid' ? trial.choice.toUpperCase() : trial.status.toUpperCase()}`));
  if (trial.justification) parent.append(node('blockquote',trial.justification));
  if (trial.status === 'invalid') parent.append(node('p',trial.raw_answer));
}
function renderCase() {
  const scenario = study.protocol.scenarios.find(row => row.id === $('scenario').value);
  $('scenario-facts').replaceChildren(node('h3','The fixed consequences'),node('p','Each dot represents one of the ten people. Red = dies; green = survives.','note'));
  const actions = node('div',undefined,'cards');
  for (const action of ['stay','swerve']) {
    const column = node('div');
    column.append(node('h3',action.toUpperCase()));
    for (const outcome of scenario[action]) {
      const row = node('div');
      row.append(node('p',`${100*outcome.probability}% probability: ${outcome.deaths} die, ${outcome.survivors} survive`));
      const dots = node('div',undefined,'people');
      dots.setAttribute('aria-hidden','true');
      for (let index=0; index<10; index++) dots.append(node('span','●',index<outcome.deaths?'dies':'survives'));
      row.append(dots);
      column.append(row);
    }
    actions.append(column);
  }
  $('scenario-facts').append(actions);
  $('neutral-prompt').textContent = cell('neutral').prompt;
  $('reframed-prompt').textContent = cell($('frame').value).prompt;
  $('original-answer').replaceChildren();
  showTrial($('original-answer'),cell('neutral').trials[0]);
  $('reveal').hidden = true;
  $('reveal').replaceChildren();
  const available = cell('neutral').trials[0].status === 'valid' && cell($('frame').value).trials[0].status === 'valid';
  $('same').disabled = !available;
  $('different').disabled = !available;
  $('trial-details').replaceChildren();
  for (const frame of ['neutral','survival_first','death_first']) {
    const article = node('article');
    article.append(node('h3',frame.replaceAll('_',' ')));
    for (const trial of cell(frame).trials) showTrial(article,trial);
    $('trial-details').append(article);
  }
}
function reveal(guess) {
  const first = cell('neutral').trials[0];
  const next = cell($('frame').value).trials[0];
  const actual = first.choice === next.choice ? 'same' : 'different';
  $('reveal').replaceChildren(node('h3',actual === 'same' ? 'The action stayed the same.' : 'The action changed.'),node('p',guess === actual ? 'Your prediction matched this recorded response.' : 'Your prediction did not match this recorded response.'));
  showTrial($('reveal'),next);
  $('reveal').append(node('p','This one pair is an illustration. Use the repeated-prompt comparison below to assess the broader pattern.','note'));
  $('reveal').hidden = false;
}
function percent(value) {return value === null ? 'Not yet available' : `${(100*value).toFixed(1)}%`;}
function gap(value) {return value === null ? 'Not yet available' : `${(100*value).toFixed(1)} pp`;}
function renderResults() {
  const count = study.counts;
  const standard = study.conditions.standard;
  if (count.missing === 0 && count.invalid === 0) {
    $('finding').textContent = standard.gap <= 0
      ? 'Across this bank, equivalent descriptions did not disagree more than identical-prompt repeats. A changed response alone would overstate the evidence for a framing effect. Inspect the risk cases and both instruction conditions below.'
      : 'Across this bank, equivalent descriptions disagreed more often than identical-prompt repeats. This is a descriptive result for these scenarios, not proof of a general framing effect. Inspect individual scenarios and the intervention below.';
  } else {
    $('finding').textContent = 'Collection is incomplete. The comparison below uses only complete scenario-conditions; wait for the full bank before drawing conclusions.';
  }
  $('status').textContent = `${count.valid} valid · ${count.invalid} invalid · ${count.missing} missing / 240 planned responses · model: ${study.protocol.model}`;
  for (const [condition, metric] of Object.entries(study.conditions)) {
    const article = node('article',undefined,'card');
    article.append(node('h3',conditionNames[condition]),node('p',gap(metric.gap),'metric'),node('p','excess cross-description disagreement'),node('p',`Same prompt: ${percent(metric.within)}. Different descriptions: ${percent(metric.cross)}.`),node('p',`${metric.complete_scenarios}/8 complete scenarios.`,'note'));
    if (metric.cross !== null) {
      for (const [label,value] of [['Same prompt',metric.within],['Different descriptions',metric.cross]]) {
        const plot = node('div',undefined,'bar-row');
        plot.append(node('p',`${label}: ${percent(value)}`));
        const track = node('div',undefined,'bar-track');
        const fill = node('div',undefined,'bar-fill');
        fill.style.width = `${100*value}%`;
        track.append(fill);
        plot.append(track);
        article.append(plot);
      }
    }
    $('metrics').append(article);
  }
  const mixed = [...study.cells].sort((a,b)=>a.id.localeCompare(b.id)).find(row => row.condition === 'standard' && row.trials.some(trial => trial.choice === 'stay') && row.trials.some(trial => trial.choice === 'swerve'));
  if (mixed) {
    $('reason-contrast').append(node('p',`${mixed.scenario_id} · ${mixed.frame.replaceAll('_',' ')} · identical prompt`),node('p',mixed.prompt,'note'));
    for (const action of ['stay','swerve']) showTrial($('reason-contrast'),mixed.trials.find(trial=>trial.choice===action));
    $('reason-contrast').append(node('p','Both explanations may support different risk preferences. Their coexistence shows that one explanation need not reliably predict the next answer. This does not establish internal unfaithfulness.','note'));
  } else {
    $('reason-contrast').append(node('p','No standard-condition prompt currently has valid recorded examples of both actions.'));
  }
  for (const row of study.metrics) {
    const tr = node('tr');
    for (const text of [row.scenario_id,conditionNames[row.condition],percent(row.measurement?.within ?? null),percent(row.measurement?.cross ?? null),gap(row.measurement?.gap ?? null)]) tr.append(node('td',text));
    $('metric-rows').append(tr);
  }
}
async function start() {
  try {
    const response = await fetch('data/study.json');
    if (!response.ok) throw new Error(`Data request failed: ${response.status}`);
    study = await response.json();
    for (const row of study.protocol.scenarios) {
      const option = node('option',`${names[row.family]} · ${row.id.endsWith('mirrored') ? 'actions reversed' : 'original orientation'}`);
      option.value = row.id;
      $('scenario').append(option);
    }
    for (const id of ['scenario','condition','frame']) $(id).addEventListener('change',renderCase);
    $('same').addEventListener('click',()=>reveal('same'));
    $('different').addEventListener('click',()=>reveal('different'));
    renderCase();
    renderResults();
  } catch (error) {
    $('status').textContent = `Could not load study evidence: ${error.message}. Serve this site over HTTP using the README instructions.`;
    $('same').disabled = true;
    $('different').disabled = true;
  }
}
start();
