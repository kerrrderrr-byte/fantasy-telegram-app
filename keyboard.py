# keyboard.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_start_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚔️ Начать приключение")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard