from discord import TextChannel

from discord.ext import tasks
import discord

from disc_bot.bot_queue import SingletonQueue


class CHANNELS:
# @DEV  IF channel names are not set corectly it throws silen errors that brake the app
    GENERAL = 'general'


class AlertTask(discord.Client):
    public_signals_channel: TextChannel
    # private_signals_one_channel: TextChannel
    # private_signals_two_channel: TextChannel

    async def setup_hook_alert(self) -> None:
        # start the task to run in the background
        self.alert_task.start()

    @tasks.loop()
    async def alert_task(self):
        message = await SingletonQueue().dequeue_alert()
        await self.public_signals_channel.send(f"{message}")

    @alert_task.before_loop
    async def before_alert_task(self):
        print('\n AlertTask Ready\n\n')
        await self.wait_until_ready()  # wait until the bot logs in

    # this function is used to map the channels to the class variables
    async def on_ready_alert(self, text_channel_list:list[TextChannel]):
        try:
            self.public_signals_channel = next(
                filter(lambda x: x.name == CHANNELS.GENERAL, text_channel_list))

        except:
            ## TODO The program is throwing silent errors if channel name is not found!
            print('CRITICAL ERROR in AlertTask.on_ready_alert()')
