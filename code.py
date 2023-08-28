#!/usr/bin/env python3
import os
import random
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

created_channels = []

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
    if before.channel and before.channel.id in created_channels:
        if not before.channel.members:
            await before.channel.delete()
            created_channels.remove(before.channel.id)

    if after.channel and after.channel.id == int(os.environ['DISCORD_DUPLICATE_VOICE_CHANNEL']):
        permissions = after.channel.overwrites
        new_channel = await after.channel.guild.create_voice_channel(
                name=f"{len(created_channels)+1} 🔊 Random Battle", 
            category=after.channel.category,
            overwrites=permissions,
        )
        created_channels.append(new_channel.id)
        await member.move_to(new_channel)

bot.run(os.environ['DISCORD_BOT_SECRET_KEY'])

