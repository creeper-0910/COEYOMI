import os
import re

import discord
from discord.ext import commands

import api
import config as cfg

# PATHに追加
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

def matchindex(mention_list,id):
    for i in range(len(mention_list)):
        if  str(id) in str(mention_list[i]):
            return i
    return None


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command(name='join')
async def join(ctx):
    if ctx.author.voice and ctx.author.voice.channel:
        channel = ctx.author.voice.channel
        if ctx.guild.voice_client is None:
            vc = await channel.connect()
            await ctx.send(f'Joined {channel.name}')
            cfg.in_voice[ctx.guild.id] = vc
            cfg.call_channel[ctx.guild.id] = ctx.channel
        else:
            await ctx.send('Already in a voice channel')

@bot.command(name='leave')
async def leave(ctx):
    if ctx.guild.id in cfg.in_voice:
        vc = cfg.in_voice[ctx.guild.id]
        await vc.disconnect()
        await ctx.send('Left the voice channel')
        del cfg.in_voice[ctx.guild.id]
        del cfg.call_channel[ctx.guild.id]

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.guild and message.guild.id in cfg.in_voice and message.content and not message.content.startswith('!'):
        if cfg.call_channel[message.guild.id] != message.channel:
            return
        vc = cfg.in_voice[message.guild.id]
        clean_message = re.sub(r'[\n\s\\/:*?"<>|]+','',message.content)[:25]
        mention_user = re.findall(r'<@\S{1,}>', message.content)
        mention_user = sorted(set(mention_user), key=mention_user.index)
        speaker_text = message.content
        if len(message.mentions) != 0:
            for mention in message.mentions:
                index = matchindex(mention_user,mention.id)
                if(index != None):
                    if(mention.nick != None):
                        speaker_text = speaker_text.replace(mention_user[index], mention.nick+"さん")
                    elif(mention.global_name != None):
                        speaker_text = speaker_text.replace(mention_user[index], mention.global_name+"さん")
                    else:
                        speaker_text = speaker_text.replace(mention_user[index], mention.name+"さん")
        if len(message.attachments) != 0:
            attach_count = {}
            for i in range(len(message.attachments)):
                print(message.attachments[i].url)
                print(message.attachments[0].content_type)
                if "image" in message.attachments[i].content_type:
                    attach_count["image"] = attach_count.get("image",0) + 1
                elif "video" in message.attachments[i].content_type:
                    attach_count["video"] = attach_count.get("video",0) + 1
                elif "audio" in message.attachments[i].content_type:
                    attach_count["audio"] = attach_count.get("audio",0) + 1
                else:
                    attach_count["other"] = attach_count.get("other",0) + 1

            if(attach_count.get("image",None) != None):
                speaker_text = str(attach_count["image"])+"件の画像ファイル "+speaker_text
            if(attach_count.get("video",None) != None):
                speaker_text = str(attach_count["video"])+"件の動画ファイル "+speaker_text
            if(attach_count.get("audio",None) != None):
                speaker_text = str(attach_count["audio"])+"件の音声ファイル "+speaker_text
            if(attach_count.get("other",None) != None):
                speaker_text = str(attach_count["other"])+"件のファイル "+speaker_text





        linkcount = len(re.findall(cfg.url_regex, speaker_text))
        if(linkcount != 0):
            speaker_text = re.sub(cfg.url_regex,'',speaker_text)
            speaker_text = str(linkcount)+"件のリンク "+speaker_text


        voice = api.genvoice(speaker_text)
        temp_file = rf'temp_{clean_message}.wav'

        # 生成した音声を一時ファイルに保存
        with open(temp_file, 'wb') as f:
            f.write(voice)

        vc.play(discord.FFmpegPCMAudio(temp_file, executable=cfg.ffmpeg_path), after=lambda e: os.remove(temp_file))

    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.guild.id in cfg.in_voice and not member == bot.user:
        if len(member.guild.voice_client.channel.members) == 1:
            vc = cfg.in_voice[member.guild.id]
            await vc.disconnect()
            del cfg.in_voice[member.guild.id]
            del cfg.call_channel[member.guild.id]

bot.run(cfg.token)