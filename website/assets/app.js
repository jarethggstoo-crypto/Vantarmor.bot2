const $ = (selector) => document.querySelector(selector);
const guildGrid = $('#guild-grid');
const guildStatus = $('#guild-status');
const loginButton = $('#login-button');
const profileChip = $('#profile-chip');
const menu = $('#side-menu');
const menuToggle = $('#menu-toggle');
const backdrop = $('#menu-backdrop');

const views = ['inicio', 'funciones', 'estado', 'invitar', 'planes', 'ajustes'];
const viewTitles = {
  inicio: 'Inicio',
  funciones: 'Funciones y comandos',
  estado: 'Estado y protección',
  invitar: 'Invitar bot',
  planes: 'Planes',
  ajustes: 'Ajustes',
};
const inviteBase = 'https://discord.com/oauth2/authorize?client_id=1567331667826311288&scope=bot%20applications.commands&permissions=0';

function setMenu(open) {
  menu.classList.toggle('open', open);
  menu.setAttribute('aria-hidden', String(!open));
  menuToggle.setAttribute('aria-expanded', String(open));
  menuToggle.setAttribute('aria-label', open ? 'Cerrar menú' : 'Abrir menú');
  backdrop.hidden = !open;
}

function showView(view, updateHistory = false) {
  const activeView = views.includes(view) ? view : 'inicio';
  for (const id of views) {
    const section = document.getElementById(id);
    if (section) section.hidden = id !== activeView;
  }
  const intro = document.querySelector('.intro-strip');
  if (intro) intro.hidden = activeView !== 'inicio';
  const bottomCta = document.querySelector('.bottom-cta');
  if (bottomCta) bottomCta.hidden = activeView !== 'inicio';

  document.querySelectorAll('.menu-link').forEach((link) => {
    const selected = link.getAttribute('href') === `#${activeView}`;
    link.classList.toggle('active', selected);
    if (selected) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });

  document.title = `${viewTitles[activeView]} — Vantarmor Commands`;
  if (updateHistory && location.hash !== `#${activeView}`) {
    history.pushState({view: activeView}, '', `#${activeView}`);
  }
  setMenu(false);
  window.scrollTo({top: 0, behavior: 'smooth'});
}

menuToggle.addEventListener('click', () => setMenu(menuToggle.getAttribute('aria-expanded') !== 'true'));
$('#menu-close').addEventListener('click', () => setMenu(false));
backdrop.addEventListener('click', () => setMenu(false));

// Treat the menu and in-page calls to action as separate dashboard views,
// rather than scrolling through one long landing page.
document.querySelectorAll('a[href^="#"]').forEach((link) => {
  link.addEventListener('click', (event) => {
    const target = link.getAttribute('href').slice(1);
    if (!views.includes(target)) return;
    event.preventDefault();
    showView(target, true);
  });
});
window.addEventListener('popstate', () => showView(location.hash.slice(1) || 'inicio'));
showView(location.hash.slice(1) || 'inicio');

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}

function drawGuilds(guilds) {
  guildGrid.replaceChildren();
  if (!guilds.length) {
    guildStatus.textContent = 'No encontramos servidores donde tengas permisos para añadir bots. Comprueba tus permisos en Discord.';
    return;
  }
  guildStatus.textContent = `Tus servidores disponibles para invitar: ${guilds.length}. Elige uno para continuar en Discord.`;
  for (const guild of guilds) {
    const card = document.createElement('article');
    card.className = 'guild-card';
    const icon = document.createElement(guild.icon ? 'img' : 'div');
    icon.className = 'guild-icon';
    if (guild.icon) {
      icon.src = `https://cdn.discordapp.com/icons/${encodeURIComponent(guild.id)}/${encodeURIComponent(guild.icon)}.png?size=96`;
      icon.alt = '';
    } else {
      icon.textContent = (guild.name || '?').slice(0, 1).toUpperCase();
    }
    const details = document.createElement('div');
    details.innerHTML = `<div class="guild-name">${escapeHtml(guild.name || 'Servidor')}</div><a class="guild-action" href="${inviteBase}&guild_id=${encodeURIComponent(guild.id)}&disable_guild_select=true" target="_blank" rel="noopener noreferrer">Invitar Vantarmor ↗</a>`;
    card.append(icon, details);
    guildGrid.append(card);
  }
}

async function loadGuilds() {
  guildStatus.textContent = 'Cargando tus servidores…';
  try {
    const response = await fetch('/api/guilds', {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
    if (response.status === 401) {
      guildStatus.textContent = 'Inicia sesión con Discord para consultar servidores donde puedes añadir el bot.';
      return;
    }
    if (!response.ok) throw new Error('No pudimos cargar tus servidores. Inténtalo otra vez.');
    const data = await response.json();
    drawGuilds(Array.isArray(data.guilds) ? data.guilds : []);
  } catch (error) {
    guildStatus.textContent = error.message || 'No pudimos cargar tus servidores.';
  }
}

function setProfile(user) {
  const name = user?.username || 'Usuario de Discord';
  const initial = name.trim().slice(0, 1).toUpperCase() || 'V';
  profileChip.hidden = false;
  loginButton.hidden = true;
  $('#profile-name').textContent = name;
  $('#profile-avatar').textContent = initial;
  $('#settings-name').textContent = name;
  $('#settings-id').textContent = user?.id ? `ID de Discord: ${user.id}` : 'Sesión iniciada con Discord';
  $('#settings-avatar').textContent = initial;
  $('#settings-login').hidden = true;
  $('#settings-logout').hidden = false;
}

async function init() {
  try {
    const response = await fetch('/api/me', {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
    if (response.ok) {
      const data = await response.json();
      setProfile(data.user || {});
      await loadGuilds();
    }
  } catch (_) {
    // La página pública sigue disponible si no se puede consultar la sesión.
  }
}

$('#refresh-guilds').addEventListener('click', loadGuilds);
init();
