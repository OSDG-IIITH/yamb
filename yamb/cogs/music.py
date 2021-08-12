import asyncio
import os
import requests

import discord
import youtube_dl

from discord.ext import commands
from youtube_title_parse import get_artist_title

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')
        self.channel = data.get('channel')
        self.thumb = data.get('thumbnail_url')

        self.artist_title = get_artist_title(self.title)

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def metadata(self, title):
        """Get metadata from last.fm"""
        api_key = os.environ.get('LASTFM_API_KEY')

        url = ["http://ws.audioscrobbler.com/2.0/?method=track.search"]
        url.append("track=" + title)
        url.append("api_key=" + api_key)
        url.append("format=json")

        response = requests.get('&'.join(url))

        if response:
            meta = response.json()
            try:
                title = meta['results']['trackmatches']['track'][0]['name']
                artist = meta['results']['trackmatches']['track'][0]['artist']
            except KeyError:
                title, artist = None, None

        # get album art
        url = ["http://ws.audioscrobbler.com/2.0/?method=track.getInfo"]
        url.append("track=" + title)
        url.append("artist=" + artist)
        url.append("api_key=" + api_key)
        url.append("format=json")

        response = requests.get('&'.join(url))
        if response:
            meta = response.json()
            try:
                album_art = meta['track']['album']['image'][2]['#text']
            except KeyError:
                album_art = None

        return title, artist, album_art

    @commands.command()
    async def play(self, ctx, *args):
        """Plays music from query"""

        url = ' '.join(args)
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await self.np(ctx)

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume))

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        await ctx.voice_client.disconnect()

    @commands.command()
    async def np(self, ctx):
        """Display the currently playing track"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        meta = self.metadata(ctx.voice_client.source.artist_title[1] or ctx.voice_client.source.title)
        title = meta[0] or ctx.voice_client.source.artist_title[1] or ctx.voice_client.source.title
        artist = meta[1] or ctx.voice_client.source.artist_title[0] or ctx.voice_client.source.channel
        album_art = meta[2] or ctx.voice_client.source.thumb

        embed = discord.Embed(title="Now playing")
        embed.set_image(url=album_art)
        embed.add_field(name="Title", value=title)
        embed.add_field(name="Artist", value=artist)

        await ctx.send(embed=embed)

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()



