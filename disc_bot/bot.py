from discord import TextChannel
import discord
from typing import Callable
import asyncio
import re

from disc_bot.background_tasks import AlertTask

help_str = ('''
--- Commands ---
$ping - pong!
$Watch:BTC/USDC - Start watching a pair
$Cancel:BTC/USDC - Cancel watching a pair
$List - List all pairs being watched
''')


class DiscordBot(AlertTask,  discord.Client):
    def __init__(self, *args, **kwargs):
        self.text_channel_list: list[TextChannel] = []
        self.stream_data_runner: Callable = None
        self.watch_tasks = {}  # Dictionary to store tasks
        super().__init__(*args, **kwargs)

    async def setup_hook(self) -> None:
        await self.setup_hook_alert()

    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')
        # get all the channels the bot has access to
        await self.get_channels()
        # on_ready_alert just maps the channels to the class variables ( channels )
        await self.on_ready_alert(self.text_channel_list)

    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.content.startswith('$ping'):
            await message.channel.send(f'pong!')
            return
        if message.content.startswith('$Watch:'):
            return await self.start_watch_task(message)
        if message.content.startswith('$Cancel:'):
            return await self.cancel_watch_task(message)
        if message.content.startswith('$List'):
            return await message.channel.send(f'Active Pairs: {", ".join(self.watch_tasks.keys())}')

        return await message.channel.send(help_str)

    async def start_watch_task(self, message):
        content = message.content.replace('$Watch:', '')
        match = re.match(r'([A-Za-z]{2,5})\/([A-Za-z]{2,5})$', content)
        if not match:
            return await message.channel.send('Invalid pair format. Please use the format like $Watch:BTC/USDC.')

        pair = match.group(0)
        await message.channel.send(f'Watching [{pair}]')
        self.watch_tasks[pair] = asyncio.create_task(self.stream_data_runner(pair))
        return

    async def cancel_watch_task(self, message):
        content = message.content.replace('$Cancel:', '')
        match = re.match(r'([A-Za-z]{2,5})\/([A-Za-z]{2,5})$', content)

        if not match:
            return await message.channel.send('Invalid pair format. Please use the format like $Cancel:BTC/USDC.')

        pair = match.group(0)
        task = self.watch_tasks.get(pair)
        if task and not task.done():
            task.cancel()  # Request cancellation of the task
            try:
                await task  # Optionally wait for the task to be cancelled
            except asyncio.CancelledError:
                pass  # Task was cancelled, expected exception
            del self.watch_tasks[pair]  # Remove the task from the dictionary

            return await message.channel.send(f'Cancelled pair [{pair}]')
        return

    async def get_channels(self):
        for server in self.guilds:
            print(f"Bot is part of {server} server")
            for channel in server.text_channels:
                self.text_channel_list.append(channel)

    def attach_stream_data_runner(self, stream_data_runner: Callable) -> None:
        self.stream_data_runner = stream_data_runner


def discord_client():
    intents = discord.Intents.all()
    client = DiscordBot(intents=intents)
    return client
