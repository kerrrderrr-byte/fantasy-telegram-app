# storyteller.py
import os
import httpx
from typing import List, Dict

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Контекст-системный промпт (настраивайте под ваш мир!)
SYSTEM_PROMPT = (
    "Ты — древний повествователь в фэнтези-мире «Тени и Огня». "
    "Ты описываешь мир, реагируешь на действия игрока живо, детально, с драматизмом и поэзией. "
    "Ты не управляешь игроком — только описываешь последствия его решений. "
    "Используй эмодзи для атмосферы: 🌲, 🐺, 🕯️, 🩸, 🌌. "
    "Отвечай коротко (1–3 абзаца), как в устной саге. Не предлагай варианты — пусть игрок сам решает."
)

async def get_deepseek_response(messages: List[Dict[str, str]]) -> str:
    if not DEEPSEEK_API_KEY:
        return (
            "🧙‍♂️ *Голос эха:* «Ключ DeepSeek не задан. Проверь .env»\n\n"
            "🌲 Лес шелестит листвой. Ветер несёт запах дыма и… старой крови."
        )

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "temperature": 0.85,
        "max_tokens": 500
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(DEEPSEEK_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg:
            return "🔒 *Ошибка авторизации DeepSeek.* Проверь DEEPSEEK_API_KEY в .env"
        elif "429" in error_msg:
            return "⏳ *Лимит запросов.* Подожди 30 секунд."
        else:
            return f"💥 *Ошибка связи с DeepSeek:* `{error_msg[:100]}`"