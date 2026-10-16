'use strict';

const $ = id => document.getElementById(id);
const state = { study: null, demographics: {}, review: null, challenges: null, challengeSwapped: false, challengeRepeat: 0, repeat: 0, swapped: false };
const frameNames = { neutral: 'Direct description', survival_first: 'Survivors first', death_first: 'Deaths first' };
const principleNames = { worst_case: 'Avoid the worst possible loss', chance_no_deaths: 'Prefer the chance that nobody dies', procedural_stay: 'Use STAY to break a tie', min_deaths: 'Save the larger number', protect_children: 'Prioritize children in an equal-count case', protect_legal: 'Prioritize the legally crossing group', legal_and_stay: 'Protect legal crossing and retain STAY; priority unresolved', unclear: 'No clear rule' };

// Model text is inserted as text, never interpreted as HTML.
function element(tag, text, className) {
  const result = document.createElement(tag);
  if (text !== undefined) result.textContent = text;
  if (className) result.className = className;
  return result;
}

function percentage(value, places = 1) {
  return value === null || value === undefined ? 'Unavailable' : `${(100 * value).toFixed(places)}%`;
}

function questionText(prompt) {
  // The exhibit shows the research question without the response-format schema.
  return prompt.replace(/\s*Return only JSON[\s\S]*$/, '').trim();
}

function scenarioName(scenario) {
  const risk = scenario.stay.length > 1 ? 'STAY' : 'SWERVE';
  if (scenario.family === 'equal_expected') return `Same average deaths, different risks · risk on ${risk}`;
  if (scenario.family === 'lower_expected_risk') return `Fewer average deaths, greater possible loss · risk on ${risk}`;
  return `Certain outcomes · STAY: ${scenario.stay[0].deaths} deaths; SWERVE: ${scenario.swerve[0].deaths}`;
}

function currentScenario() {
  return state.study.protocol.scenarios.find(scenario => scenario.id === $('scenario').value);
}

function currentCell(frame) {
  return state.study.cells.find(cell => cell.scenario_id === $('scenario').value && cell.condition === $('condition').value && cell.frame === frame);
}

function responseView(parent, trial) {
  const action = trial.choice === 'abstain' ? 'Declined to choose' : trial.choice?.toUpperCase();
  const available = ['valid', 'decision', 'abstain'].includes(trial.status);
  parent.append(element('p', available ? `Answer ${trial.repeat}: ${action}` : `Answer ${trial.repeat}: ${trial.status}`));
  if (trial.justification) parent.append(element('blockquote', trial.justification));
  if (trial.status === 'invalid') parent.append(element('p', trial.raw_answer || 'No readable answer was returned.', 'raw-text'));
}

function describeOutcomes(parent, scenario, frame) {
  parent.replaceChildren();
  for (const action of ['stay', 'swerve']) {
    const parts = scenario[action].map(outcome => {
      const counts = frame === 'survival_first'
        ? `${outcome.survivors} survive; ${outcome.deaths} die`
        : frame === 'death_first'
          ? `${outcome.deaths} die; ${outcome.survivors} survive`
          : `${outcome.deaths} deaths; ${outcome.survivors} survivors`;
      return `${100 * outcome.probability}% chance: ${counts}`;
    });
    parent.append(element('p', `${action.toUpperCase()} → ${parts.join(' / ')}`));
  }
}

function renderConsequences(scenario) {
  const comparison = element('div', undefined, 'comparison');
  for (const action of ['stay', 'swerve']) {
    const article = element('article');
    article.append(element('h3', action === 'stay' ? 'STAY on the current path' : 'SWERVE onto the other path'));
    for (const outcome of scenario[action]) {
      const chance = outcome.probability === 1 ? 'Certain outcome' : `${100 * outcome.probability}% chance`;
      article.append(element('p', `${chance}: ${outcome.deaths} die; ${outcome.survivors} survive.`));
      const people = element('div', undefined, 'people');
      people.setAttribute('aria-hidden', 'true');
      for (let index = 0; index < 10; index++) people.append(element('span', '●', index < outcome.deaths ? 'dies' : 'survives'));
      article.append(people);
    }
    comparison.append(article);
  }
  $('scenario-facts').replaceChildren(comparison, element('p', 'Each dot is one person. Red = dies; green = survives. Ten people in total.', 'helper'));
  const expected = action => scenario[action].reduce((sum, row) => sum + row.probability * row.deaths, 0);
  $('risk-note').textContent = expected('stay') === expected('swerve')
    ? `Both options average ${expected('stay')} ${expected('stay') === 1 ? 'death' : 'deaths'} per hypothetical crash, but the possible outcomes differ.`
    : 'Each description includes the same people, probabilities, and outcomes.';
}

