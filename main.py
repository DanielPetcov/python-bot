import os
import asyncio

from dotenv import load_dotenv

from models.models import BotInitializer

from classes.bot import Bot

load_dotenv()

async def main():
    bot_initializer = BotInitializer(
        phone_number=os.getenv('PHONE_NUMBER'),
        telegram_api_id=os.getenv('TELEGRAM_API_ID'),
        telegram_api_hash=os.getenv('TELEGRAM_API_HASH'),
        binance_api_key=os.getenv('BINANCE_API_KEY'),
        binance_api_secret=os.getenv('BINANCE_API_SECRET')
    )
    bot_itself = Bot(bot_initializer)

    while True:
        print("\nEnter what you need:")
        print("1. Connect")
        print("2. Disconnect")
        print("3. Print a list of chats")
        print('4. Modify a chat')
        print("5. Start the listener")
        print("6. Connect Binance")
        print("7. Exit the app.")
        option = input("Enter: ")

        match option:
            case "1":
                await bot_itself.start()
            case "2":
                await bot_itself.stop()
            case "3":
                await bot_itself.printChats()
            case "4":
                await bot_itself.modifyChat()
            case "5":
                await bot_itself.btcHandler()
            case "6":
                await bot_itself.connectBinance()
            case "7":
                await bot_itself.stop()
                break
            case _:
                print("Invalid option")

if __name__ == "__main__":
    asyncio.run(main())