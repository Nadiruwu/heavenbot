import discord
from discord.ext import commands
from discord import ui
from discord.ui import Button, View, Modal, TextInput, Select
import json
import asyncio
import os
import sqlite3
import aiohttp
from dotenv import load_dotenv

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="h!", intents=intents, help_command=None)

DB_FILE = "databaseheaven.json"
VANITY_ROLES = {"nvn": 1284285993494773800}
AUTHORIZED_USERS = {1084586006939975861}
AUTHORIZED_ROLES = {}
ROL_PROHIBIDO_ID = 1337652194069188691
BACKUP_FILE = "channel_backup.json"
guarded_channels = {}
SERVER_ID = 1142939786533933086
def create_table():
    conn = sqlite3.connect("your_database.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS channels (
        channel_id INTEGER PRIMARY KEY,
        owner_id INTEGER,
        visibility TEXT DEFAULT 'public'
    )
    """)
    conn.commit()
    conn.close()

create_table()
class VCControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.user_select_menu = UserSelectMenu()
        self.add_item(self.user_select_menu)

    @discord.ui.button(label="🔓 Abrir", style=discord.ButtonStyle.green, row=0)
    async def open_vc(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        channel = interaction.user.voice.channel if interaction.user.voice else None

        if not channel:
            await interaction.followup.send(embed=self.create_embed("❌ No estás en un canal de voz."), ephemeral=True)
            return

        owner_id = get_channel_owner_by_id(channel.id)
        if owner_id != interaction.user.id:
            await interaction.followup.send(embed=self.create_embed("❌ No eres el dueño de este canal."), ephemeral=True)
            return

        await channel.set_permissions(interaction.guild.default_role, connect=True)
        await interaction.followup.send(embed=self.create_embed(f"✅ El canal **{channel.name}** está ahora **abierto**."), ephemeral=True)

    @discord.ui.button(label="🔒 Cerrar", style=discord.ButtonStyle.red, row=0)
    async def close_vc(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        channel = interaction.user.voice.channel if interaction.user.voice else None

        if not channel:
            await interaction.followup.send(embed=self.create_embed("❌ No estás en un canal de voz."), ephemeral=True)
            return

        owner_id = get_channel_owner_by_id(channel.id)
        if owner_id != interaction.user.id:
            await interaction.followup.send(embed=self.create_embed("❌ No eres el dueño de este canal."), ephemeral=True)
            return

        await channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.followup.send(embed=self.create_embed(f"✅ El canal **{channel.name}** está ahora **cerrado**."), ephemeral=True)

    @discord.ui.button(label="✏️ Renombrar", style=discord.ButtonStyle.blurple, row=1)
    async def rename_vc(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(RenameModal())

    @discord.ui.button(label="🗑️ Eliminar", style=discord.ButtonStyle.red, row=2)
    async def delete_vc(self, interaction: discord.Interaction, button: Button):
        channel = interaction.user.voice.channel if interaction.user.voice else None

        if not channel:
            await interaction.response.send_message(embed=self.create_embed("❌ No estás en un canal de voz."), ephemeral=True)
            return

        owner_id = get_channel_owner_by_id(channel.id)
        if owner_id != interaction.user.id:
            await interaction.response.send_message(embed=self.create_embed("❌ No eres el dueño de este canal."), ephemeral=True)
            return

        confirm_embed = discord.Embed(title="⚠️ Confirmar Eliminación", description="¿Estás seguro de que quieres eliminar este canal?", color=discord.Color.red())
        view = DeleteConfirmationView(channel, interaction.user)
        await interaction.response.send_message(embed=confirm_embed, view=view, ephemeral=True)
        
        await view.wait()
        if view.result is True:
            await channel.delete()
            await interaction.followup.send(embed=self.create_embed(f"✅ El canal **{channel.name}** ha sido eliminado."), ephemeral=True)
        else:
            await interaction.followup.send(embed=self.create_embed("❌ Eliminación cancelada."), ephemeral=True)

    @staticmethod
    def create_embed(message: str) -> discord.Embed:
        return discord.Embed(description=message, color=discord.Color.blue())

class RenameModal(Modal):
    def __init__(self):
        super().__init__(title="Renombrar Canal")
        self.new_name = TextInput(label="Nuevo Nombre")
        self.add_item(self.new_name)
    
    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.user.voice.channel if interaction.user.voice else None

        if not channel:
            await interaction.response.send_message(embed=VCControlView.create_embed("❌ No estás en un canal de voz."), ephemeral=True)
            return

        owner_id = get_channel_owner_by_id(channel.id)
        if owner_id != interaction.user.id:
            await interaction.response.send_message(embed=VCControlView.create_embed("❌ No eres el dueño de este canal."), ephemeral=True)
            return

        await channel.edit(name=self.new_name.value)
        await interaction.response.send_message(embed=VCControlView.create_embed(f"✅ Canal renombrado a: **{self.new_name.value}**"), ephemeral=True)

class UserSelectMenu(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Selecciona un usuario", min_values=1, max_values=1)

    async def update_options(self, interaction):
        # Agregar opciones de miembros cuando se muestre el menú
        options = [
            discord.SelectOption(label=member.display_name, value=str(member.id))
            for member in interaction.guild.members
            if member.voice  # Solo miembros que están en un canal de voz
        ]
        self.options = options

    async def callback(self, interaction: discord.Interaction):
        # Obtener el canal de voz del usuario que interactuó
        channel = interaction.user.voice.channel if interaction.user.voice else None
        if not channel:
            await interaction.response.send_message(embed=VCControlView.create_embed("❌ No estás en un canal de voz."), ephemeral=True)
            return

        # Verificar si el usuario es el dueño del canal
        owner_id = get_channel_owner_by_id(channel.id)  # Asumimos que esta función existe
        if owner_id != interaction.user.id:
            await interaction.response.send_message(embed=VCControlView.create_embed("❌ No eres el dueño de este canal."), ephemeral=True)
            return

        # Obtener el miembro seleccionado en el menú
        member = interaction.guild.get_member(int(self.values[0]))
        if not member:
            await interaction.response.send_message(embed=VCControlView.create_embed("❌ Usuario no encontrado."), ephemeral=True)
            return

        # Verificar qué acción se está tomando según el custom_id
        action = interaction.custom_id  # Este ID se debe definir cuando añades el Select al View

        if action == "permit":
            # Permitir que el miembro se una al canal
            await channel.set_permissions(member, connect=True)
            await interaction.response.send_message(embed=VCControlView.create_embed(f"✅ Se ha permitido a **{member.display_name}** unirse al canal."), ephemeral=True)

        elif action == "kick":
            # Expulsar al miembro del canal si está presente
            if member in channel.members:
                await member.move_to(None)
                await interaction.response.send_message(embed=VCControlView.create_embed(f"✅ **{member.display_name}** ha sido expulsado del canal."), ephemeral=True)
            else:
                await interaction.response.send_message(embed=VCControlView.create_embed("❌ El usuario no está en el canal."), ephemeral=True)

        elif action == "ban":
            # Baneamos al miembro, impidiéndole unirse al canal
            await channel.set_permissions(member, connect=False)
            await interaction.response.send_message(embed=VCControlView.create_embed(f"✅ **{member.display_name}** ha sido baneado del canal."), ephemeral=True)

        else:
            await interaction.response.send_message(embed=VCControlView.create_embed("❌ Acción no válida."), ephemeral=True)

class PermissionModal(Modal):
    def __init__(self, action):
        super().__init__(title=f"{action.capitalize()} Usuario")
        self.action = action
        self.username = TextInput(label="Usuario (ID o mención)")
        self.add_item(self.username)
class DeleteConfirmationView(View):
    def __init__(self, channel, user):
        super().__init__(timeout=30)
        self.channel = channel
        self.user = user
        self.result = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(embed=VCControlView.create_embed("❌ No puedes usar este panel."), ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Sí", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        self.result = True
        self.stop()

    @discord.ui.button(label="❌ No", style=discord.ButtonStyle.gray)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        self.result = False
        self.stop()
    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.user.voice.channel
        try:
            user_id = int(self.username.value)
            member = interaction.guild.get_member(user_id)
            if not member:
                await interaction.response.send_message("❌ Usuario no encontrado.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ ID de usuario no válido.", ephemeral=True)
            return

        if self.action == "permit":
            await channel.set_permissions(member, connect=True)
            embed = discord.Embed(title="✅ Permiso Concedido", description=f"**{member.display_name}** ahora puede unirse.", color=discord.Color.green())

        await interaction.response.send_message(embed=embed, ephemeral=True)
# Función para obtener el dueño de un canal
def get_channel_owner_by_id(channel_id):
    conn = sqlite3.connect("your_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT owner_id FROM channels WHERE channel_id = ?", (channel_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Función para configurar el canal de interfaz
async def setup_interface_channel(guild):
    existing_channel = discord.utils.get(guild.text_channels, name="interfaz")
    if not existing_channel:
        channel = await guild.create_text_channel("interfaz")
    else:
        channel = existing_channel
    return channel
def get_channel_owner_by_id(channel_id):
    conn = sqlite3.connect("your_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT owner_id FROM channels WHERE channel_id = ?", (channel_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

async def setup_interface_channel(guild):
    existing_channel = discord.utils.get(guild.text_channels, name="interfaz")
    if not existing_channel:
        channel = await guild.create_text_channel("interfaz")
    else:
        channel = existing_channel
    return channel
def load_database():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    required_keys = ["autoResponses", "autoReactions" ]
    for key in required_keys:
        if key not in data:
            data[key] = {}

    return data

def save_database():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=2)

database = load_database()

def load_backup():
    if os.path.exists(BACKUP_FILE):
        if os.stat(BACKUP_FILE).st_size == 0:
            return {}
        with open(BACKUP_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_backup(data):
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

channel_backup = load_backup()

async def restore_your_database():
    conn = sqlite3.connect("your_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM channels")
    rows = cursor.fetchall()
    conn.close()

    guild = guild = bot.get_guild(SERVER_ID)

    for row in rows:
        channel_id, owner_id, visibility = row
        channel = discord.utils.get(guild.channels, id=channel_id)

        if channel:
            owner = guild.get_member(owner_id)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=False),
                owner: discord.PermissionOverwrite(connect=True) if owner else None
            } if visibility == "private" else {
                guild.default_role: discord.PermissionOverwrite(connect=True)
            }
            await channel.edit(overwrites=overwrites)

@bot.event
async def on_ready():
    conn = sqlite3.connect("your_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            role_id INTEGER PRIMARY KEY,
            name TEXT,
            permissions INTEGER,
            color INTEGER,
            hoist BOOLEAN,
            mentionable BOOLEAN,
            icon TEXT
        )
    """)
    
    for guild in bot.guilds:
        for role in guild.roles:
            cursor.execute("INSERT OR REPLACE INTO roles (role_id, name, permissions, color, hoist, mentionable, icon) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (role.id, role.name, role.permissions.value, role.color.value, role.hoist, role.mentionable, role.display_icon.url if role.display_icon else None))
    
    conn.commit()
    conn.close()
    print("✅ Todos los roles han sido registrados en la base de datos.")
    guild = bot.get_guild(SERVER_ID)
    rol_prohibido = guild.get_role(ROL_PROHIBIDO_ID)
    global guarded_channels
    guarded_channels.clear()
    for channel in guild.channels:
        await channel.set_permissions(rol_prohibido, read_messages=False, send_messages=False)
    print(f"Bot conectado y permisos negados al rol {rol_prohibido.name}")
    for guild in bot.guilds:
        for category in guild.categories:
            if category.id != 1337654394589675591:
                guarded_channels[category.id] = [
                    (ch.name, type(ch), ch.overwrites, ch.position) for ch in category.channels
                ]
    channel = await setup_interface_channel(guild)
    await channel.purge()
    embed = discord.Embed(
        title="🎛️ Panel de Gestión de Canales de Voz",
        description="Controla tu canal de voz con los botones a continuación.",
        color=discord.Color.blue() )
    view = VCControlView()
    embed = discord.Embed(title="Selecciona un Usuario", description="Selecciona un miembro del canal de voz.")
    await view.user_select_menu.update_options(interaction=None)
    embed.set_footer(text="Sistema de Gestión de Canales de Voz")
    await channel.send(embed=embed, view=view)
    print(f"Interfaz de control enviada en {channel.name}")
    print("Estructura del servidor guardada.")
    await bot.change_presence(activity=discord.Game("Trabajando en Heaven"))
    await restore_your_database()
@bot.event
async def on_presence_update(before, after):
    if not after or not after.activities:
        return
    assigned_roles = set()
    for activity in after.activities:
        if isinstance(activity, discord.CustomActivity) and activity.name:
            for vanity, role_id in VANITY_ROLES.items():
                if vanity in activity.name:
                    assigned_roles.add(role_id)
    await update_member_roles(after, assigned_roles)

async def update_member_roles(member, assigned_roles):
    current_roles = {role.id for role in member.roles}
    for role_id in assigned_roles:
        if role_id not in current_roles:
            role = member.guild.get_role(role_id)
            if role:
                await member.add_roles(role)
    for role_id in VANITY_ROLES.values():
        if role_id in current_roles and role_id not in assigned_roles:
            role = member.guild.get_role(role_id)
            if role:
                await member.remove_roles(role)
@bot.event
async def on_guild_role_delete(role):
    conn = sqlite3.connect("your_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM roles WHERE role_id = ?", (role.id,))
    data = cursor.fetchone()
    if data:
        restored_role = await role.guild.create_role(
            name=data[1],
            permissions=discord.Permissions(data[2]),
            color=discord.Color(data[3]),
            hoist=bool(data[4]),
            mentionable=bool(data[5])
        )
        if data[6]:
            await restored_role.edit(display_icon=data[6])
        await role.guild.system_channel.send(f'🔄 Se ha restaurado el rol **{restored_role.name}** tras su eliminación.')
    conn.close()

@bot.event
async def on_guild_role_create(role):
    conn = sqlite3.connect("your_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO roles (role_id, name, permissions, color, hoist, mentionable, icon) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (role.id, role.name, role.permissions.value, role.color.value, role.hoist, role.mentionable, role.display_icon.url if role.display_icon else None))
    conn.commit()
    conn.close()
@bot.event
async def on_voice_state_update(member, before, after):
    CATEGORIA_ESPECIFICA_ID = 1337654394589675591  
    CANAL_DE_CREACION_ID = 1337654441305968682  

    if after.channel and after.channel.category and after.channel.category.id == CATEGORIA_ESPECIFICA_ID:
        if after.channel.id == CANAL_DE_CREACION_ID:
            guild = after.channel.guild
            category = after.channel.category

            new_channel = await guild.create_voice_channel(
                name=f"Canal de {member.display_name}",
                category=category,
                reason="Canal de voz creado automáticamente"
            )

            await member.move_to(new_channel)

            conn = sqlite3.connect("your_database.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO channels (channel_id, owner_id, visibility) VALUES (?, ?, ?)",
                           (new_channel.id, member.id, "private"))
            conn.commit()
            conn.close()

            print(f"✅ Canal de voz '{new_channel.name}' creado para {member.display_name}.")

    if before.channel and before.channel.category and before.channel.category.id == CATEGORIA_ESPECIFICA_ID:
        if before.channel.id == CANAL_DE_CREACION_ID:
            return  

        if len(before.channel.members) == 0:
            conn = sqlite3.connect("your_database.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM channels WHERE channel_id = ?", (before.channel.id,))
            conn.commit()
            conn.close()

            await before.channel.delete()
            print(f"❌ Canal de voz '{before.channel.name}' eliminado porque está vacío.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content_lower = message.content.lower()

    if content_lower in database.get("autoResponses", {}):
        await message.channel.send(database["autoResponses"][content_lower])

    if content_lower in database.get("autoReactions", {}):
        await message.add_reaction(database["autoReactions"][content_lower])

    await bot.process_commands(message)

@bot.event
async def on_guild_channel_create(channel):
    guild = channel.guild
    role = guild.get_role(ROL_PROHIBIDO_ID)

    if role:
        await channel.set_permissions(role, view_channel=False)
        print(f"🔒 Se han actualizado los permisos para {role.name} en {channel.name}")

@bot.event
async def on_guild_channel_delete(channel):
    guild = channel.guild
    
    if isinstance(channel, discord.CategoryChannel):
        print(f"Categoría eliminada: {channel.name}")
        category_id = channel.id
        
        channels_to_restore = guarded_channels.get(category_id, [])
        
        new_category = await guild.create_category(name=channel.name, overwrites=channel.overwrites)
        print(f"Categoría '{new_category.name}' recreada.")
        
        await asyncio.sleep(2)
        
        # Recrear los canales dentro de la nueva categoría
        for ch_name, ch_type, ch_overwrites, ch_position in channels_to_restore:
            try:
                if ch_type == discord.TextChannel:
                    new_channel = await guild.create_text_channel(
                        name=ch_name,
                        category=new_category,
                        overwrites=ch_overwrites,
                        position=ch_position
                    )
                elif ch_type == discord.VoiceChannel:
                    new_channel = await guild.create_voice_channel(
                        name=ch_name,
                        category=new_category,
                        overwrites=ch_overwrites,
                        position=ch_position
                    )
                print(f"Canal '{new_channel.name}' recreado en la categoría '{new_category.name}'.")
            except discord.Forbidden:
                print(f"No tengo permisos para recrear el canal '{ch_name}'.")
            except discord.HTTPException as e:
                print(f"Error al recrear el canal '{ch_name}': {e}")
        
        # Actualizar la estructura guardada
        guarded_channels[new_category.id] = channels_to_restore
    
    elif isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
        print(f"Canal eliminado: {channel.name}")
        
        if channel.category and channel.category.id in guarded_channels:
            print(f"Recreando canal '{channel.name}' en su categoría original.")
            
            try:
                if isinstance(channel, discord.TextChannel):
                    new_channel = await guild.create_text_channel(
                        name=channel.name,
                        category=channel.category,
                        overwrites=channel.overwrites,
                        position=channel.position
                    )
                elif isinstance(channel, discord.VoiceChannel):
                    new_channel = await guild.create_voice_channel(
                        name=channel.name,
                        category=channel.category,
                        overwrites=channel.overwrites,
                        position=channel.position
                    )
                print(f"Canal '{new_channel.name}' recreado en la categoría '{channel.category.name}'.")
            except discord.Forbidden:
                print(f"No tengo permisos para recrear el canal '{channel.name}'.")
            except discord.HTTPException as e:
                print(f"Error al recrear el canal '{channel.name}': {e}")
conn = sqlite3.connect("your_database.db")
cursor = conn.cursor()

# Verifica si la columna proof_path ya existe
cursor.execute("PRAGMA table_info(blacklist)")
columns = [col[1] for col in cursor.fetchall()]
if "proof_path" not in columns:
    cursor.execute("ALTER TABLE blacklist ADD COLUMN proof_path TEXT")

conn.commit()
conn.close()
os.makedirs("blacklist_proofs", exist_ok=True)
class HelpView(View):
    def __init__(self, ctx, pages):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.pages = pages
        self.current_page = 0

    async def update_embed(self, interaction):
        embed = discord.Embed(
            color=discord.Color.blue(),
            title=f"Comandos del Bot (Página {self.current_page + 1}/{len(self.pages)})"
        )
        embed.description = self.pages[self.current_page]
        embed.set_footer(text="Desarrollado por codigo0010")
        await interaction.response.edit_message(embed=embed)

    @ui.button(label="Anterior", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_embed(interaction)

    @ui.button(label="Siguiente", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self.update_embed(interaction)

    async def on_timeout(self):
        await self.message.edit(view=None)

@bot.command()
async def help(ctx):
    pages = [
        "📜 **Comandos de Autorespuesta:**\n"
        "`h!addresponse <trigger> <respuesta>` ➝ Agrega una auto-respuesta.\n"
        "`h!delresponse <trigger>` ➝ Elimina una auto-respuesta.\n"
        "`h!addreaction <trigger> <emoji>` ➝ Agrega una auto-reacción.\n"
        "`h!delreaction <trigger>` ➝ Elimina una auto-reacción.",

        "🔧 **Comandos de Administración:**\n"
        "`h!jail <miembro>`: Quita todos los roles de un usuario y le asigna el rol predeterminado.\n"
        "`h!restaurarroles <miembro>`: Restaura los roles eliminados previamente de un usuario.\n"
        "`h!ban <miembro>`: Banea a un usuario del servidor.\n"
        "`h!blacklist add/remove/show <userID>`: Gestiona la lista negra de usuarios.",

        "🎤 **Comandos de Canal de Voz:**\n"
        "`h!togglevc <open/close>`: Abre o cierra el canal de voz.\n"
        "`h!renamevc <nuevo_nombre>`: Cambia el nombre de tu canal de voz privado.\n"
        "`h!deletevc`: Elimina tu canal de voz privado.\n"
        "`h!vcperms <miembro>`: Da acceso a otro usuario a tu canal de voz privado.\n"
        "`h!kickvc <miembro>`: Desconecta a un miembro de tu canal de voz privado.\n"
        "`h!banvc <miembro>`: Prohíbe a un miembro unirse a tu canal de voz privado.\n"
        "`h!viewvc <private/public>`: Cambia la visibilidad del canal de voz.",

        "ℹ️ **Comandos de Información:**\n"
        "`h!user <miembro>`: Muestra la información de un usuario específico o la del autor del comando.\n"
        "`h!help`: Muestra la lista de todos los comandos disponibles."
    ]

    view = HelpView(ctx, pages)
    embed = discord.Embed(
        color=discord.Color.blue(),
        title=f"Comandos del Bot (Página 1/{len(pages)})"
    )
    embed.description = pages[0]
    embed.set_footer(text="Desarrollado por codigo0010")
    view.message = await ctx.send(embed=embed, view=view)

@bot.command()
async def addresponse(ctx, trigger: str, *, response: str):
    if ctx.author.id not in AUTHORIZED_USERS and not any(r.id in AUTHORIZED_ROLES for r in ctx.author.roles):
        await ctx.send("❌ No tienes permisos.")
        return
    database["autoResponses"][trigger.lower()] = response
    save_database()
    await ctx.send(f'✅ Auto-respuesta añadida: **{trigger}** → "{response}"')

@bot.command()
async def delresponse(ctx, trigger: str):
    if ctx.author.id not in AUTHORIZED_USERS and not any(r.id in AUTHORIZED_ROLES for r in ctx.author.roles):
        await ctx.send("❌ No tienes permisos.")
        return
    if trigger.lower() in database["autoResponses"]:
        del database["autoResponses"][trigger.lower()]
        save_database()
        await ctx.send(f'✅ Auto-respuesta eliminada para: **{trigger}**')
    else:
        await ctx.send("❌ No existe esa auto-respuesta.")

@bot.command()
async def addreaction(ctx, trigger: str, emoji: str):
    if ctx.author.id not in AUTHORIZED_USERS and not any(r.id in AUTHORIZED_ROLES for r in ctx.author.roles):
        await ctx.send("❌ No tienes permisos.")
        return
    database["autoReactions"][trigger.lower()] = emoji
    save_database()
    await ctx.send(f'✅ Se ha añadido una reacción automática para **{trigger}** con {emoji}')

@bot.command()
async def delreaction(ctx, trigger: str):
    if ctx.author.id not in AUTHORIZED_USERS and not any(r.id in AUTHORIZED_ROLES for r in ctx.author.roles):
        await ctx.send("❌ No tienes permisos.")
        return
    if trigger.lower() in database["autoReactions"]:
        del database["autoReactions"][trigger.lower()]
        save_database()
        await ctx.send(f'✅ Auto-reacción eliminada para: **{trigger}**')
    else:
        await ctx.send("❌ No existe esa auto-reacción.")

@bot.command()
async def user(ctx, member: discord.Member = None):
    member = member or ctx.author
    roles = ", ".join([role.mention for role in member.roles if role.id != ctx.guild.id]) or "Ningún rol asignado"
    embed = discord.Embed(color=discord.Color.blue(), title=f"Info de {member}")
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="🆔 ID", value=member.id, inline=True)
    embed.add_field(name="📆 Cuenta creada", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="📥 Se unió al servidor", value=member.joined_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="🔰 Roles", value=roles, inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def ban(ctx, member: discord.Member, *, reason="No especificado"):
    if ctx.author.id not in AUTHORIZED_USERS and not any(r.id in AUTHORIZED_ROLES for r in ctx.author.roles):
        await ctx.send("❌ No tienes permisos.")
        return
    await member.ban(reason=reason)
    await ctx.send(f'✅ Usuario {member} baneado por: {reason}')

@bot.command()
async def blacklist(ctx, action: str, user_id: int = None, *, reason: str = "No especificado"):
    if ctx.author.id not in AUTHORIZED_USERS and not any(r.id in AUTHORIZED_ROLES for r in ctx.author.roles):
        await ctx.send("❌ No tienes permisos para ejecutar este comando.")
        return
    
    conn = sqlite3.connect("your_database.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS blacklist (user_id TEXT PRIMARY KEY, reason TEXT, proof_path TEXT)")
    
    embed = discord.Embed(color=discord.Color.red())
    
    if action == "add" and user_id:
        proof_path = "No adjunto"
        
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            proof_path = f"blacklist_proofs/{user_id}_{attachment.filename}"
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as resp:
                    if resp.status == 200:
                        with open(proof_path, "wb") as f:
                            f.write(await resp.read())
        
        cursor.execute("INSERT OR REPLACE INTO blacklist (user_id, reason, proof_path) VALUES (?, ?, ?)", (str(user_id), reason, proof_path))
        conn.commit()
        embed.title = "🚫 Usuario agregado a la Blacklist"
        embed.description = f"✅ El usuario **{user_id}** ha sido añadido a la blacklist."
        embed.add_field(name="📌 Razón", value=reason, inline=False)
        if proof_path != "No adjunto":
            file = discord.File(proof_path, filename=proof_path.split("/")[-1])
            embed.set_image(url=f"attachment://{proof_path.split('/')[-1]}")
            await ctx.send(embed=embed, file=file)
        else:
            await ctx.send(embed=embed)
    elif action == "remove" and user_id:
        cursor.execute("SELECT proof_path FROM blacklist WHERE user_id = ?", (str(user_id),))
        row = cursor.fetchone()
        if row and row[0] != "No adjunto":
            try:
                os.remove(row[0])
            except FileNotFoundError:
                pass
        
        cursor.execute("DELETE FROM blacklist WHERE user_id = ?", (str(user_id),))
        conn.commit()
        embed.title = "✅ Usuario eliminado de la Blacklist"
        embed.description = f"🚀 El usuario **{user_id}** ha sido eliminado de la blacklist."
        await ctx.send(embed=embed)
    elif action == "show":
        cursor.execute("SELECT user_id, reason, proof_path FROM blacklist")
        blacklist_data = cursor.fetchall()
        if blacklist_data:
            pages = [blacklist_data[i:i + 5] for i in range(0, len(blacklist_data), 5)]
            page = 0
            embed.title = "🚫 Blacklist (Página 1)"
            files = []
            
            for uid, reason, proof in pages[page]:
                embed.add_field(name=f"👤 Usuario: {uid}", value=f"📌 Razón: {reason}\n━━━━━━━━━━━━━━", inline=False)
                if os.path.exists(proof) and proof != "No adjunto":
                    file = discord.File(proof, filename=proof.split("/")[-1])
                    embed.set_image(url=f"attachment://{proof.split('/')[-1]}")
                    files.append(file)
            
            if files:
                message = await ctx.send(embed=embed, files=files)
            else:
                message = await ctx.send(embed=embed)
            
            if len(pages) > 1:
                await message.add_reaction("⬅️")
                await message.add_reaction("➡️")
                
                def check(reaction, user):
                    return user == ctx.author and reaction.message.id == message.id and str(reaction.emoji) in ["⬅️", "➡️"]
                
                while True:
                    try:
                        reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
                        if str(reaction.emoji) == "➡️" and page < len(pages) - 1:
                            page += 1
                        elif str(reaction.emoji) == "⬅️" and page > 0:
                            page -= 1
                        embed.clear_fields()
                        embed.title = f"🚫 Blacklist (Página {page + 1})"
                        files = []
                        
                        for uid, reason, proof in pages[page]:
                            embed.add_field(name=f"👤 Usuario: {uid}", value=f"📌 Razón: {reason}\n━━━━━━━━━━━━━━", inline=False)
                            if os.path.exists(proof) and proof != "No adjunto":
                                file = discord.File(proof, filename=proof.split("/")[-1])
                                embed.set_image(url=f"attachment://{proof.split('/')[-1]}")
                                files.append(file)
                        
                        if files:
                            await message.edit(embed=embed, attachments=files)
                        else:
                            await message.edit(embed=embed)
                        await message.remove_reaction(reaction.emoji, user)
                    except asyncio.TimeoutError:
                        break
        else:
            await ctx.send("🚫 La blacklist está vacía.")
    else:
        await ctx.send("❌ Uso incorrecto. Usa `h!blacklist add/remove/show <userID>`." )
    
    conn.close()



@bot.command()
@commands.has_permissions(administrator=True)
async def jail(ctx, miembro: discord.Member):
    try:
        roles_to_remove = [role for role in miembro.roles if role.id != ctx.guild.id]
        if roles_to_remove:
            database["roles_backup"][str(miembro.id)] = [role.id for role in roles_to_remove]
            save_database()
            for role in roles_to_remove:
                await miembro.remove_roles(role)
            rol_prohibido = ctx.guild.get_role(ROL_PROHIBIDO_ID)
            if rol_prohibido:
                await miembro.add_roles(rol_prohibido)
                await ctx.send(f"✅ Se han eliminado todos los roles de {miembro.mention} y se le asignó el rol predeterminado.")
            else:
                await ctx.send("⚠️ No se encontró el rol predeterminado. Verifica el ID.")
    except Exception as e:
        await ctx.send(f"❌ Error al modificar los roles: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def restaurarroles(ctx, miembro: discord.Member):
    try:
        rol_prohibido = ctx.guild.get_role(ROL_PROHIBIDO_ID)
        if rol_prohibido and rol_prohibido in miembro.roles:
            await miembro.remove_roles(rol_prohibido)
            await ctx.send(f"⚠️ Se ha quitado el rol predeterminado de {miembro.mention}.")
        if str(miembro.id) in database["roles_backup"]:
            roles_to_restore = [ctx.guild.get_role(role_id) for role_id in database["roles_backup"][str(miembro.id)]]
            roles_to_restore = [role for role in roles_to_restore if role is not None]
            if roles_to_restore:
                roles_to_restore = [role for role in roles_to_restore if role != rol_prohibido]
                await miembro.add_roles(*roles_to_restore)
                await ctx.send(f"✅ Se han restaurado los roles de {miembro.mention}.")
            else:
                await ctx.send("⚠️ No se encontraron roles para restaurar.")
            del database["roles_backup"][str(miembro.id)]
            save_database()
        else:
            await ctx.send("❌ No hay roles guardados para este usuario.")
    except Exception as e:
        await ctx.send(f"❌ Error al restaurar los roles: {e}")


@bot.command()
async def togglevc(ctx, action: str):
    if action.lower() not in ['open', 'close']:
        await ctx.send("❌ Acción no válida. Usa 'open' o 'close'.")
        return

    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ No estás en un canal de voz.")
        return

    channel = ctx.author.voice.channel
    owner_id = get_channel_owner_by_id(channel.id)

    if owner_id != ctx.author.id:
        await ctx.send("❌ No eres el dueño de este canal.")
        return

    if action.lower() == 'open':
        overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(connect=True)}
        await channel.edit(overwrites=overwrites)
        await ctx.send(f"✅ El canal de voz {channel.name} está ahora **abierto**.")
    elif action.lower() == 'close':
        overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(connect=False)}
        await channel.edit(overwrites=overwrites)
        await ctx.send(f"✅ El canal de voz {channel.name} está ahora **cerrado** para todos, excepto el dueño.")

@bot.command()
async def renamevc(ctx, *, new_name: str):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ No estás en un canal de voz.")
        return

    channel = ctx.author.voice.channel
    owner_id = get_channel_owner_by_id(channel.id)

    if owner_id != ctx.author.id:
        await ctx.send("❌ No eres el dueño de este canal.")
        return

    await channel.edit(name=new_name)
    await ctx.send(f"✅ El canal de voz ha sido renombrado a: **{new_name}**.")

@bot.command()
async def vcperms(ctx, member: discord.Member):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ No estás en un canal de voz.")
        return

    channel = ctx.author.voice.channel
    owner_id = get_channel_owner_by_id(channel.id)

    if owner_id != ctx.author.id:
        await ctx.send("❌ No eres el dueño de este canal.")
        return

    await channel.set_permissions(member, connect=True)
    await ctx.send(f"✅ Se ha dado acceso a {member.mention} para unirse al canal **{channel.name}**.")


@bot.command()
async def kickvc(ctx, member: discord.Member):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ No estás en un canal de voz.")
        return

    channel = ctx.author.voice.channel
    owner_id = get_channel_owner_by_id(channel.id)

    if owner_id != ctx.author.id:
        await ctx.send("❌ No eres el dueño de este canal.")
        return

    if member in channel.members:
        await member.move_to(None)
        await ctx.send(f"✅ {member.mention} ha sido desconectado de **{channel.name}**.")
    else:
        await ctx.send("❌ Ese miembro no está en el canal.")

@bot.command()
async def banvc(ctx, member: discord.Member):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ No estás en un canal de voz.")
        return

    channel = ctx.author.voice.channel
    owner_id = get_channel_owner_by_id(channel.id)

    if owner_id != ctx.author.id:
        await ctx.send("❌ No eres el dueño de este canal.")
        return

    await channel.set_permissions(member, connect=False)
    await ctx.send(f"✅ {member.mention} ha sido **prohibido** de unirse a **{channel.name}**.")

@bot.command()
async def viewvc(ctx, visibility: str):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ No estás en un canal de voz.")
        return

    channel = ctx.author.voice.channel
    owner_id = get_channel_owner_by_id(channel.id)

    if owner_id != ctx.author.id:
        await ctx.send("❌ No eres el dueño de este canal.")
        return

    if visibility.lower() == "private":
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            ctx.author: discord.PermissionOverwrite(view_channel=True)
        }
        await channel.edit(overwrites=overwrites)
        conn = sqlite3.connect("your_database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE channels SET visibility = ? WHERE channel_id = ?", ("private", channel.id))
        conn.commit()
        conn.close()
        await ctx.send("✅ El canal ha sido configurado como **invisible** para todos excepto el dueño.")
    elif visibility.lower() == "public":
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=True)
        }
        await channel.edit(overwrites=overwrites)
        conn = sqlite3.connect("your_database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE channels SET visibility = ? WHERE channel_id = ?", ("public", channel.id))
        conn.commit()
        conn.close()
        await ctx.send("✅ El canal ha sido configurado como **visible** para todos.")
    else:
        await ctx.send("❌ Visibilidad no válida. Usa `private` o `public`.")


@bot.command()
async def deletevc(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ No estás en un canal de voz.")
        return

    channel = ctx.author.voice.channel
    owner_id = get_channel_owner_by_id(channel.id)

    if owner_id != ctx.author.id:
        await ctx.send("❌ No eres el dueño de este canal.")
        return

    conn = sqlite3.connect("your_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM channels WHERE channel_id = ?", (channel.id,))
    result = cursor.fetchone()

    if result:
        cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel.id,))
        conn.commit()
        await channel.delete()
        await ctx.send(f"✅ El canal de voz **{channel.name}** ha sido eliminado correctamente.")
    else:
        await ctx.send("❌ Este canal no está registrado en la base de datos.")

    conn.close()

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ Error: BOT_TOKEN no encontrado en .env")
