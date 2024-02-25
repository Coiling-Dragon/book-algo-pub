import os, sys, subprocess
import asyncio
from datetime import datetime, timezone

from disc_bot.bot_queue import SingletonQueue
from disc_bot.bot import discord_client
from dotenv import load_dotenv


from binance import (
    WS_BINANCE_ORDER_BOOK_SOURCE,
    LocalOrderBookStream, get_initial_order_book, fetch_7day_avg_volume)

# Specify the directory for the compiled .so files
build_dir = os.path.join(os.getcwd(), "cython_mods")

# Create the build directory if it does not exist
os.makedirs(build_dir, exist_ok=True)

# Compile the Cython code
subprocess.run([
    sys.executable,
    'setup.py',
    'build_ext',
    '--inplace',
    '--build-lib', build_dir
])

# Add the build directory to sys.path to make the compiled .so file importable
sys.path.append(build_dir)


# Import the compiled Cython module
import binance_orderbook

# Import the compiled Cython module
binance_order_book_parser = binance_orderbook.parser


load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')


async def algo_worker() -> None:
    '''Has to complete calculations faster than data stream'''
    try:
        while True:
            message = await SingletonQueue().dequeue_book_data()

            # Implement Order BOOK logic here

            print(f'''
            datetime.now: {(datetime.now(timezone.utc))}
            message: {message}
            ''')

            await SingletonQueue().enqueue_alert(message)
    except Exception as e:
        msg = f'ERROR:::THREAD:::algo_worker -> {e}'
        print(msg)


async def stream_data_runner(socket_pair):
    SOCKET = WS_BINANCE_ORDER_BOOK_SOURCE(socket_pair)
    order_book = await get_initial_order_book(socket_pair)
    if not order_book:
        await SingletonQueue().enqueue_error(f'ERROR:::THREAD:::stream_data_runner -> {socket_pair}')
        return
    
    avg_volume = await fetch_7day_avg_volume(socket_pair)

    await SingletonQueue().enqueue_alert(f'Starting bot for {socket_pair}, avg_volume: {avg_volume}')

    ws_app = LocalOrderBookStream(SOCKET, order_book, avg_volume, binance_order_book_parser)
    await ws_app.connect_websocket()


async def main():
    client = discord_client()
    client.attach_stream_data_runner(stream_data_runner)
    
    assert DISCORD_TOKEN, 'DISCORD_TOKEN not found in .env file'

    await asyncio.gather(
        algo_worker(),  # the algo task
        client.start(DISCORD_TOKEN, reconnect=True),  # the alert task
    )

if __name__ == '__main__':
    asyncio.run(main())
