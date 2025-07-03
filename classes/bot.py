import pandas as pd

from telethon import TelegramClient, events
from binance import Client as BinanceClient
from binance import ThreadedWebsocketManager
from models.models import BotInitializer
from decimal import Decimal, ROUND_DOWN

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
        
        if not self.client.is_connected():
            await self.client.start()
        
        try:
            entity = await self.client.get_entity(self.chat_id)
        except ValueError as e:
            print(f"Could not find chat '{self.chat_id}': {e}")
            return
        
        @self.client.on(events.NewMessage(chats=entity))
        async def handler(event):
            message = event.raw_text
            crypt_slugs = getBotTag(message)

            if(crypt_slugs):
                for tag in crypt_slugs:
                    await self.trade_on_binance(tag)

        await self.client.run_until_disconnected()

    # BINANCE STUFF ------------------------------------------------------------------------------------------
    def round_step(self, value, step):
        return float(Decimal(str(value)).quantize(Decimal(str(step)), rounding=ROUND_DOWN))

    async def trade_on_binance(self, coin: str = "BTC"):
        symbol = f"{coin.upper()}USDT"
        client = BinanceClient(self.binance_api_key, self.binance_api_secret, testnet=True)

        balance = client.futures_account_balance()
        usdt_balance = next((item['balance'] for item in balance if item['asset'] == 'USDT'), None)

        current_symbol_price = client.get_symbol_ticker(symbol=symbol)['price']
        current_symbol_precision = client.get_symbol_info(symbol=symbol)['baseAssetPrecision']
    
        ammount_to_invest = float(usdt_balance) * 0.1

        leverage = 10
        take_profit_pct = 100  # +100% move
        stop_loss_pct = 50     # -50% move

        # Current price
        entry_price = current_symbol_price

        tp = float(entry_price) * (1 + take_profit_pct / 100)
        sl = float(entry_price) * (1 - stop_loss_pct / 100)

        client.futures_change_leverage(symbol=symbol, leverage=leverage)

        symbol_info = client.get_symbol_info(symbol=symbol)
        filters = {f['filterType']: f for f in symbol_info['filters']}
        step_size = float(filters['LOT_SIZE']['stepSize'])        # for quantity
        tick_size = float(filters['PRICE_FILTER']['tickSize'])    # for price

        buy_quantity = round(ammount_to_invest / float(entry_price), current_symbol_precision)
        print(buy_quantity)

        print(tick_size, step_size)

        buy_quantity_rounded = self.round_step(value=buy_quantity, step=step_size)
        tp_rounded = self.round_step(value=tp, step=tick_size)
        sl_rounded = self.round_step(value=sl, step=tick_size)

        print(tp_rounded, sl_rounded)

        # order = client.futures_create_order(symbol=symbol, side="BUY", type="MARKET", quantity=buy_quantity_rounded)
        # stop_order = client.futures_create_order(symbol=symbol, side="SELL", type="TAKE_PROFIT_MARKET", quantity=buy_quantity_rounded, stopPrice=tp_rounded)
        # take_profit_order = client.futures_create_order(symbol=symbol, side="SELL", type="STOP_MARKET", quantity=buy_quantity_rounded, stopPrice=sl_rounded)

        # twm = ThreadedWebsocketManager(api_key=self.binance_api_key, api_secret=self.binance_api_secret)
        # twm.start()

        # print(stop_order)
        # print(take_profit_order)

        # take_profit_order_id = take_profit_order
        # stop_loss_order_id = stop_order

        # active_order_ids = {
        #     "tp": take_profit_order_id,
        #     "sl": stop_loss_order_id
        # }

        def handle_socket_msg(msg):
            if msg['e'] == 'ORDER_TRADE_UPDATE':
                order = msg['o']
                order_id = order['i']
                status = order['X']  # e.g., 'FILLED', 'CANCELED'
                if order_id in active_order_ids.values() and status == 'FILLED':
                    print(f"Order filled: {order_id}")
                    # Cancel the other one
                    for label, oid in active_order_ids.items():
                        if oid != order_id:
                            try:
                                client.futures_cancel_order(
                                    symbol='BTCUSDT',
                                    orderId=oid
                                )
                                print(f"Canceled {label.upper()} order {oid}")
                            except Exception as e:
                                print(f"Could not cancel {label.upper()} order: {e}")
                    # Stop the WebSocket if you want
                    twm.stop()


        # twm.start_futures_user_socket(callback=handle_socket_msg)