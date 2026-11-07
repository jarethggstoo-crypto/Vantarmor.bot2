"""Owner-approval flow for newly joined Discord bot accounts."""
import asyncio
import re
import time

PENDING_SECONDS = 600


class BotApprovalView:
    """Factory is used after discord.py is available in the runtime app."""


def register(tree, client, discord, app_commands, guild_object, config, save_config, premium_system):
    class ApprovalView(discord.ui.View):
        def __init__(self, guild_id, bot_id, owner_id):
            super().__init__(timeout=PENDING_SECONDS)
            self.guild_id = guild_id
            self.bot_id = bot_id
            self.owner_id = owner_id
            self.resolved = False

        async def interaction_check(self, interaction):
            if interaction.user.id != self.owner_id:
                await interaction.response.send_message(
                    "Solo el propietario del servidor puede autorizar este bot.", ephemeral=True
                )
                return False
            if self.resolved:
                await interaction.response.send_message("Esta solicitud ya fue resuelta.", ephemeral=True)
                return False
            return True

        async def on_timeout(self):
            if self.resolved:
                return
            self.resolved = True
            guild = client.get_guild(self.guild_id)
            member = guild.get_member(self.bot_id) if guild else None
            if member:
                try:
                    await member.kick(reason="No recibió autorización en 10 minutos (anti-bots Premium)")
                except (discord.Forbidden, discord.HTTPException) as error:
                    print(f"Anti-bots: no se pudo expulsar el bot {self.bot_id}: {type(error).__name__}")
            for item in self.children:
                item.disabled = True
            if self.message:
                try:
                    await self.message.edit(
                        content="⌛ No se recibió autorización en 10 minutos. Se intentó expulsar el bot.", view=self
                    )
                except discord.HTTPException:
                    pass

        async def resolve(self, interaction, approve):
            if not await self.interaction_check(interaction):
                return
            self.resolved = True
            guild = client.get_guild(self.guild_id)
            member = guild.get_member(self.bot_id) if guild else None
            if not member and guild:
                try:
                    member = await guild.fetch_member(self.bot_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    member = None
            if approve:
                result = f"✅ {member.mention if member else 'El bot'} fue autorizado por el propietario." \
                    if member else "El bot ya no está en el servidor; solicitud cerrada."
            elif member:
                try:
                    await member.kick(reason=f"Bot rechazado por el propietario {interaction.user.id}")
                    result = f"❌ {member} fue expulsado por decisión del propietario."
                except (discord.Forbidden, discord.HTTPException):
                    result = "No pude expulsar el bot. Revisa los permisos y la jerarquía del bot."
            else:
                result = "El bot ya no está en el servidor."
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(content=result, view=self)

        @discord.ui.button(label="Autorizar ✅", style=discord.ButtonStyle.secondary, custom_id="anti_bots:approve")
        async def approve_button(self, interaction, button):
            await self.resolve(interaction, True)

        @discord.ui.button(label="Rechazar ❌", style=discord.ButtonStyle.danger, custom_id="anti_bots:reject")
        async def reject_button(self, interaction, button):
            await self.resolve(interaction, False)

    async def handle_bot_join(member):
        if not member.bot or not config.get("anti_bots", {}).get(str(member.guild.id), False):
            return
        guild = member.guild
        owner = guild.owner or client.get_user(guild.owner_id)
        if owner is None:
            try:
                owner = await client.fetch_user(guild.owner_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                owner = None
        if owner is None:
            try:
                await member.kick(reason="No se pudo contactar al propietario para la aprobación anti-bots")
            except (discord.Forbidden, discord.HTTPException):
                pass
            return

        view = ApprovalView(guild.id, member.id, guild.owner_id)
        text = (
            f"🤖 **Solicitud de autorización de bot**\n"
            f"Bot/app: **{discord.utils.escape_markdown(member.name)}** (`{member.id}`)\n\n"
            "Este bot es nuevo para el servidor. El propietario debe autorizarlo para que permanezca. "
            "Selecciona una opción; si no hay decisión en 10 minutos, el bot será expulsado."
        )
        log_id = config.get("audit_log", {}).get(str(guild.id))
        channel = guild.get_channel(int(log_id)) if log_id else None
        try:
            if channel and hasattr(channel, "send"):
                view.message = await channel.send(text, view=view, allowed_mentions=discord.AllowedMentions.none())
            else:
                view.message = await owner.send(text, view=view)
        except (discord.Forbidden, discord.HTTPException):
            try:
                view.message = await owner.send(text, view=view)
            except (discord.Forbidden, discord.HTTPException):
                print(f"Anti-bots: no se pudo notificar al propietario del servidor {guild.id}")
                try:
                    await member.kick(reason="No se pudo entregar la solicitud de autorización anti-bots")
                except (discord.Forbidden, discord.HTTPException):
                    pass

    @tree.command(name="anti-bots", description="Premium: solicita autorización para bots nuevos", guild=guild_object)
    @app_commands.choices(accion=[
        app_commands.Choice(name="activar", value="activar"),
        app_commands.Choice(name="desactivar", value="desactivar"),
    ])
    @app_commands.describe(accion="Activa o desactiva la aprobación de bots nuevos")
    async def anti_bots_command(interaction: discord.Interaction, accion: app_commands.Choice[str]):
        if not await premium_system.require_premium(interaction):
            return
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Usa este comando dentro de un servidor.", ephemeral=True)
            return
        if not (interaction.user.guild_permissions.manage_guild or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("Necesitas Administrar servidor para configurar anti-bots.", ephemeral=True)
            return
        key = str(interaction.guild.id)
        if accion.value == "activar":
            config.setdefault("anti_bots", {})[key] = True
            save_config()
            await interaction.response.send_message(
                "✅ Anti-bots Premium activado. Los bots nuevos esperarán aprobación del propietario; sin decisión en 10 minutos se intentará expulsarlos.",
                ephemeral=True,
            )
        else:
            config.setdefault("anti_bots", {}).pop(key, None)
            save_config()
            await interaction.response.send_message("✅ Anti-bots Premium desactivado.", ephemeral=True)

    return handle_bot_join


def patch_app_file(app_file):
    """Inject registration and member-join hook into app.py idempotently."""
    source = app_file.read_text(encoding="utf-8")
    if "import premium_system" not in source:
        source = source.replace("import discord\n", "import discord\nimport premium_system\nimport premium_antibots\n", 1)
    elif "import premium_antibots" not in source:
        source = source.replace("import discord\n", "import discord\nimport premium_antibots\n", 1)
    defaults_start = source.find("CONFIG_DEFAULTS = {")
    if defaults_start < 0:
        raise RuntimeError("No encontré CONFIG_DEFAULTS para anti-bots.")
    defaults_end = source.find("\n}", defaults_start)
    if defaults_end < 0:
        raise RuntimeError("CONFIG_DEFAULTS no está cerrado correctamente.")
    defaults = source[defaults_start:defaults_end]
    if '"anti_bots"' not in defaults and "'anti_bots'" not in defaults:
        updated, count = re.subn(r'("antilink"\s*:\s*\{\}\s*,?)', r'\1 "anti_bots": {},', defaults, count=1)
        if count == 1:
            source = source[:defaults_start] + updated + source[defaults_end:]

    hook = "    await anti_bots_on_member_join(member)\n"
    if hook not in source:
        marker = "async def on_member_join(member):\n"
        if marker not in source:
            raise RuntimeError("No encontré on_member_join para conectar la aprobación de bots.")
        source = source.replace(marker, marker + hook, 1)

    registration = "anti_bots_on_member_join = premium_antibots.register(tree, client, discord, app_commands, GUILD, config, save_config, premium_system)"
    if registration not in source:
        marker = "client.run(TOKEN)"
        if marker not in source:
            raise RuntimeError("No encontré client.run(TOKEN) para registrar anti-bots.")
        source = source.replace(marker, registration + "\n\n" + marker, 1)
    app_file.write_text(source, encoding="utf-8")
