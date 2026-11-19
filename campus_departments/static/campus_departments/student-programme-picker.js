(() => {
  'use strict';
  const form = document.querySelector('#cu-application-form');
  if (!form) return;
  const department = form.querySelector('#id_department');
  const grade = form.querySelector('#id_kcse_mean_grade');
  const points = form.querySelector('#id_reported_cluster_points');
  const selector = form.querySelector('#id_programme');
  const info = document.querySelector('#cu-results');
  if (!department || !grade || !points || !selector || !info) return;
  const initialSelection = selector.value;
  let seq = 0;
  async function update() {
    const id = ++seq;
    const value = Number(points.value);
    selector.replaceChildren(new Option('Choose a matching programme', ''));
    if (!department.value) {
      info.textContent = 'Select your department to view its programmes.';
      return;
    }
    if (!grade.value || !points.value || !Number.isFinite(value) || value < 0 || value > 48) {
      info.textContent = 'Now choose your KCSE grade and enter estimated cluster points (0–48).';
      return;
    }
    info.textContent = 'Finding preliminary matches within this department…';
    try {
      const url = new URL(form.dataset.finderUrl, window.location.href);
      url.searchParams.set('department', department.value);
      url.searchParams.set('grade', grade.value);
      url.searchParams.set('points', points.value);
      const response = await fetch(url, {credentials: 'same-origin'});
      if (!response.ok) throw new Error('Fetch failed');
      const data = await response.json();
      if (seq !== id) return;
      for (const p of data.programmes) {
        selector.add(new Option(`${p.name} (${p.code}) — example min. ${p.minimum_points}/48`, String(p.id)));
      }
      if ([...selector.options].some((o) => o.value === initialSelection)) selector.value = initialSelection;
      info.textContent = data.programmes.length
        ? `${data.programmes.length} programme(s) shown for ${department.value}. These are indicative, not admission offers.`
        : 'No matches using the sample entry scores. Check your details or contact the admissions office.';
    } catch (_err) {
      if (seq === id) info.textContent = 'Unable to load programmes. Check your network and try again.';
    }
  }
  let timer;
  const updateSoon = () => {clearTimeout(timer); timer = setTimeout(update, 250);};
  department.addEventListener('change', update);
  grade.addEventListener('change', update);
  points.addEventListener('change', update);
  points.addEventListener('input', updateSoon);
  update();
})();
