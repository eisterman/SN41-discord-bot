#!/usr/bin/env python3
import os
import random
import logging
from itertools import pairwise
from collections import OrderedDict
from datetime import datetime, timedelta
import pytz
from hashlib import md5
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SN41-Bot')

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.message_content = True

ADMIN_ROLES = ['ADEPTUS MECHANICUS', 'AMMIRAGLIO', 'RECLUTATORE [SN41]', 'COMMODORO', 'BOT']

join_message = \
    ("Benvenuto in **SN41 COMMUNITY** {}!\n"
     "Modifica il tuo soprannome nel nostro discord in modo che coincida con il tuo nickname in gioco e "
     "se vuoi metti il tuo nome tra parentesi.\n"
     "Se sei interessato ad entrare nel clan, non esitare a contattare uno degli admin.\n"
     "Buona permanenza !")

join_image_path = './discord_msg_img.png'

goodbye_phrases_file = './goodbye_phrases.txt'
with open(goodbye_phrases_file) as f:
    goodbye_phrases = [ph.strip() for ph in f.readlines() if len(ph.strip()) > 0]

msgentrydb = {}  # user_id: MsgEntry


class MsgEntry:
    def __init__(self, msg, timestamp):
        self.hashmsg = md5(msg.content.encode()).hexdigest()
        self.timestamp = timestamp
        self.n = 1
        self.msgs = [msg]


bot = commands.Bot(command_prefix="!", intents=intents)

max_channels = 50

created_channels = []  # (i, chidx)

delete_msg = """Rilevati messaggi ripetuti.
Messaggi precedenti cancellati. 
Ulteriori invii dello stesso messaggio di seguito risulteranno in un timeout di 5 minuti.

In caso di domande o falsi positivi, contattare @eisterman"""


def get_rolesets(guild: discord.Guild):
    names = [role.name for role in guild.roles]
    lnicom_i = names.index("SN41 COMMUNITY")
    commod_i = names.index("COMMODORO")
    clans_name = ['[SN41]'] + list(reversed(names[lnicom_i+1:commod_i]))  # From older to newer
    out = OrderedDict()
    for clan_name in clans_name:
        out[clan_name] = [clan_name, "SN41 COMMUNITY"]
    out["OSPITI"] = ["OSPITI"]
    return out


class RolesetButton(Button):
    def __init__(self, clanname, rolenames: list[str], member: discord.Member,
                 original_interaction: discord.Interaction | None = None):
        self._member = member
        self._rolenames = rolenames
        self._ointeraction = original_interaction
        super().__init__(label=clanname)

    async def callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            channel = bot.get_channel(int(os.environ['DISCORD_ADMIN_LOG_CHANNEL']))
            await interaction.message.delete()
            msg = (
                f"**ATTENZIONE!** UTENTE {interaction.user.mention} HA TENTATO DI CAMBIARE I RUOLI " 
                f"(set to {self.label}) ALL'UTENTE {self._member.mention} IN MANIERA ILLEGALE!"
            )
            try:
                await interaction.user.send(
                    "**ATTENZIONE!** E' stato rilevato un tentativo illegale di cambio utente.\n"
                    "Tale azione e' stata reportata agli amministratori."
                )
            except Exception:
                print(f"Error sending msg to {interaction.user.name}")
            await channel.send(msg)
            return
        if self._ointeraction is None:
            await interaction.message.delete()
        else:
            await self._ointeraction.delete_original_response()
        guild = interaction.guild
        channel = bot.get_channel(int(os.environ['DISCORD_ASSIGNROLE_TEXT_CHANNEL']))
        roles_to_assign = [discord.utils.get(guild.roles, name=rolename) for rolename in self._rolenames]
        await self._member.edit(roles=roles_to_assign)
        msg = f"L'utente {self._member.mention} è stato assegnato da {interaction.user.mention} al gruppo {self.label}!"
        await channel.send(msg)


def is_admin(user: discord.Member) -> bool:
    return any([role.name in ADMIN_ROLES for role in user.roles])


def ac_check_if_admin(interaction: discord.Interaction) -> bool:
    return is_admin(interaction.user)


async def send_changerole_msg_with(
        awaitable_func,
        user: discord.Member,
        original_interaction: discord.Interaction | None = None,
        **kwargs
):
    view = View(timeout=None)
    rolesets = get_rolesets(user.guild)
    for clanname, rolenames in rolesets.items():
        view.add_item(RolesetButton(clanname, rolenames, user, original_interaction))
    msg = (
        f"E' entrato il nuovo utente {user.mention} ! Che ruolo dobbiamo assegnargli?"
    )
    await awaitable_func(msg, view=view, **kwargs)


