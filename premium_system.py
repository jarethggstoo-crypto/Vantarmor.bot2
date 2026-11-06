"""Lifetime Premium entitlements and one-time key management for Vantarmor."""
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

OWNER_ID = int(os.getenv("PREMIUM_OWNER_ID", "1522361078237892628"))
DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).resolve().parent)))
DATA_FILE = DATA_DIR / "premium_data.json"
_LOCK = threading.RLock()


def _read():
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("keys", {})
    data.setdefault("users", {})
    return data


def _write(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = DATA_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, DATA_FILE)


def _key_hash(key):
    return hashlib.sha256(key.strip().upper().encode("utf-8")).hexdigest()


def notify_discord_user(user_id, message):
    """Best-effort private notice from the bot; entitlement remains saved if DM fails."""
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        return False
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "Vantarmor Premium",
    }

    def discord_post(path, payload):
        request = urllib.request.Request(
            f"https://discord.com/api/v10{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=4) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        dm = discord_post("/users/@me/channels", {"recipient_id": str(int(user_id))})
        discord_post(f"/channels/{dm['id']}/messages", {"content": message})
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError, ValueError, TypeError) as error:
        print(f"No se pudo enviar notificación Premium por DM; tipo={type(error).__name__}")
        return False


def issue_key(created_by):
    raw = "VANTARMOR-" + secrets.token_urlsafe(18).replace("-", "").replace("_", "").upper()
    with _LOCK:
        data = _read()
        data["keys"][_key_hash(raw)] = {"created_by": str(created_by), "created_at": int(time.time()), "redeemed_by": None}
        _write(data)
    return raw


def redeem_key(user_id, key):
    uid = str(int(user_id))
    digest = _key_hash(key)
    with _LOCK:
        data = _read()
        record = data["keys"].get(digest)
        if not record or record.get("revoked"):
            return False, "La key no es válida o fue revocada."
        if record.get("redeemed_by"):
            return False, "Esta key ya fue canjeada."
        record["redeemed_by"] = uid
        data["users"][uid] = {"source": "key", "key_hash": digest, "granted_at": int(time.time()), "by": "key"}
        _write(data)
    notify_discord_user(uid, "✅ Tu cuenta de Discord ya tiene Premium vitalicio en Vantarmor. El bot reconoce tu acceso. Si aún no ves comandos Premium, vuelve a abrir Discord y consulta al administrador: las funciones Premium disponibles dependen de los comandos publicados por el bot.")
    return True, "Premium vitalicio activado para tu cuenta de Discord. El bot fue avisado; revisa tus mensajes directos de Discord."


def revoke_key(key):
    digest = _key_hash(key)
    with _LOCK:
        data = _read()
        record = data["keys"].get(digest)
        if not record:
            return False, "No encontré esa key. No se modificó ningún Premium."
        if record.get("revoked"):
            return False, "Esa key ya estaba revocada."
        record["revoked"] = True
        record["revoked_at"] = int(time.time())
        uid = str(record.get("redeemed_by") or "")
        entitlement = data["users"].get(uid) if uid else None
        removed = False
        legacy_unlinked = False
        if entitlement and entitlement.get("source") == "key":
            if entitlement.get("key_hash") == digest:
                data["users"].pop(uid, None)
                removed = True
            elif not entitlement.get("key_hash"):
                legacy_unlinked = True
        _write(data)
    if removed:
        notify_discord_user(uid, "ℹ️ Se revocó el acceso Premium de esta cuenta en Vantarmor.")
        return True, f"Key revocada y Premium quitado al usuario {uid}."
    if not uid:
        return True, "Key revocada. No tenía un canje asociado."
    if legacy_unlinked:
        return True, f"Key revocada para el usuario {uid}; su acceso anterior no se pudo asociar con seguridad a esta key y no se quitó. Usa /premium-revocar con su ID para revocar manualmente."
    return True, f"Key revocada. El usuario {uid} conserva Premium porque su acceso proviene de otra autorización."


def grant_user(user_id, granted_by):
    uid = str(int(user_id))
    with _LOCK:
        data = _read()
        data["users"][uid] = {"source": "whitelist", "granted_at": int(time.time()), "by": str(granted_by)}
        _write(data)
    notify_discord_user(uid, "✅ El propietario activó Premium vitalicio en tu cuenta de Vantarmor. El bot ya registra tu acceso.")
    return uid


def revoke_user(user_id):
    uid = str(int(user_id))
    with _LOCK:
        data = _read()
        existed = uid in data["users"]
        data["users"].pop(uid, None)
        _write(data)
    if existed:
        notify_discord_user(uid, "ℹ️ Se revocó el acceso Premium de esta cuenta en Vantarmor.")
    return existed


def has_premium(user_id):
    with _LOCK:
        return str(int(user_id)) in _read()["users"]


def register_commands(tree, discord, app_commands, guild):
    @tree.command(name="premium-key", description="[Owner] Genera una key Premium de un solo uso", guild=guild)
    async def premium_key_command(interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("No tienes permiso para administrar Premium.", ephemeral=True)
            return
        key = issue_key(interaction.user.id)
        await interaction.response.send_message(f"Key Premium vitalicia (muéstrala solo al comprador):\n`{key}`", ephemeral=True)

    @tree.command(name="premium-canjear", description="Canjea una key Premium de un solo uso", guild=guild)
    @app_commands.describe(key="Key Premium recibida")
    async def premium_redeem_command(interaction: discord.Interaction, key: str):
        if len(key) > 100:
            await interaction.response.send_message("La key no es válida.", ephemeral=True)
            return
        ok, message = redeem_key(interaction.user.id, key)
        await interaction.response.send_message(message, ephemeral=True)

    @tree.command(name="premium-whitelist", description="[Owner] Activa Premium vitalicio sin key a un usuario", guild=guild)
    @app_commands.describe(usuario="Usuario al que otorgar Premium")
    async def premium_whitelist_command(interaction: discord.Interaction, usuario: discord.User):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("No tienes permiso para administrar Premium.", ephemeral=True)
            return
        grant_user(usuario.id, interaction.user.id)
        await interaction.response.send_message(f"Premium vitalicio activado para {usuario.mention} (ID `{usuario.id}`).", ephemeral=True)

    @tree.command(name="premium-revocar", description="[Owner] Revoca el Premium de un usuario", guild=guild)
    @app_commands.describe(usuario="Usuario al que quitar Premium")
    async def premium_revoke_command(interaction: discord.Interaction, usuario: discord.User):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("No tienes permiso para administrar Premium.", ephemeral=True)
            return
        if revoke_user(usuario.id):
            await interaction.response.send_message(f"Se revocó Premium a {usuario.mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("Ese usuario no tenía Premium activo.", ephemeral=True)

    @tree.command(name="key-revocar", description="[Owner] Revoca una key y su Premium asociado", guild=guild)
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(key="Key Premium que quieres revocar")
    async def key_revoke_command(interaction: discord.Interaction, key: str):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("No tienes permiso para revocar keys Premium.", ephemeral=True)
            return
        if not key.strip() or len(key) > 100:
            await interaction.response.send_message("Escribe una key válida.", ephemeral=True)
            return
        _, message = revoke_key(key)
        await interaction.response.send_message(message, ephemeral=True)

    return True
