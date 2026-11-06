"""Lifetime Premium entitlements and one-time key management for Vantarmor.

Set DATA_DIR to a persistent Railway volume mount to preserve keys and grants
across redeploys. The owner ID can be overridden with PREMIUM_OWNER_ID.
"""
import hashlib
import json
import os
import secrets
import threading
import time
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


def issue_key(created_by):
    # The plaintext key is returned once and never stored on disk.
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
        if not record:
            return False, "La key no es válida."
        if record.get("redeemed_by"):
            return False, "Esta key ya fue canjeada."
        record["redeemed_by"] = uid
        data["users"][uid] = {"source": "key", "granted_at": int(time.time()), "by": "key"}
        _write(data)
    return True, "Premium vitalicio activado para tu cuenta."


def grant_user(user_id, granted_by):
    uid = str(int(user_id))
    with _LOCK:
        data = _read()
        data["users"][uid] = {"source": "whitelist", "granted_at": int(time.time()), "by": str(granted_by)}
        _write(data)
    return uid


def revoke_user(user_id):
    uid = str(int(user_id))
    with _LOCK:
        data = _read()
        existed = uid in data["users"]
        data["users"].pop(uid, None)
        _write(data)
    return existed


def has_premium(user_id):
    with _LOCK:
        return str(int(user_id)) in _read()["users"]


def register_commands(tree, discord, app_commands, guild):
    """Register management commands in the same guild synced by app.py."""
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

    return True
