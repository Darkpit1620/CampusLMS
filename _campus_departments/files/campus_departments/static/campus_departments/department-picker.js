(() => {
  'use strict';
  const picker = document.querySelector('[data-cd-unit-picker]');
  if (!picker) return;
  const form = picker.closest('form');
  const department = form?.querySelector('#id_department');
  const yearFilter = picker.querySelector('[data-cd-year]');
  const semesterFilter = picker.querySelector('[data-cd-semester]');
  const search = picker.querySelector('[data-cd-search]');
  const options = picker.querySelector('[data-cd-options]');
  const selectedBox = picker.querySelector('[data-cd-selected]');
  const hidden = picker.querySelector('[data-cd-hidden]');
  const count = picker.querySelector('[data-cd-count]');
  if (!department || !options) return;
  let available = [];
  let selected = new Set((picker.dataset.initial || '').split(',').filter(Boolean));
  let requestId = 0;

  function updateSelected() {
    hidden.replaceChildren();
    for (const id of selected) {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'requested_units';
      input.value = id;
      hidden.appendChild(input);
    }
    count.textContent = `${selected.size} unit(s) selected for administrator approval`;
    selectedBox.replaceChildren();
    for (const id of selected) {
      const unit = available.find((u) => String(u.id) === id);
      if (!unit) continue;
      const tag = document.createElement('button');
      tag.type = 'button';
      tag.className = 'cd-tag';
      tag.textContent = `${unit.title} ×`;
      tag.setAttribute('aria-label', `Remove ${unit.title}`);
      tag.addEventListener('click', () => {
        selected.delete(id);
        updateSelected();
        render();
      });
      selectedBox.appendChild(tag);
    }
  }

  function render() {
    options.replaceChildren();
    const filter = search.value.trim().toLocaleLowerCase();
    const items = available.filter((u) =>
      (!yearFilter.value || String(u.year) === yearFilter.value) &&
      (!semesterFilter.value || String(u.semester) === semesterFilter.value) &&
      (!filter || `${u.title} ${u.programme}`.toLocaleLowerCase().includes(filter))
    );
    if (!items.length) {
      const empty = document.createElement('p');
      empty.className = 'cd-muted';
      empty.textContent = available.length ? 'No units match your filters.' : 'Choose a department to see its units.';
      options.appendChild(empty);
      return;
    }
    for (const u of items) {
      const label = document.createElement('label');
      label.className = 'cd-unit-row';
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = selected.has(String(u.id));
      checkbox.addEventListener('change', () => {
        const id = String(u.id);
        checkbox.checked ? selected.add(id) : selected.delete(id);
        updateSelected();
      });
      const text = document.createElement('span');
      text.textContent = `${u.title} — ${u.programme} · Year ${u.year}, Semester ${u.semester}`;
      label.append(checkbox, text);
      options.appendChild(label);
    }
  }

  async function load() {
    const myId = ++requestId;
    const name = department.value;
    if (!name) {
      available = [];
      selected.clear();
      updateSelected();
      render();
      return;
    }
    options.textContent = 'Loading department units…';
    try {
      const url = new URL(picker.dataset.url, window.location.href);
      url.searchParams.set('department', name);
      const response = await fetch(url, {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
      if (!response.ok) throw new Error('Fetch error');
      const data = await response.json();
      if (myId !== requestId) return;
      available = data.units || [];
      const ids = new Set(available.map((u) => String(u.id)));
      selected = new Set([...selected].filter((id) => ids.has(id)));
      updateSelected();
      render();
    } catch (_err) {
      if (myId === requestId) options.textContent = 'Could not load department units. Refresh and try again.';
    }
  }
  department.addEventListener('change', () => {
    selected.clear();
    yearFilter.value = '';
    semesterFilter.value = '';
    search.value = '';
    load();
  });
  yearFilter.addEventListener('change', render);
  semesterFilter.addEventListener('change', render);
  search.addEventListener('input', render);
  load();
})();