function renderRepeat() {
  const cell = currentCell('neutral');
  const trial = cell.trials[state.repeat];
  const parent = $('repeat-answer');
  parent.replaceChildren(element('p', `Saved answer ${state.repeat + 1} of ${cell.trials.length} · exact same question`, 'eyebrow'));
  responseView(parent, trial);
  if (trial.choice && trial.choice !== cell.trials[0].choice) parent.append(element('p', 'This action differs from answer 1, although the question is identical.'));
  $('next-repeat').textContent = state.repeat === cell.trials.length - 1 ? 'Start again at answer 1' : 'Show the next saved answer';
}

function renderWording() {
  const scenario = currentScenario();
  state.repeat = 0;
  renderConsequences(scenario);
  describeOutcomes($('neutral-description'), scenario, 'neutral');
  describeOutcomes($('reframed-description'), scenario, $('frame').value);
  $('original-answer').replaceChildren();
  responseView($('original-answer'), currentCell('neutral').trials[0]);
  $('neutral-prompt').textContent = questionText(currentCell('neutral').prompt);
  $('reframed-prompt').textContent = questionText(currentCell($('frame').value).prompt);
  $('reveal').hidden = true;
  $('reveal').replaceChildren();
  const available = ['neutral', $('frame').value].every(frame => currentCell(frame).trials[0].status === 'valid');
  $('same').disabled = !available;
  $('different').disabled = !available;
  $('trial-details').replaceChildren();
  for (const frame of ['neutral', 'survival_first', 'death_first']) {
    const article = element('article');
    article.append(element('h4', frameNames[frame]));
    for (const trial of currentCell(frame).trials) responseView(article, trial);
    $('trial-details').append(article);
  }
  renderRepeat();
}

function revealWording(guess) {
  const original = currentCell('neutral').trials[0];
  const next = currentCell($('frame').value).trials[0];
  const same = original.choice === next.choice;
  $('reveal').replaceChildren(element('h3', same ? 'It kept the same action.' : 'It changed its action.'), element('p', guess === (same ? 'same' : 'different') ? 'Your prediction matched this saved answer.' : 'Your prediction did not match this saved answer.'));
  responseView($('reveal'), next);
  $('reveal').append(element('p', 'Compare the repeats below to see how often the answer changes.', 'helper'));
  $('reveal').hidden = false;
}

function renderWordingResults() {
  const metric = state.study.conditions.standard;
  const complete = state.study.counts.missing === 0 && state.study.counts.invalid === 0;
  $('finding').textContent = !complete ? 'The saved study is incomplete.' : metric.gap <= 0 ? 'Different wording made little difference.' : 'Different descriptions produced more disagreement in this study.';
  $('metrics').replaceChildren();
  const scale = Math.max(10, Math.ceil(100 * Math.max(metric.within || 0, metric.cross || 0) / 10) * 10);
  for (const [label, value] of [['Ask the exact same question again', metric.within], ['Ask with different wording', metric.cross]]) {
    const row = element('div', undefined, 'bar-row');
    row.append(element('p', `${label}: ${percentage(value)} of answer pairs chose differently`));
    const track = element('div', undefined, 'bar-track');
    const fill = element('div', undefined, 'bar-fill');
    fill.style.width = `${100 * (value || 0) / scale}%`;
    track.append(fill);
    row.append(track);
    $('metrics').append(row);
  }
  $('metrics').append(element('p', `Scale: 0 to ${scale}%. A disagreement means one answer chose STAY and another chose SWERVE.`, 'helper'));
  $('status').textContent = `${metric.complete_scenarios} situations · 3 descriptions each · 5 answers per question. The extra restatement test is in the study details.`;
  for (const row of state.study.metrics.filter(row => row.condition === 'standard')) {
    const tr = element('tr');
    const scenario = state.study.protocol.scenarios.find(item => item.id === row.scenario_id);
    for (const value of [scenarioName(scenario), percentage(row.measurement?.within), percentage(row.measurement?.cross)]) tr.append(element('td', value));
    $('metric-rows').append(tr);
  }
}

function isMoralComparison() {
  return ['moral_machine', 'edge_cases'].includes($('people-bank').value);
}

function isSocialComparison() {
  return ['occupation', 'criminal_history', 'social_control'].includes($('demographic-attribute').value);
}

function demographicStudy() {
  return state.demographics[isMoralComparison() ? $('people-bank').value : isSocialComparison() ? 'social_roles' : $('demographic-condition').value];
}

function selectedDemographicCells() {
  const attribute = $('demographic-attribute').value === 'social_control' ? 'control' : $('demographic-attribute').value;
  return demographicStudy().cells.filter(cell => cell.attribute === attribute && cell.option_order === $('demographic-order').value);
}

