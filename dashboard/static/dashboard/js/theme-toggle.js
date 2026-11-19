/* CampusLMS accessible theme toggle, shared by every page using dashboard/base.html. */
(() => {
  'use strict';
  const KEY = 'campuslms-theme';
  const root = document.documentElement;
  const preferredDark = () => window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const getSaved = () => {
    try {
      const saved = window.localStorage.getItem(KEY);
      if (saved === 'light' || saved === 'dark') return saved;
    } catch (error) { /* Storage may be unavailable in private browsing. */ }
    return null;
  };
  let saved = getSaved();
  let current = saved || (preferredDark() ? 'dark' : 'light');

  function apply(theme) {
    current = theme;
    root.setAttribute('data-theme', theme);
    root.style.colorScheme = theme;
    const goingDark = theme !== 'dark';
    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      const label = goingDark ? 'Dark mode' : 'Light mode';
      button.setAttribute('aria-label', 'Switch to ' + label.toLowerCase());
      button.setAttribute('title', 'Switch to ' + label.toLowerCase());
      button.setAttribute('aria-pressed', String(theme === 'dark'));
      const icon = button.querySelector('[data-theme-icon]');
      const text = button.querySelector('[data-theme-label]');
      if (icon) icon.textContent = goingDark ? '☾' : '☀';
      if (text) text.textContent = label;
    });
    const themeColor = document.querySelector('meta[name="theme-color"]');
    if (themeColor) themeColor.setAttribute('content', theme === 'dark' ? '#101629' : '#6857f6');
  }

  apply(current);
  function init() {
    apply(current);
    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      button.addEventListener('click', () => {
        const next = current === 'dark' ? 'light' : 'dark';
        saved = next;
        try { window.localStorage.setItem(KEY, next); } catch (error) { /* still works this session */ }
        apply(next);
      });
    });
    if (window.matchMedia) {
      const query = window.matchMedia('(prefers-color-scheme: dark)');
      const onChange = () => {
        if (!saved) apply(query.matches ? 'dark' : 'light');
      };
      if (query.addEventListener) query.addEventListener('change', onChange);
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
