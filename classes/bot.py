from telethon import TelegramClient, events
from binance import Client as BinanceClient
from binance import ThreadedWebsocketManager
from models.models import BotInitializer
from decimal import Decimal, ROUND_DOWN

import requests
import asyncio

import aiohttp

import nest_asyncio
nest_asyncio.apply()

from helpfullFunctions.functions import getBotTag

class Bot:
    def __init__(self, bot_info: BotInitializer):
        self.phone_number=bot_info.phone_number
        self.telegram_api_id=bot_info.telegram_api_id
        self.telegram_api_hash=bot_info.telegram_api_hash
        self.binance_api_key=bot_info.binance_api_key
        self.binance_api_secret=bot_info.binance_api_secret
        self.chat_id=bot_info.chat_id
        self.client = TelegramClient('session', self.telegram_api_id, self.telegram_api_hash)
        self.listen_key = None
        self.active_orders = {}
        self.trade_done_event = asyncio.Event()

    async def start(self):
        if(self.client.is_connected()):
            print("you are already connected")
            return

        await self.client.start(self.phone_number)

    async def stop(self):
        await self.client.disconnect()

    async def printChats(self):
        if not self.client.is_connected():
            await self.client.start()

        async for dialog in self.client.iter_dialogs():
            print(f'id: {dialog.id}, title: {dialog.title}')

    async def printCurrentChatId(self):
        if(self.chat_id):
            print("Chat_id: ", self.chat_id)
            return
        print("There is no chat_id stored!")
        
    async def modifyChat(self):
        try:
            chat_id = int(input("Enter the chat id: ").strip())
            self.chat_id = chat_id
            print(f"Chat ID set to: {self.chat_id}")
        except ValueError:
            print("Invalid chat ID. Must be a number.")

    async def btcHandler(self):
        if not self.chat_id:
            print('You have no chat id present;')
            return

        async def fetch_exchange_info_periodically():
            while True:
                try:
                    print("Fetching latest exchangeInfo from Binance...")
                    async with aiohttp.ClientSession() as session:
                        async with session.get('https://fapi.binance.com/fapi/v1/exchangeInfo') as response:
                            if response.status == 200:
                                self.exchange_info = await response.json()
                                print("exchangeInfo updated.")
                            else:
                                print(f"Failed to fetch exchangeInfo: HTTP {response.status}")
                except Exception as e:
                    print(f"Error fetching exchangeInfo: {e}")
                await asyncio.sleep(3600)  # 1 hour = 3600 seconds

        # Start periodic fetcher
        asyncio.create_task(fetch_exchange_info_periodically())

        while True:  # main loop
            if not self.client.is_connected():
                await self.client.start()

            entity = await self.client.get_entity(self.chat_id)

            @self.client.on(events.NewMessage(chats=entity))
            async def handler(event):
                message = event.raw_text
                crypt_slugs = getBotTag(message)
                if crypt_slugs:
                    for tag in crypt_slugs:
                        await self.trade_on_binance(tag)

            task = asyncio.create_task(self.client.run_until_disconnected())

            print("Waiting for trade to complete...")
            await self.trade_done_event.wait()
            self.trade_done_event.clear()

            print("Trade completed, restarting listener...")

            await self.client.disconnect()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    # BINANCE STUFF ------------------------------------------------------------------------------------------
    
    def round_step(self, value, step):
        return float(Decimal(str(value)).quantize(Decimal(str(step)), rounding=ROUND_DOWN))

    async def trade_on_binance(self, coin):
        my_symbol = f"{coin.upper()}USDT"
        print('my symbol: ', my_symbol)
        invest_percent = 60
        leverage = 20

        client = BinanceClient(self.binance_api_key, self.binance_api_secret)
        try:
            client.futures_change_leverage(symbol=my_symbol, leverage=leverage)
            symbol_price = client.get_symbol_ticker(symbol=my_symbol)['price']
        except Exception as e:
            print(e)
            return

        if self.exchange_info == None:
            url = 'https://fapi.binance.com/fapi/v1/exchangeInfo'
            response = requests.get(url)
            if response.status_code == 200:
                self.exchange_info = response.json()
            else:
                print(f"Request failed with status code {response.status_code}")
                return

        quantityPrecision = 0
        tick_precision = 0
        for symbol in self.exchange_info['symbols']:
            if symbol['symbol'] == my_symbol:
                quantityPrecision = symbol['quantityPrecision']
                tick_precision = symbol['filters'][0]['tickSize']

        print('quantity precision: ', quantityPrecision)

        assets = client.futures_account_balance()
        balance = 0
        for asset in assets:
            if asset['asset'] == 'USDT':
                balance = asset['balance']

        if balance == 0:
            print('the balance is 0')
            return

        the_ammount_to_invest = (invest_percent * float(balance)) / 100
        quantity = the_ammount_to_invest / float(symbol_price)
        print('quantity before round: ', quantity)
        rounded_quantity = round(quantity, quantityPrecision)

        print('ammount to invest: ', the_ammount_to_invest)
        print('initial quantity: ', quantity)
        print('rounded quantity: ', rounded_quantity)

        tp_pct = 100
        sl_pct = 70

        position_size = the_ammount_to_invest * leverage
        delta_tp = (the_ammount_to_invest * tp_pct / 100) / (position_size / float(symbol_price))
        delta_sl = (the_ammount_to_invest * sl_pct / 100) / (position_size / float(symbol_price))

        tp_price = float(symbol_price) + delta_tp
        sl_price = float(symbol_price) - delta_sl

        tp_price = self.round_step(tp_price, tick_precision)
        sl_price = self.round_step(sl_price, tick_precision)

        print('current price: ', float(symbol_price))
        print("stop loss price: ", sl_price)
        print('take profit price: ', tp_price)

        try:
            order = client.futures_create_order(symbol=my_symbol, side='BUY', type='MARKET', quantity=str(rounded_quantity))
            take_profit = client.futures_create_order(
                symbol=my_symbol, side="SELL", type="TAKE_PROFIT_MARKET",
                quantity=str(rounded_quantity), stopPrice=str(tp_price)
            )
            stop_loss = client.futures_create_order(
                symbol=my_symbol, side="SELL", type="STOP_MARKET",
                quantity=str(rounded_quantity), stopPrice=str(sl_price)
            )

            active_order_ids = {
                "tp": take_profit['orderId'],
                "sl": stop_loss['orderId']
            }
            print(active_order_ids)

            twm = ThreadedWebsocketManager(api_key=self.binance_api_key, api_secret=self.binance_api_secret)
            twm.start()

            def handle_socket_msg(msg):
                print(msg)
                if msg['e'] == 'ORDER_TRADE_UPDATE':
                    order = msg['o']
                    order_id = order['i']
                    status = order['X']  # 'FILLED', 'CANCELED', etc.
                    if order_id in active_order_ids.values() and status == 'FILLED':
                        print(f"Order filled: {order_id}")
                        # Cancel the other order
                        for label, oid in active_order_ids.items():
                            if oid != order_id:
                                try:
                                    client.futures_cancel_order(
                                        symbol=my_symbol,
                                        orderId=oid
                                    )
                                    print(f"Canceled {label.upper()} order {oid}")
                                except Exception as e:
                                    print(f"Could not cancel {label.upper()} order: {e}")
                        # Stop websocket
                        twm.stop()

                        # Signal that trade is done (must schedule coroutine thread safe)
                        asyncio.get_event_loop().call_soon_threadsafe(self.trade_done_event.set)

            twm.start_futures_user_socket(callback=handle_socket_msg)

            # Wait until trade_done_event is set from websocket callback
            await self.trade_done_event.wait()
            self.trade_done_event.clear()

        except Exception as e:
            print(e)
            return

