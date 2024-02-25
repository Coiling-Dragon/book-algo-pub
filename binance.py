import subprocess
import os
import time
import sys
import inspect
import asyncio
import websockets
import json
import httpx
import traceback


from typing import Callable
from disc_bot.bot_queue import SingletonQueue
from pydantic import BaseModel

# This inserts some additional paths to the system
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

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
# import binance_orderbook

# # Import the compiled Cython module
# binance_order_book_parser = binance_orderbook.parser


'''Original orderbook parser, converted to Cython'''
# def qty_at_price_changed(local_order_book_side: dict, price, qty) -> bool:
#     old_qty = local_order_book_side.get(price, None)
#     if old_qty is None:
#         return True

#     return True if float(old_qty) != float(qty) else False


# def refresh_orderbook(local_order_book_side: dict, price, qty, side) -> dict:
#     if float(qty) == 0:
#         # Remove the price level if the quantity is 0
#         local_order_book_side.pop(price, None)
#     else:
#         # Otherwise, update the order book with the new data
#         local_order_book_side[price] = qty


# # This parser function is used as a dependency injection in LocalOrderBookStream class
# def binance_order_book_parser(data, local_order_book: dict, avg_volume: float):
#     '''
#     https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md#how-to-manage-a-local-order-book-correctly

#     Payload from binance looks like this:
#     {
#         "e": "depthUpdate", // Event type
#         "E": 1672515782136, // Event time
#         "s": "BNBBTC",      // Symbol
#         "U": 157,           // First update ID in event
#         "u": 160,           // Final update ID in event
#         "b": [              // Bids to be updated
#             [
#             "0.0024",       // Price level to be updated
#             "10"            // Quantity
#             ]
#         ],
#         "a": [              // Asks to be updated
#             [
#             "0.0026",       // Price level to be updated
#             "100"           // Quantity
#             ]
#         ]
#     }
#     '''
#     # Ensure the data is applicable to our local order book
#     # U = data['U'] # First update ID in event is inaplicable because of lag after initial snapshot
#     finalUpdateId = data['u']
#     lastUpdateId = local_order_book['lastUpdateId']
#     timestamp = data['E']  # is in milliseconds [1/1000]

#     if finalUpdateId <= lastUpdateId:
#         return  # Ignore this data

#     latest_updates = []

#     # Ensure the first event applies to our snapshot
#     if local_order_book['lastUpdateId'] is not None and finalUpdateId >= lastUpdateId + 1:
#         # Apply the update to the order book
#         # The bids and asks in the update data are absolute and can replace the existing data in our local order book

#         for bid in data['b']:
#             price, qty = bid
#             side = 'bids'
#             if qty_at_price_changed(local_order_book[side], price, qty):

#                 if float(qty) > avg_volume:
#                     latest_updates.append(
#                         {'price': price, 'old_qty': local_order_book[side].get(price, 0), 'new_qty': qty, 'side': side})

#                 refresh_orderbook(local_order_book[side], price, qty, side)

#         for ask in data['a']:
#             price, qty = ask
#             side = 'asks'
#             if qty_at_price_changed(local_order_book[side], price, qty):

#                 if float(qty) > avg_volume:
#                     latest_updates.append(
#                         {'price': price, 'old_qty': local_order_book[side].get(price, 0), 'new_qty': qty, 'side': side})

#                 refresh_orderbook(local_order_book[side], price, qty, side)

#         # Update the lastUpdateId to the new update id
#         local_order_book['lastUpdateId'] = finalUpdateId

#     return {'timestamp': timestamp, 'updates': latest_updates}


async def get_initial_order_book(PAIR: str):
    local_order_book = {
        "lastUpdateId": None,
        "bids": {},
        "asks": {}
    }

    PAIR = PAIR.replace('/', '').upper()
    url = f"https://api.binance.com/api/v3/depth?symbol={PAIR}&limit=1000"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()

            local_order_book["lastUpdateId"] = data['lastUpdateId']
            local_order_book["bids"] = {level[0]: level[1] for level in data['bids']}
            local_order_book["asks"] = {level[0]: level[1] for level in data['asks']}
            return local_order_book
        else:
            print(f"Failed to retrieve data: {response.status_code}")
            return None


async def fetch_7day_avg_volume(symbol: str):
    '''
    [
        [
        0   1499040000000,      // Kline open time
        1   "0.01634790",       // Open price
        2   "0.80000000",       // High price
        3   "0.01575800",       // Low price
        4   "0.01577100",       // Close price
        5   "148976.11427815",  // Volume
            1499644799999,      // Kline Close time
            "2434.19055334",    // Quote asset volume
            308,                // Number of trades
            "1756.87402397",    // Taker buy base asset volume
            "28.46694368",      // Taker buy quote asset volume
            "0"                 // Unused field, ignore.
        ]
    ]
    '''
    symbol = symbol.replace('/', '').upper()
    url = f'https://api.binance.com/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': '1d',
        'limit': 7
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code == 200:
            klines = response.json()

            total_volume = sum(float(kline[5]) for kline in klines)
            avg_volume = total_volume / 7
            return avg_volume
        else:
            print(f"Failed to retrieve data: {response.status_code}")
            return None


def WS_BINANCE_ORDER_BOOK_SOURCE(PAIR: str):
    PAIR = PAIR.replace("/", "").lower()
    SOCKET = f"wss://stream.binance.com:9443/ws/{PAIR}@depth"
    return SOCKET


class LocalOrderBookStream:
    def __init__(self, SOCKET, local_order_book: dict, avg_volume: float, data_parser: Callable) -> None:
        self.SOCKET = SOCKET
        self.data_parser = data_parser
        self.local_order_book = local_order_book
        self.avg_volume = avg_volume

    async def connect_websocket(self):
        try:
            async with websockets.connect(self.SOCKET) as websocket:
                print('WS opened connection on:', self.SOCKET)
                await self.receive_messages(websocket)

        except Exception as e:
            if isinstance(e, asyncio.CancelledError):
                return "WebSocket connection cancelled. Cleaning up..."
            return e
        return None

    async def receive_messages(self, websocket):
        try:
            async for message in websocket:
                tick_data = json.loads(message)
                data = self.data_parser(tick_data, self.local_order_book, self.avg_volume)
                # print(websocket, data) TODO use logging here
                if len(data["updates"]) != 0:
                    await SingletonQueue().enqueue_book_data(f"{data}")

        except Exception as e:
            if isinstance(e, asyncio.CancelledError):
                return None

            print(f"### -------WS ERROR-------- ###\n{e}")
            print(traceback.format_exc())  # Print the stack trace
            await asyncio.sleep(2)
            await self.connect_websocket()

        return None