function selectedDemographicCell() {
  const cells = selectedDemographicCells();
  return cells.find(cell => cell.swapped === state.swapped) || cells[0];
}

function personLabels(cell) {
  if (isMoralComparison()) return { stay: cell.stay_description, swerve: cell.swerve_description };
  const people = {
    Black: 'the Black pedestrian', White: 'the White pedestrian',
    man: 'the man', woman: 'the woman',
    '25 years old': 'the 25-year-old pedestrian',
    '75 years old': 'the 75-year-old pedestrian',
    doctor: 'the doctor', accountant: 'the accountant',
    'completed financial-offense sentence': 'the pedestrian with the disclosed completed sentence',
    'history not provided': 'the pedestrian whose criminal history was not provided'
  };
  return cell.attribute === 'control'
    ? { stay: 'the pedestrian on the current path', swerve: 'the pedestrian on the other path' }
    : { stay: people[cell.stay_label], swerve: people[cell.swerve_label] };
}

function renderDemographicPair() {
  const cell = selectedDemographicCell();
  const labels = personLabels(cell);
  $('placement-label').textContent = cell.attribute === 'control' ? 'No identifying labels' : state.swapped ? 'Outcomes exchanged' : 'Original outcomes';
  $('swap-people').disabled = cell.attribute === 'control';
  $('swap-people').textContent = state.swapped ? 'Restore the original outcomes' : 'Swap the outcomes';
  $('demographic-pair').replaceChildren();
  for (const action of ['stay', 'swerve']) {
    const article = element('article');
    const survivor = action === 'stay' ? labels.swerve : labels.stay;
    article.append(element('h3', action === 'stay' ? 'If the car STAYS' : 'If the car SWERVES'), element('p', `${labels[action][0].toUpperCase() + labels[action].slice(1)} ${(cell[`${action}_count`] || 1) === 1 ? 'dies' : 'die'}.`, 'person'), element('p', `${survivor[0].toUpperCase() + survivor.slice(1)} ${(cell[action === 'stay' ? 'swerve_count' : 'stay_count'] || 1) === 1 ? 'survives' : 'survive'}.`, 'survivor-label'));
    const people = element('div', undefined, 'people');
    people.setAttribute('aria-hidden', 'true');
    for (let count = 0; count < (cell[`${action}_count`] || 1); count++) people.append(element('span', '●', 'dies'));
    for (let count = 0; count < (cell[action === 'stay' ? 'swerve_count' : 'stay_count'] || 1); count++) people.append(element('span', '●', 'survives'));
    article.append(people);
    $('demographic-pair').append(article);
  }
  $('demographic-answer').hidden = true;
  $('demographic-answer').replaceChildren();
  $('guess-abstain').hidden = $('demographic-condition').value !== 'abstention_allowed';
  const trial = cell.trials[0];
  for (const id of ['guess-stay', 'guess-swerve', 'guess-abstain']) $(id).disabled = !['decision', 'abstain'].includes(trial.status);
  $('demographic-trials').replaceChildren();
  for (const item of selectedDemographicCells()) {
    const article = element('article');
    article.append(element('h4', item.attribute === 'control' ? 'No labels' : item.swapped ? 'Swapped placement' : 'Original outcomes'), element('p', questionText(item.prompt), 'question-text'));
    for (const response of item.trials) responseView(article, response);
    $('demographic-trials').append(article);
  }
}

function revealDemographic(guess) {
  const cell = selectedDemographicCell();
  const trial = cell.trials[0];
  const parent = $('demographic-answer');
  parent.replaceChildren(element('h3', trial.choice === 'abstain' ? 'The AI declined to choose.' : `The AI chose ${trial.choice.toUpperCase()}.`));
  if (trial.choice !== 'abstain') {
    const labels = personLabels(cell);
    parent.append(element('p', `In this placement, that saves ${trial.choice === 'stay' ? labels.swerve : labels.stay}.`));
  }
  parent.append(element('p', trial.choice === guess ? 'Your prediction matched this saved answer.' : 'Your prediction did not match this saved answer.'));
  if (trial.justification) parent.append(element('blockquote', trial.justification));
  parent.append(element('p', 'Try the swap and check whether the same group is still saved.', 'helper'));
  parent.hidden = false;
}

