(() => {
  'use strict';
  const form = document.querySelector('#cu-application-form');
  if (!form) return;
  const grade = form.querySelector('#id_kcse_mean_grade');
  const points = form.querySelector('#id_reported_cluster_points');
  const selector = form.querySelector('#id_programme');
  const info = document.querySelector('#cu-results');
  if (!grade || !points || !selector || !info) return;
  const originalSelection = selector.value;
  let currentFetch = 0;
  const msg = (txt) => { info.textContent = txt; };
  const update = async () => {
    const myFetch = ++currentFetch;
    const value = Number(points.value);
    if (!grade.value || !points.value || !Number.isFinite(value) || value < 0 || value > 48) {
      msg('Select a KCSE mean grade and enter points between 0 and 48.');
      selector.replaceChildren(new Option('Enter grade and points first', ''));
      return;
    }
    msg('Finding preliminary programme matches…');
    try {
      const u = new URL(form.dataset.finderUrl, window.location.href);
      u.searchParams.set('grade', grade.value);
      u.searchParams.set('points', points.value);
      const response = await fetch(u, {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
      if (!response.ok) throw new Error('Unable to load programmes');
      const data = await response.json();
      if (myFetch !== currentFetch) return;
      const keep = selector.value || originalSelection;
      selector.replaceChildren(new Option('Choose a programme', ''));
      for (const p of data.programmes) {
        const label = `${p.name} — ${p.code} (example minimum ${p.minimum_points}/48)`;
        selector.add(new Option(label, String(p.id)));
      }
      if (Array.from(selector.options).some(opt => opt.value === keep)) selector.value = keep;
      msg(data.programmes.length
        ? `${data.programmes.length} preliminary match(es) found. These are not admission decisions; administrator verification is required.`
        : 'No programmes match the current example thresholds. Check your score, or contact Admissions.');
    } catch (error) {
      if (myFetch === currentFetch) msg('Could not load the programme list. Refresh this page or contact Admissions.');
    }
  };
  grade.addEventListener('change', update);
  points.addEventListener('change', update);
  points.addEventListener('input', () => { clearTimeout(points._updateTimer); points._updateTimer = setTimeout(update, 280); });
  if (grade.value && points.value) update();
})();
