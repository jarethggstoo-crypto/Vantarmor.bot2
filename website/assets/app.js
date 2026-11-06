const $ = (selector) => document.querySelector(selector);
const guildSection = $('#servidores');
const guildGrid = $('#guild-grid');
const guildStatus = $('#guild-status');
const loginButton = $('#login-button');
const accountArea = $('#account-area');
const supportLink = $('#support-link');

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}

function botInviteUrl() {
  return 'https://discord.com/oauth2/authorize?client_id=1567331667826311288&scope=bot%20applications.commands&permissions=0';
}

function renderGuilds(guilds) {
  guildGrid.replaceChildren();
  if (!guilds.length) {
    guildStatus.textContent = 'No encontramos servidores donde tengas permisos de administración. Puedes añadir Vantarmor desde el botón de invitación.';
    return;
  }
  guildStatus.textContent = `Encontramos ${guilds.length} servidor${guilds.length === 1 ? '' : 'es'} que puedes administrar.`;
  guilds.forEach((guild) => {
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
    details.innerHTML = `<div class="guild-name">${escapeHtml(guild.name || 'Servidor')}</div><a class="guild-action" href="${botInviteUrl()}&guild_id=${encodeURIComponent(guild.id)}&disable_guild_select=true" target="_blank" rel="noopener noreferrer">Añadir Vantarmor ↗</a>`;
    card.append(icon, details);
    guildGrid.append(card);
  });
}

async function loadGuilds() {
  guildStatus.textContent = 'Cargando tus servidores…';
  try {
    const response = await fetch('/api/guilds', {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
    if (response.status === 401) {
      guildStatus.textContent = 'Inicia sesión con Discord para ver tus servidores.';
      return;
    }
    if (!response.ok) throw new Error('No pudimos consultar tus servidores. Inténtalo de nuevo.');
    const data = await response.json();
    renderGuilds(Array.isArray(data.guilds) ? data.guilds : []);
  } catch (error) {
    guildStatus.textContent = error.message || 'No pudimos consultar tus servidores.';
  }
}

async function init() {
  try {
    const configResponse = await fetch('/config.json', {credentials: 'same-origin'});
    const config = await configResponse.json();
    if (config.support_url) {
      supportLink.href = config.support_url;
      supportLink.target = '_blank';
      supportLink.rel = 'noopener noreferrer';
      supportLink.hidden = false;
    }
    const meResponse = await fetch('/api/me', {credentials: 'same-origin'});
    if (meResponse.ok) {
      const data = await meResponse.json();
      guildSection.hidden = false;
      loginButton.textContent = `Hola, ${data.user?.username || 'Discord'}`;
      loginButton.href = '/auth/logout';
      loginButton.classList.add('button-outline');
      loginButton.setAttribute('aria-label', 'Cerrar sesión');
      loginButton.insertAdjacentText('beforeend', ' · Salir');
      await loadGuilds();
    }
    if (!config.auth_enabled) {
      loginButton.title = 'El administrador debe configurar Discord OAuth en Railway.';
      loginButton.addEventListener('click', (event) => {
        event.preventDefault();
        alert('El inicio de sesión aún no está configurado. Añade DISCORD_CLIENT_SECRET y DISCORD_REDIRECT_URI en Railway.');
      });
    }
  } catch (_) {
    // The public landing page remains available if OAuth is not configured.
  }
}

$('#refresh-guilds')?.addEventListener('click', loadGuilds);
init();
