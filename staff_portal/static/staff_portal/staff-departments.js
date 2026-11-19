(function () {
  "use strict";
  function init() {
    const form = document.getElementById("staff-registration");
    const dataElement = document.getElementById("campus-staff-departments");
    if (!form || !dataElement) return;
    const category = form.querySelector('[name="staff_category"]');
    const department = form.querySelector('[name="department"]');
    if (!category || !department) return;
    let catalogue = [];
    try { catalogue = JSON.parse(dataElement.textContent); }
    catch (_error) { return; }
    function refresh() {
      const previous = department.value;
      const chosen = category.value;
      department.replaceChildren();
      const placeholder = new Option(chosen ? "Choose your department" : "Select a staff category first", "");
      department.add(placeholder);
      catalogue.filter(item => item.category === chosen).forEach(item => {
        department.add(new Option(item.name, item.name));
      });
      if (Array.from(department.options).some(opt => opt.value === previous)) {
        department.value = previous;
      } else { department.value = ""; }
      department.disabled = !chosen;
    }
    category.addEventListener("change", refresh);
    refresh();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else { init(); }
}());