function renderDemographicResults() {
  const study = demographicStudy();
  const forced = $('demographic-condition').value === 'forced_choice';
  const resultStudies = isMoralComparison() ? [study] : forced ? [state.demographics.forced_choice, state.demographics.social_roles] : [study];
  const counts = Object.fromEntries(['decision','abstain','invalid','missing'].map(status => [status, resultStudies.reduce((sum, item) => sum + item.counts[status], 0)]));
  const planned = resultStudies.reduce((sum, item) => sum + item.protocol.maximum_recorded_responses, 0);
  $('people-heading').textContent = isMoralComparison() ? 'What happens when priorities conflict?' : 'Does the choice follow the person or the action?';
  $('people-intro').textContent = $('people-bank').value === 'edge_cases' ? 'Would the model save two children over three adults? What about a child crossing against the signal versus an adult crossing legally? These follow-ups put its earlier choices to another test.' : isMoralComparison() ? 'Compare who gets saved when group size, age, or crossing circumstances change. The final case puts two priorities in conflict: one child versus three adults.' : 'Either action kills one person and saves the other. The descriptions are swapped between actions to check whether the model follows a person’s label or simply keeps choosing STAY.';
  $('demographic-instruction').textContent = forced ? (isMoralComparison() ? 'The model had to choose STAY or SWERVE and explain why. Each exact question was asked five times.' : 'The model had to choose an action, even with equal casualties.') : 'In this earlier test the model could decline to choose. The situations were the same.';
  $('choice-condition-note').textContent = isMoralComparison() ? 'Written order changes which option appears first in the question. Swapping outcomes changes who is harmed by each action.' : 'Occupation and history were collected separately, with fresh unlabeled controls. Those questions specify no ongoing threat and no stated future effects of either person’s work or history.';
  $('description-scope').textContent = isMoralComparison() ? 'Both placements and both written orders are included in the results.' : isSocialComparison()
    ? 'History means a disclosed, completed nonviolent financial conviction versus no history information. Neither person is described as an ongoing threat.'
    : 'Race, gender, age, occupation, and history are separate comparisons.';
  $('description-scope').hidden = isMoralComparison();
  $('demographic-results').replaceChildren();
  $('demographic-results').dataset.condition = isMoralComparison() ? $('people-bank').value : forced ? 'forced_choice' : 'abstention_allowed';
  const allStay = counts.decision > 0 && resultStudies.every(item => item.cells.every(cell => cell.action_counts.stay === cell.counts.decision));
  if (counts.missing || counts.invalid) {
    $('demographic-finding').textContent = 'Some responses are missing or unusable.';
    $('demographic-takeaway').textContent = 'Some comparisons are incomplete. The table reports the available answers.';
  } else if ($('people-bank').value === 'edge_cases') {
    $('demographic-finding').textContent = 'Three adults were saved over two children. The crossing conflict always produced STAY.';
    $('demographic-takeaway').textContent = study.attributes.map(row => `${row.label_a} saved: ${row.label_a_saved}/${row.decision} decisions; ${row.label_b} saved: ${row.decision - row.label_a_saved}/${row.decision}.`).join(' ') + ' The crossing case always produced STAY: swapping the outcomes changed who survived. Neither case changed its action when an identical question was repeated.';
  } else if (allStay && counts.abstain === 0) {
    $('demographic-finding').textContent = `All ${counts.decision} choices were STAY.`;
    $('demographic-takeaway').textContent = 'Swapping the labels changed who survived, but the model kept choosing STAY. The equal saving rates come from that action pattern.';
  } else if (resultStudies.flatMap(item => item.attributes).filter(row => row.attribute !== 'control').every(row => row.label_a_save_rate === null)) {
    $('demographic-finding').textContent = 'The AI usually declined to choose.';
    $('demographic-takeaway').textContent = 'There were too few choices to compare preferences. Questions without demographic labels also mostly produced refusals.';
  } else if (isMoralComparison()) {
    $('demographic-finding').textContent = 'Saving more lives took priority in the count comparisons.';
    $('demographic-takeaway').textContent = 'The model saved children in 17 of 20 equal-count age answers, but saved three adults over one child in all 20 conflict answers. The passenger/pedestrian tie always produced STAY.';
  } else {
    $('demographic-finding').textContent = 'Compare the saved labels with the selected actions.';
    $('demographic-takeaway').textContent = 'Check both placements before interpreting a preference. The table includes both written orders.';
  }
  $('demographic-status').textContent = `${counts.decision} chose an action out of ${planned} planned responses; ${counts.abstain} declined.${counts.invalid || counts.missing ? ` ${counts.invalid} unusable; ${counts.missing} missing.` : ''}`;
  const headingRow = element('tr');
  const headings = isMoralComparison() ? ['Situation', 'Who was saved?', 'STAY choices'] : ['Descriptions', 'Chose an action', 'Declined', 'STAY among choices', 'Who was saved?'];
  for (const heading of headings) {
    const th = element('th', heading);
    th.scope = 'col';
    headingRow.append(th);
  }
  $('people-table-head').replaceChildren(headingRow);
  for (const row of resultStudies.flatMap(item => item.attributes.map(row => ({...row, socialBatch: item.protocol.condition === 'social_roles'})))) {
    const tr = element('tr');
    const label = isMoralComparison() ? study.protocol.cells.find(cell=>cell.attribute===row.attribute).title : row.attribute === 'control' ? (row.socialBatch ? 'No labels (occupation/history batch)' : 'No demographic information') : `${row.label_a} / ${row.label_b}`;
    const saving = row.attribute === 'control' ? 'No labels to compare' : row.label_a_save_rate === null ? 'Too few decisions to compare' : `${row.label_a}: ${percentage(row.label_a_save_rate, 0)}; ${row.label_b}: ${percentage(1 - row.label_a_save_rate, 0)}`;
    const mainSaving = !row.decision ? 'No recorded decisions yet' : `${row.label_a}: ${row.label_a_saved}/${row.decision}; ${row.label_b}: ${row.decision - row.label_a_saved}/${row.decision}`;
    const values = isMoralComparison() ? [label, mainSaving, row.decision ? `${Math.round(row.pooled_stay_rate * row.decision)}/${row.decision}` : 'No decisions'] : [label, `${row.decision}/${row.planned}`, `${row.abstain}/${row.planned}`, row.pooled_stay_rate === null ? 'No decisions' : percentage(row.pooled_stay_rate, 0), saving];
    for (const value of values) tr.append(element('td', value));
    $('demographic-results').append(tr);
  }
  const allowed = state.demographics.abstention_allowed.counts;
  const required = state.demographics.forced_choice.counts;
  $('abstention-comparison').textContent = `When allowed to decline, the AI did so ${allowed.abstain} times out of 140. When required to choose, it selected an action ${required.decision} times out of 140. The earlier refusals left too few choices to compare group preferences.`;
  renderDemographicPair();
}

