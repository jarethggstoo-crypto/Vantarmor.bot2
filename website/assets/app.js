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
  inicio: 'Inicio', funciones: 'Funciones y comandos', estado: 'Estado y protección',
  invitar: 'Invitar bot', planes: 'Planes', ajustes: 'Ajustes',
};
const inviteBase = 'https://discord.com/oauth2/authorize?client_id=1567331667826311288&scope=bot%20applications.commands&permissions=0';
let discordVerified = false;

function createVerificationGate() {
  const style = document.createElement('style');
  style.textContent = `.discord-gate{position:fixed;inset:0;z-index:20;display:grid;place-items:center;padding:22px;background:rgba(0,0,0,.78);backdrop-filter:blur(12px)}.discord-gate-card{width:min(440px,100%);padding:32px;border:1px solid #444;border-radius:16px;background:linear-gradient(145deg,#151515,#080808);box-shadow:0 30px 100px #000;color:#f7f7f7;text-align:center}.discord-gate-mark{width:54px;height:54px;margin:0 auto 20px;display:grid;place-items:center;border-radius:15px;background:#fff;color:#050505;font:700 27px 'Space Grotesk',sans-serif}.discord-gate-card .gate-eyebrow{color:#aaa;font:700 9px 'DM Sans',sans-serif;letter-spacing:.18em}.discord-gate-card h2{margin:12px 0;font:600 27px 'Space Grotesk',sans-serif;letter-spacing:-.04em}.discord-gate-card p{color:#aaa;font:12px/1.7 'DM Sans',sans-serif;margin:0 auto 22px}.discord-gate-link{display:inline-flex;justify-content:center;align-items:center;gap:10px;padding:13px 20px;border-radius:8px;background:#fff;color:#050505;text-decoration:none;font:700 12px 'DM Sans',sans-serif}.discord-gate-note{display:block;color:#777;font:9px/1.6 'DM Sans',sans-serif;margin-top:16px}.discord-gate[hidden]{display:none!important}`;
  document.head.append(style);
  const gate = document.createElement('div');
  gate.className = 'discord-gate';
  gate.hidden = true;
  gate.innerHTML = `<section class="discord-gate-card" role="dialog" aria-modal="true" aria-labelledby="discord-gate-title"><div class="discord-gate-mark" aria-hidden="true">V</div><div class="gate-eyebrow">VERIFICACIÓN DE CUENTA</div><h2 id="discord-gate-title">Continúa con Discord</h2><p>Para entrar a Vantarmor Commands, confirma tu identidad autorizando el inicio de sesión oficial de Discord.</p><a class="discord-gate-link" href="/auth/discord">Verificar con Discord <span aria-hidden="true">↗</span></a><small class="discord-gate-note">Nunca te pediremos la contraseña ni el token de tu cuenta. La autorización se realiza en Discord.</small></section>`;
  document.body.append(gate);
  return gate;
}
const verificationGate = createVerificationGate();
function setVerified(value) {
  discordVerified = value;
  verificationGate.hidden = value;
  document.body.classList.toggle('discord-verification-required', !value);
  if (value) {
    const status = $('#top-status');
    if (status) status.innerHTML = '<i></i> Discord verificado';
  }
}

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
  if (updateHistory && location.hash !== `#${activeView}`) history.pushState({view: activeView}, '', `#${activeView}`);
  setMenu(false);
  window.scrollTo({top: 0, behavior: 'smooth'});
}

menuToggle.addEventListener('click', () => setMenu(menuToggle.getAttribute('aria-expanded') !== 'true'));
$('#menu-close').addEventListener('click', () => setMenu(false));
backdrop.addEventListener('click', () => setMenu(false));
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
    if (!response.ok) {
      setVerified(false);
      return;
    }
    const data = await response.json();
    setVerified(true);
    setProfile(data.user || {});
    await loadGuilds();
  } catch (_) {
    setVerified(false);
  }
}

$('#refresh-guilds').addEventListener('click', loadGuilds);
init();
