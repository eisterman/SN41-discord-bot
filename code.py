#!/usr/bin/env python3
import os
import random
from itertools import pairwise
from datetime import datetime, timedelta
import pytz
from hashlib import md5
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.message_content = True

join_message = \
    ("Benvenuto in **LNI COMMUNITY** {}!\n"
     "Modifica il tuo soprannome nel nostro discord in modo che coincida con il tuo nickname in gioco e "
     "se vuoi metti il tuo nome tra parentesi.\n"
     "Se sei interessato ad entrare nel clan, non esitare a contattare uno degli admin.\n"
     "Buona permanenza !")

join_image_path = './discord_msg_img.jpg'

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


@bot.event
async def on_member_join(member):
    file = discord.File(join_image_path, filename="image.png")
    embed = discord.Embed(description=join_message.format(member.display_name), colour=discord.Colour.gold())
    embed.set_image(url="attachment://image.png")
    await member.send(file=file, embed=embed)


@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(int(os.environ['DISCORD_GENERAL_TEXT_CHANNEL']))
    phrase = random.sample(goodbye_phrases, 1)[0]
    await channel.send(phrase.format(member.display_name))


@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel and before.channel.id in map(lambda x: x[1], created_channels):
        if not before.channel.members:
            await before.channel.delete()
            index = next((i for i, (x, chid) in enumerate(created_channels) if chid == before.channel.id), None)
            created_channels.pop(index)

    if after.channel and after.channel.id == int(os.environ['DISCORD_DUPLICATE_VOICE_CHANNEL']):
        permissions = after.channel.overwrites
        if len(created_channels) >= max_channels:
            await member.move_to(None)
            await member.send(f"Vile marrano! Limite stanze a {max_channels}! 🗿🗿🗿")
            return
        already_numbers = sorted([0] + [x for x, _ in created_channels])
        for s, e in pairwise(already_numbers):
            if e - s > 1:
                new_number = s + 1
                break
        else:
            new_number = len(already_numbers)
        new_channel = await after.channel.guild.create_voice_channel(
            name=f"{new_number} {after.channel.name}",
            category=after.channel.category,
            overwrites=permissions,
            position=after.channel.position + new_number,
        )
        created_channels.append((new_number, new_channel.id))
        await member.move_to(new_channel)


@bot.event
async def on_message(message):
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
                await message.author.send(delete_msg)
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


bot.run(os.environ['DISCORD_BOT_SECRET_KEY'])