function renderExplanationExample() {
  // Fixed examples from one repeated age question, not a summary of every response.
  const cell = state.demographics.moral_machine.cells.find(item => item.id === 'age__original__stay_first');
  $('reason-contrast').replaceChildren();
  for (const index of [0, 4]) {
    const article = element('article');
    article.append(element('h3', index === 0 ? 'Save the children' : 'Avoid redirecting harm'));
    responseView(article, cell.trials[index]);
    $('reason-contrast').append(article);
  }
}

function annotationName(annotation) {
  const filename = annotation.source_path.split('/').pop().replace('.json', '');
  const parts = filename.split('__');
  if (annotation.source_path.includes('/framing/')) return `${parts[0].endsWith('mirrored') ? 'Risk on STAY' : 'Risk on SWERVE'} · ${frameNames[parts[1]]} · answer ${parts[3].slice(1)}`;
  const labels = { age: 'Age', race: 'Race', gender: 'Gender', number: 'Number of lives', role: 'Passenger / pedestrian', crossing: 'Crossing signals', conflict: 'Age versus number' };
  return `${labels[parts[0]]} · ${parts[1] === 'swapped' ? 'swapped paths' : 'original paths'} · ${parts[2] === 'stay_first' ? 'STAY written first' : 'SWERVE written first'} · answer 1`;
}

function renderExplanationReview() {
  const review = state.review;
  $('explanation-summary').replaceChildren(element('h3', `${review.reviewed_responses} explanations reviewed`), element('p', `${review.main_reviewed_responses} come from the main dilemma experiment and ${review.supporting_reviewed_responses} from the supporting studies. ${review.facts_correct.yes} were judged accurate about the stated facts; one was unclear because it inferred illegality from a crossing signal. All ${review.supports_action.yes} gave a reason supporting their own action.`), element('p', 'The explanations mention saving more people, protecting children, avoiding risk, respecting crossing rules, and staying on the current path.'));
  for (const [index, check] of review.checks.entries()) {
    const tr = element('tr');
    for (const value of [['Risk situations', 'Demographic ties', 'Main People experiment'][index], `${check.matches} of ${check.scored} choices matched`, `${check.always_stay_matches} of ${check.scored} choices matched`]) tr.append(element('td', value));
    $('explanation-checks').append(tr);
  }
  for (const row of review.annotations) {
    const details = element('details');
    const judgment = { yes: 'Yes', no: 'No', unclear: 'Unclear' };
    details.append(element('summary', annotationName(row)), element('blockquote', row.justification), element('p', `Stated principle: ${principleNames[row.principle]}. Facts accurate: ${judgment[row.facts_correct] || 'Unclear'}. Reason supports this action: ${judgment[row.supports_action] || 'Unclear'}.`), element('p', row.notes, 'helper'));
    $('explanation-annotations').append(details);
  }
}

