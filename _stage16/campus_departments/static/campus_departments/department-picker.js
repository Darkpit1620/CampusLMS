/* CampusLMS Stage 16: department -> programme/year/term -> unit dropdown.
   Never grants permission: Django forms validate submitted placement IDs. */
(() => {
  'use strict';
  function initialize(picker) {
    const form = picker.closest('form');
    const department = form && form.querySelector('[name="department"]');
    const programme = picker.querySelector('[data-cd-programme]');
    const year = picker.querySelector('[data-cd-year]');
    const semester = picker.querySelector('[data-cd-semester]');
    const search = picker.querySelector('[data-cd-search]');
    const dropdown = picker.querySelector('[data-cd-unit-dropdown]');
    const add = picker.querySelector('[data-cd-add]');
    const selectedBox = picker.querySelector('[data-cd-selected]');
    const hidden = picker.querySelector('[data-cd-hidden]');
    const status = picker.querySelector('[data-cd-status]');
    const count = picker.querySelector('[data-cd-count]');
    if (!department || !dropdown || !add || !hidden || !status) return;
    let available = Array.from(dropdown.options).filter(o => o.value).map(o => ({
      id: o.value,
      title: o.textContent.split(' · ')[0],
      programme: o.dataset.programme || '',
      year: Number(o.dataset.year || 0),
      semester: Number(o.dataset.semester || 0)
    }));
    const selected = new Set((picker.dataset.initial || '').split(',').filter(Boolean));
    let serial = 0;

    function label(u) { return `${u.title} — ${u.programme} · Year ${u.year}, Semester ${u.semester}`; }
    function drawSelected() {
      hidden.replaceChildren();
      selectedBox.replaceChildren();
      for (const id of selected) {
        const input = document.createElement('input');
        input.type = 'hidden'; input.name = 'requested_units'; input.value = id;
        hidden.appendChild(input);
        const item = available.find(u => String(u.id) === id);
        const chip = document.createElement('button');
        chip.type = 'button'; chip.className = 'cd-tag';
        chip.textContent = `${item ? label(item) : `Unit #${id}`} ×`;
        chip.setAttribute('aria-label', `Remove ${item ? label(item) : id}`);
        chip.addEventListener('click', () => { selected.delete(id); drawSelected(); drawDropdown(); });
        selectedBox.appendChild(chip);
      }
      count.textContent = `${selected.size} unit(s) selected for administrator approval`;
    }
    function drawProgrammes() {
      const previous = programme.value;
      const names = Array.from(new Set(available.map(u => u.programme))).sort();
      programme.replaceChildren(new Option('All programmes in this department', ''));
      names.forEach(name => programme.add(new Option(name, name)));
      if (names.includes(previous)) programme.value = previous;
    }
    function drawDropdown() {
      const q = search.value.trim().toLocaleLowerCase();
      const matches = available.filter(u =>
        (!programme.value || u.programme === programme.value) &&
        (!year.value || String(u.year) === year.value) &&
        (!semester.value || String(u.semester) === semester.value) &&
        (!q || `${u.title} ${u.programme}`.toLocaleLowerCase().includes(q))
      );
      dropdown.replaceChildren(new Option(
        matches.length ? 'Choose a unit to add' : (available.length ? 'No units match these filters' : 'No units available'), ''
      ));
      matches.forEach(u => {
        if (!selected.has(String(u.id))) dropdown.add(new Option(label(u), String(u.id)));
      });
      status.textContent = department.value
        ? `${matches.length} matching unit placement(s). ${available.length} total in ${department.value}.`
        : 'Choose a department to see available units.';
    }
    function useResult(units) {
      available = units.map(u => ({
        id: String(u.id), title: String(u.title), programme: String(u.programme),
        year: Number(u.year), semester: Number(u.semester)
      }));
      const ids = new Set(available.map(u => String(u.id)));
      for (const id of selected) if (!ids.has(id)) selected.delete(id);
      drawProgrammes(); drawSelected(); drawDropdown();
    }
    async function load() {
      const requestId = ++serial;
      if (!department.value) { useResult([]); return; }
      status.textContent = 'Loading department units…';
      // Show existing server-rendered options immediately if available.
      try {
        const endpoint = new URL(picker.dataset.url, window.location.href);
        endpoint.searchParams.set('department', department.value);
        const response = await fetch(endpoint, {
          credentials: 'same-origin', headers: {Accept: 'application/json'}
        });
        if (!response.ok) throw new Error('Unable to load units');
        const data = await response.json();
        if (requestId !== serial) return;
        useResult(Array.isArray(data.units) ? data.units : []);
      } catch (_) {
        if (requestId !== serial) return;
        if (available.length) {
          status.textContent = 'Showing saved department units. If the list is outdated, refresh this page.';
          drawProgrammes(); drawDropdown();
        } else {
          status.textContent = 'Units could not load. Check your connection or ask the administrator to verify the course catalogue.';
          dropdown.replaceChildren(new Option('Units unavailable', ''));
        }
      }
    }
    add.addEventListener('click', () => {
      if (!dropdown.value) return;
      selected.add(dropdown.value);
      drawSelected(); drawDropdown();
    });
    dropdown.addEventListener('change', () => {
      // A simple selection immediately adds the unit; the Add button also works.
      if (dropdown.value) { selected.add(dropdown.value); drawSelected(); drawDropdown(); }
    });
    [programme, year, semester].forEach(input => input.addEventListener('change', drawDropdown));
    search.addEventListener('input', drawDropdown);
    department.addEventListener('change', () => {
      selected.clear(); programme.value = ''; year.value = ''; semester.value = ''; search.value = '';
      available = []; drawSelected(); drawDropdown(); load();
    });
    drawSelected();
    if (department.value) { drawProgrammes(); drawDropdown(); load(); }
    else { useResult([]); }
  }
  document.querySelectorAll('[data-cd-unit-picker]').forEach(initialize);
})();
