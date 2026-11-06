// This file is added by railway_start.py to the landing page. Keep it separate
// so the server can add dashboard navigation without editing the site's HTML.
(() => {
  const button = document.querySelector('#login-button');
  if (!button) return;
  button.addEventListener('click', () => {
    button.setAttribute('aria-busy', 'true');
  });
})();