@bot.tree.command(description="Apre un messaggio di selezione ruolo per l'utente scelto")
@app_commands.describe(user="L'utente di cui modificare il ruolo")
@app_commands.check(ac_check_if_admin)
@app_commands.default_permissions(move_members=True)
@app_commands.guild_only()
async def cambiaruolo(interaction: discord.Interaction, user: discord.Member):
    channel = bot.get_channel(int(os.environ['DISCORD_ASSIGNROLE_TEXT_CHANNEL']))
    if interaction.channel != channel:
        # noinspection PyUnresolvedReferences
        await interaction.response.send_message(f"Non puoi usare /cambiaruolo fuori da {channel.name}!", ephemeral=True)
        return
    if is_admin(user):
        channel = bot.get_channel(int(os.environ['DISCORD_ADMIN_LOG_CHANNEL']))
        try:
            await interaction.user.send(
                "**ATTENZIONE!** E' stato rilevato un tentativo illegale di cambio utente.\n"
                "Tale azione e' stata reportata agli amministratori.\n\n"
                "Distinti saluti,\n~SN41 Bot~"
            )
        except Exception:
            print(f"Error sending msg to {interaction.user.name}")
        msg = (
            f"**ATTENZIONE!** UTENTE {interaction.user.mention} HA TENTATO DI CAMBIARE I RUOLI "
            f"ALL'UTENTE {user.mention} NONOSTANTE SIA IN UN GRUPPO AMMINISTRATORE!"
        )
        await channel.send(msg)
        return
    # noinspection PyUnresolvedReferences
    await send_changerole_msg_with(interaction.response.send_message, user, interaction, ephemeral=True)


@bot.event
async def on_member_join(member: discord.Member):
    # Invio messaggio di benvenuto
    file = discord.File(join_image_path, filename="image.png")
    embed = discord.Embed(description=join_message.format(member.display_name), colour=discord.Colour.gold())
    embed.set_image(url="attachment://image.png")
    try:
        await member.send(file=file, embed=embed)
    except Exception:
        print(f"Error sending msg to {member.name}")
    # Apparizione messaggio di selezione ruolo
    channel = bot.get_channel(int(os.environ['DISCORD_ASSIGNROLE_TEXT_CHANNEL']))
    await send_changerole_msg_with(channel.send, member)


@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(int(os.environ['DISCORD_GENERAL_TEXT_CHANNEL']))
    phrase = random.sample(goodbye_phrases, 1)[0]
    await channel.send(phrase.format(member.display_name))


@bot.event
async def on_voice_state_update(member, before, after):
    # This check is required because a on_voice_state_update fire even in case of mute/unmute.
    # Some clients enter the channel the first time muted and then unmute immediately after.
    # If this happens fast enough to be done still inside the Dupl Voice Channel, cause a double event fire.
    if before.channel and after.channel and before.channel.id == after.channel.id:
        return

    import secrets
    event_id = f"{member.id}-{secrets.token_hex(4)}"

    # Channel cleanup logic
    if before.channel and before.channel.id in map(lambda x: x[1], created_channels):
        if not before.channel.members:
            index = next((i for i, (x, chid) in enumerate(created_channels) if chid == before.channel.id), None)
            logger.info(f"[{event_id}] Voice state update - Channel id {index} removed")
            await before.channel.delete()
            if index is not None:
                created_channels.pop(index)

    # Channel creation logic
    if after.channel and after.channel.id == int(os.environ['DISCORD_DUPLICATE_VOICE_CHANNEL']):
        if len(created_channels) >= max_channels:
            logger.info(f"[{event_id}] Voice state update - Reached max channel number with Member {member.display_name} try")
            await member.move_to(None)
            try:
                await member.send(f"Vile marrano! Limite stanze a {max_channels}! 🗿🗿🗿")
            except Exception:
                pass
            return

        already_numbers = sorted([0] + [x for x, _ in created_channels])
        for s, e in pairwise(already_numbers):
            if e - s > 1:
                new_number = s + 1
                break
        else:
            new_number = len(already_numbers)

        logger.info(f"[{event_id}] Voice state update - Member {member.display_name} (ID: {member.id}) created Channel {new_number}")
        new_channel = await after.channel.guild.create_voice_channel(
            name=f"{new_number} {after.channel.name}",
            category=after.channel.category,
            overwrites=after.channel.overwrites,
            position=after.channel.position + new_number,
        )

        created_channels.append((new_number, new_channel.id))
        await member.move_to(new_channel)


@bot.listen('on_message')
async def on_message_antispam(message):

    if message.author.id == bot.user.id:
        return
    if len(message.content) < 10:
        try:
            msgentrydb.pop(message.author.id)
        except KeyError:
            pass
        return
    now = datetime.now(pytz.UTC)
    hashmsg = md5(message.content.encode()).hexdigest()
    entry = msgentrydb.get(message.author.id)
    if entry is not None:
        if now - entry.timestamp > timedelta(minutes=1):
            # Too much time passed, reset status
            msgentrydb[message.author.id] = MsgEntry(message, now)
        elif hashmsg == entry.hashmsg:
            # Same message!
            entry.n += 1
            if entry.n >= 2:
                # Block messages
                for msg in entry.msgs:
                    await msg.delete()
                await message.delete()
                try:
                    await message.author.send(delete_msg)
                except Exception:
                    print(f"Error sending msg to {message.author.name}")
                entry.msgs = []
                # Admin Message
                if entry.n > 2:
                    await message.author.timeout(timedelta(minutes=5),
                                                 reason="Spamming")
                    channel = bot.get_channel(int(os.environ['DISCORD_ADMIN_LOG_CHANNEL']))
                    await channel.send(f"User {message.author.name} timeouted for repeated msg:\n{message.content}")
        else:
            # Not the same message, reset status
            msgentrydb[message.author.id] = MsgEntry(message, now)
    else:
        msgentrydb[message.author.id] = MsgEntry(message, now)

@bot.command()
@commands.guild_only()
@commands.has_role('MECCANICI')
async def sync_commands_here(ctx: discord.ext.commands.Context):
    guild = ctx.guild
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    await ctx.send("Commands sync with this server")


bot.run(os.environ['DISCORD_BOT_SECRET_KEY'])

