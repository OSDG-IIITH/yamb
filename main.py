import discord
from discord.ext import commands
from discord.ext.commands.bot import when_mentioned_or

import os
import logging

# Import cogs
from yamb.cogs.music import Music

description = '''
Yet another music bot.
Powered by OSDG@IIITH.
Contribute at https://github.com/OSDG-IIITH/yamb.
'''

def main():
    # Logging
    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    # Bot Setup
    bot = commands.Bot(command_prefix=when_mentioned_or('?'), description=description)

    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user.name}#{bot.user.discriminator}')

    token = os.environ.get('BOT_TOKEN')
    bot.add_cog(Music(bot))
    bot.run(token)

if __name__ == '__main__':
    main()
