#!/usr/bin/env python3
import os
import random
from itertools import pairwise
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

join_message = \
"""Benvenuto in **LNI COMMUNITY** {}!
Modifica il tuo soprannome nel nostro discord in modo che coincida con il tuo nickname in gioco e se vuoi metti il tuo nome tra parentesi.
Se sei interessato ad entrare nel clan, non esitare a contattare uno degli admin.
Buona permanenza !"""

join_image_path = './discord_msg_img.jpg'

goodbye_phrases_file = './goodbye_phrases.txt'
with open(goodbye_phrases_file) as f:
    goodbye_phrases = [ ph.strip() for ph in f.readlines() if len(ph.strip()) > 0 ]

bot = commands.Bot(command_prefix="!", intents=intents)

max_channels = 50

created_channels = []  # (i, chidx)

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
        for s,e in pairwise(already_numbers):
            if e-s > 1:
                new_number = s+1
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

bot.run(os.environ['DISCORD_BOT_SECRET_KEY'])

