/* Read-only student signup curriculum preview; actual registration happens after admission. */
(() => {
  'use strict';
  const panel = document.querySelector('[data-s16-student-preview]');
  if (!panel) return;
  const form = panel.closest('form');
  const department = form.querySelector('[name="department"]');
  const programme = form.querySelector('[name="programme"]');
  const list = panel.querySelector('[data-s16-unit-list]');
  const title = panel.querySelector('[data-s16-unit-heading]');
  if (!department || !programme || !list || !title) return;
  let last = ''; let seq = 0;
  async function update() {
    const key = `${department.value}|${programme.value}`;
    if (key === last) return;
    last = key; const id = ++seq;
    list.replaceChildren();
    if (!programme.value || !department.value) {
      title.textContent = 'Year 1 · Semester 1 units';
      list.textContent = 'Choose a department and eligible programme above to see its first-semester units.';
      return;
    }
    const programmeName = programme.selectedOptions[0]?.textContent || 'Selected programme';
    title.textContent = `${programmeName} · Year 1 · Semester 1`;
    list.textContent = 'Loading programme units…';
    try {
      const url = new URL(panel.dataset.unitsUrl, window.location.href);
      url.searchParams.set('department', department.value);
      const response = await fetch(url, {credentials:'same-origin', headers:{Accept:'application/json'}});
      if (!response.ok) throw new Error('Unable to load');
      const data = await response.json();
      if (id !== seq) return;
      // The server returns the exact Programme primary key for each placement.
      const entries = (data.units || []).filter(u =>
        Number(u.year) === 1 && Number(u.semester) === 1 &&
        String(u.programme_id) === String(programme.value)
      );
      list.replaceChildren();
      if (!entries.length) { list.textContent = 'No Year 1 Semester 1 units are currently listed for this programme.'; return; }
      const ul = document.createElement('ul'); ul.className = 's16-preview-list';
      entries.forEach(u => { const li = document.createElement('li'); li.textContent = u.title; ul.appendChild(li); });
      list.appendChild(ul);
      const note = document.createElement('small'); note.textContent = `${entries.length} units · After admission you will register for these units in the Student Dashboard.`;
      list.appendChild(note);
    } catch (_) {
      if (id === seq) list.textContent = 'Unable to load programme units. Refresh and try again.';
    }
  }
  department.addEventListener('change', () => { last = ''; update(); });
  programme.addEventListener('change', update);
  // Existing programme-matching script adds options asynchronously; observe those changes.
  new MutationObserver(() => { if (`${department.value}|${programme.value}` !== last) update(); })
    .observe(programme, {childList:true, attributes:false});
  update();
})();
