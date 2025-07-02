from telethon import TelegramClient, events
from binance import Client as BinanceClient
from models.models import BotInitializer
import pandas as pd

from helpfullFunctions.functions import getBotTag

class Bot:
    def __init__(self, bot_info: BotInitializer):
        self.phone_number=bot_info.phone_number
        self.telegram_api_id=bot_info.telegram_api_id
        self.telegram_api_hash=bot_info.telegram_api_hash
        self.binance_api_key=bot_info.binance_api_key
        self.binance_api_secret=bot_info.binance_api_secret
        self.client = TelegramClient('session', self.telegram_api_id, self.telegram_api_hash)
        self.chat_id = None

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

    def printCurrentChatId(self):
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
                print(crypt_slugs)

        await self.client.run_until_disconnected()

    # BINANCE STUFF ------------------------------------------------------------------------------------------

    async def connectBinance(self):
        client = BinanceClient(self.binance_api_key, self.binance_api_secret, testnet=True)
        tickers = client.get_all_tickers()
        df = pd.DataFrame(tickers)
        df.head()
        print(df)