async function readData(filename) {
  const response = await fetch(`data/${filename}`);
  if (!response.ok) throw new Error(`Study results could not be loaded (HTTP ${response.status})`);
  return response.json();
}

function connectControls() {
  for (const id of ['scenario', 'condition', 'frame']) $(id).addEventListener('change', renderWording);
  $('same').addEventListener('click', () => revealWording('same'));
  $('different').addEventListener('click', () => revealWording('different'));
  $('next-repeat').addEventListener('click', () => { state.repeat = (state.repeat + 1) % currentCell('neutral').trials.length; renderRepeat(); });
  $('swap-people').addEventListener('click', () => { state.swapped = !state.swapped; renderDemographicPair(); });
  for (const action of ['stay', 'swerve', 'abstain']) $(`guess-${action}`).addEventListener('click', () => revealDemographic(action));
  for (const id of ['demographic-attribute', 'demographic-order']) $(id).addEventListener('change', () => {
    state.swapped = false;
    const social = isSocialComparison() || isMoralComparison();
    if (social) $('demographic-condition').value = 'forced_choice';
    $('demographic-condition').querySelector('option[value="abstention_allowed"]').disabled = social;
    renderDemographicResults();
  });
  $('people-bank').addEventListener('change', configurePeopleBank);
  $('demographic-condition').addEventListener('change', () => { state.swapped = false; renderDemographicResults(); });
}

function followScroll() {
  const links = [...document.querySelectorAll('nav a')];
  const sections = links.map(link => document.querySelector(link.hash));
  let scheduled = false;
  function update() {
    scheduled = false;
    const marker = document.querySelector('header').getBoundingClientRect().bottom + 48;
    let current = sections[0];
    for (const section of sections) {
      if (section.getBoundingClientRect().top <= marker) current = section;
    }
    for (const link of links) {
      if (link.hash === `#${current.id}`) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
  }
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(update);
  }
  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', schedule);
  update();
}

async function start() {
  try {
    const [study, forced, allowed, review, social, moral, edges, challenges] = await Promise.all([readData('study.json'), readData('demographics_forced.json'), readData('demographics.json'), readData('explanation_analysis.json'), readData('demographics_social.json'), readData('demographics_moral.json'), readData('demographics_edges.json'), readData('challenges.json')]);
    state.study = study;
    state.demographics = { forced_choice: forced, abstention_allowed: allowed, social_roles: social, moral_machine: moral, edge_cases: edges };
    state.review = review;
    state.challenges = challenges;
    $('scenario').replaceChildren();
    for (const scenario of study.protocol.scenarios) {
      const option = element('option', scenarioName(scenario));
      option.value = scenario.id;
      $('scenario').append(option);
    }
    $('scenario').value = 'equal_expected-mirrored';
    for (const id of ['scenario', 'frame', 'demographic-attribute', 'next-repeat']) $(id).disabled = false;
    connectControls();
    renderWording();
    renderWordingResults();
    configurePeopleBank();
    configureChallenges();
    renderStudyHistory();
    renderExplanationExample();
    renderExplanationReview();
    for (const heading of document.querySelectorAll('thead th')) heading.scope = 'col';
    const recorded = challenges.counts.decision + challenges.counts.abstain + challenges.counts.invalid + edges.counts.decision + edges.counts.abstain + edges.counts.invalid + moral.counts.decision + moral.counts.abstain + moral.counts.invalid + social.counts.decision + social.counts.abstain + social.counts.invalid + study.counts.valid + study.counts.invalid + forced.counts.decision + forced.counts.abstain + forced.counts.invalid + allowed.counts.decision + allowed.counts.abstain + allowed.counts.invalid;
    const missing = challenges.counts.missing + edges.counts.missing + moral.counts.missing + social.counts.missing + study.counts.missing + forced.counts.missing + allowed.counts.missing;
    $('study-status').textContent = `${recorded} recorded answers · ${missing ? `${missing} still missing` : 'collection complete'}. The site replays these answers.`;
    $('data-counts').textContent = `Model studied: ${study.protocol.model}. The experiments contain ${recorded} recorded answers in total. Repeated questions start separate conversations; follow-up challenges begin with the same recorded question and answer. The explanation review covers ${review.reviewed_responses} selected answers, as described in the Reasons section.`;
    followScroll();
  } catch (error) {
    $('study-status').textContent = 'The study results could not be loaded. Please refresh the page or try again later.';
    $('study-status').setAttribute('role', 'alert');
    for (const control of document.querySelectorAll('main button, main select')) control.disabled = true;
    for (const id of ['finding', 'demographic-finding', 'explanation-summary', 'challenge-finding']) $(id).textContent = 'Study data unavailable. See the message at the start of the page.';
  }
}

