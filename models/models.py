from pydantic import BaseModel

class BotInitializer(BaseModel):
    phone_number: str
    telegram_api_id: int
    telegram_api_hash: str
    binance_api_key: str
    binance_api_secret: str
    chat_id: int