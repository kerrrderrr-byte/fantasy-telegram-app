# handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from keyboard import get_start_keyboard
from ai_client import get_ai_response

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🌟 *Добро пожаловать в «Мир Теней и Огня»!*\n\n"
        "Здесь каждый шаг — выбор. Каждое слово — заклинание. "
        "Мир живёт и дышит... и ждёт *тебя*.\n\n"
        "Готов?\nНажми — и ступай в неизведанное.",
        reply_markup=get_start_keyboard(),
        parse_mode="Markdown"
    )

@router.message(F.text == "⚔️ Начать приключение")
async def start_adventure(message: Message):
    # Первое повествование от ИИ
    intro = await get_ai_response("старт приключения", context="Начало игры")
    await message.answer(intro, parse_mode="Markdown")

@router.message()
async def handle_user_action(message: Message):
    # Пользователь описывает действие — отправляем в ИИ
    user_action = message.text.strip()
    response = await get_ai_response(user_action)
    await message.answer(response, parse_mode="Markdown")