start();

function configurePeopleBank() {
  const select = $('demographic-attribute');
  select.replaceChildren();
  const options = isMoralComparison()
    ? [...new Map(demographicStudy().protocol.cells.map(cell => [cell.attribute, cell.title])).entries()]
    : [['race','Race: Black and White'],['gender','Gender: man and woman'],['age','Age: 25 and 75'],['occupation','Occupation: doctor and accountant'],['criminal_history','Completed conviction / history not provided'],['social_control','No labels: occupation/history control'],['control','No demographic information']];
  for (const [value,label] of options) {
    const option = element('option',label);
    option.value = value;
    select.append(option);
  }
  state.swapped = false;
  $('demographic-condition').value = 'forced_choice';
  $('demographic-condition').querySelector('option[value="abstention_allowed"]').disabled = isMoralComparison();
  renderDemographicResults();
}

function renderStudyHistory() {
  const rows = [
    ['Wording and repeated questions', '120 main answers + 120 restatement answers', 'Answers varied about as often with identical wording as with different descriptions. One risk question produced different choices even when repeated exactly.'],
    ['Equal casualties, with refusal allowed', '140 answers', 'The model declined 137 times, including most questions without identifying labels. That left too few choices to compare group preferences.'],
    ['Equal casualties, with a required choice', '140 answers', 'Every answer chose STAY, including after labels were exchanged between outcomes and written order was reversed.'],
    ['Occupation and disclosed history', '100 answers', 'Doctor/accountant and completed-conviction/unspecified-history comparisons also produced STAY throughout.'],
    ['Moral Machine-inspired trade-offs', '100 answers', 'The model saved more people in every count comparison. It saved children in 17/20 equal-count age answers, but three adults over one child in 20/20 answers. The passenger comparison always produced STAY.'],
    ['Two follow-up conflicts', `${state.demographics.edge_cases.protocol.maximum_recorded_responses - state.demographics.edge_cases.counts.missing}/40 answers recorded`, 'Three adults were saved over two children in all 20 answers. The child-versus-legally-crossing-adult case always produced STAY, saving each person in half the placements. Repeating an identical question did not change either choice.'],
    ['Challenges to a saved decision', `${state.challenges.counts.planned - state.challenges.counts.missing}/60 new answers recorded`, 'All 60 follow-ups kept the starting action: 20 after an ethical argument, 20 after simple disagreement, and 20 after neutral reconsideration. Every branch started from the same saved exchange for that case.']
  ];
  const list = element('ol');
  for (const [title,count,result] of rows) {
    const li = element('li');
    li.append(element('strong',`${title} · ${count}`),element('p',result));
    list.append(li);
  }
  $('study-history').append(list);
}


function challengeCell() {
  const anchor = state.challenges.protocol.anchors.find(row => row.attribute === $('challenge-scenario').value && row.swapped === state.challengeSwapped);
  return state.challenges.cells.find(cell => cell.anchor_id === anchor.id && cell.condition === $('challenge-condition').value);
}

function renderChallenge() {
  const cell = challengeCell();
  const anchor = state.challenges.protocol.anchors.find(row => row.id === cell.anchor_id);
  const dilemma = state.demographics.moral_machine.cells.find(item => item.attribute === anchor.attribute && item.swapped === anchor.swapped);
  const situation = element('div', undefined, 'description');
  situation.append(element('p', `STAY kills ${dilemma.stay_description}; SWERVE kills ${dilemma.swerve_description}. The other group survives.`));
  $('challenge-initial').replaceChildren(situation, element('p', `The original choice was ${anchor.choice.toUpperCase()}, saving ${anchor.saved_label}.`), element('blockquote', anchor.justification));
  $('challenge-placement').textContent = state.challengeSwapped ? 'Outcomes exchanged between STAY and SWERVE.' : 'Original outcome placement.';
  $('challenge-swap').textContent = state.challengeSwapped ? 'Restore the original outcomes' : 'Exchange the original outcomes';
  $('challenge-prompt').textContent = cell.followup.split(' The people and consequences have not changed.')[0];
  $('challenge-original-question').textContent = questionText(anchor.prompt);
  $('challenge-exact-prompt').textContent = questionText(cell.followup);
  $('challenge-answer').hidden = true;
  $('challenge-trials').replaceChildren();
  for (const trial of cell.trials) responseView($('challenge-trials'), trial);
  const available = ['decision', 'abstain'].includes(cell.trials[state.challengeRepeat].status);
  for (const id of ['challenge-keep', 'challenge-change', 'challenge-next']) $(id).disabled = !available;
}

function revealChallenge(guess) {
  const trial = challengeCell().trials[state.challengeRepeat];
  const heading = trial.status === 'abstain' ? 'It declined to choose.' : trial.changed ? 'It changed its choice.' : 'It kept its choice.';
  const parent = $('challenge-answer');
  parent.replaceChildren(element('h3', heading));
  if (guess && trial.status === 'decision') parent.append(element('p', guess === (trial.changed ? 'change' : 'keep') ? 'Your prediction matched this saved answer.' : 'Your prediction did not match this saved answer.'));
  responseView(parent, trial);
  if (trial.saved_label) parent.append(element('p', `This choice saves ${trial.saved_label}.`));
  parent.hidden = false;
}

function renderChallengeResults() {
  const study = state.challenges;
  $('challenge-results').replaceChildren();
  for (const [condition, label] of [['argument','Ethical argument'],['disagreement','Simple disagreement'],['neutral','Neutral reconsideration']]) {
    const counts = study.conditions[condition];
    const row = element('tr');
    for (const value of [label, counts.decision ? `${counts.changed}/${counts.decision} decisions` : 'No decisions yet', counts.decision ? `${counts.kept}/${counts.decision}` : 'No decisions yet', `${counts.abstain}/${counts.planned}`]) row.append(element('td',value));
    $('challenge-results').append(row);
  }
  const counts = study.counts;
  const difference = study.comparisons.disagreement.argument_minus_baseline;
  $('challenge-finding').textContent = counts.missing || counts.invalid ? 'Challenge collection is incomplete.' : counts.changed === 0 && counts.abstain === 0 ? 'Every follow-up kept the starting choice.' : difference > 0 ? 'Ethical arguments changed more choices than disagreement alone.' : difference < 0 ? 'Disagreement alone changed more choices than the ethical arguments.' : 'Ethical arguments and disagreement changed choices equally often overall.';
  $('challenge-takeaway').textContent = difference === null ? 'Complete matched starting answers are needed for the comparison.' : counts.changed === 0 && counts.abstain === 0 ? 'All 60 responses retained the saved initial action: 20 after ethical arguments, 20 after disagreement, and 20 after neutral reconsideration. This shows stability in these conversations, even though some earlier fresh answers varied. The fresh and follow-up answers come from different conversation contexts and collection periods. This does not establish moral correctness or what caused the stability.' : `Across the same ten starting answers, the argument condition changed choices ${Math.abs(100*difference).toFixed(0)} percentage points ${difference < 0 ? 'less' : 'more'} often than disagreement alone. Neutral reconsideration shows how often the model changed without a suggested action. These results concern these particular arguments and starting answers.`;
  $('challenge-status').textContent = `${counts.planned-counts.missing} of ${counts.planned} follow-ups recorded.${counts.invalid || counts.missing ? ` ${counts.invalid} unusable and ${counts.missing} missing.` : ''} Starting answers come from the earlier study.`;
  $('challenge-by-anchor').replaceChildren();
  for (const anchor of study.protocol.anchors) {
    const row = element('tr');
    row.append(element('td',`${anchor.title} · ${anchor.swapped ? 'exchanged outcomes' : 'original outcomes'}`));
    for (const condition of ['argument','disagreement','neutral']) {
      const cell = study.cells.find(cell=>cell.anchor_id===anchor.id && cell.condition===condition);
      row.append(element('td',cell.counts.decision ? `${cell.counts.changed}/${cell.counts.decision}` : 'No decisions yet'));
    }
    $('challenge-by-anchor').append(row);
  }
}

function configureChallenges() {
  const options = new Map(state.challenges.protocol.anchors.map(anchor=>[anchor.attribute,anchor.title]));
  $('challenge-scenario').replaceChildren();
  for (const [value,label] of options) {
    const option=element('option',label);
    option.value=value;
    $('challenge-scenario').append(option);
  }
  $('challenge-scenario').value='conflict';
  for (const id of ['challenge-scenario','challenge-condition','challenge-swap']) $(id).disabled=false;
  for (const id of ['challenge-scenario','challenge-condition']) $(id).addEventListener('change',()=>{ state.challengeRepeat=0; renderChallenge(); });
  $('challenge-swap').addEventListener('click',()=>{ state.challengeSwapped=!state.challengeSwapped; state.challengeRepeat=0; renderChallenge(); });
  $('challenge-keep').addEventListener('click',()=>revealChallenge('keep'));
  $('challenge-change').addEventListener('click',()=>revealChallenge('change'));
  $('challenge-next').addEventListener('click',()=>{ state.challengeRepeat=(state.challengeRepeat+1)%challengeCell().trials.length; revealChallenge(); });
  renderChallenge();
  renderChallengeResults();
}
