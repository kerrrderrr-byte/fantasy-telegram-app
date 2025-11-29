import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

async def narrate_with_deepseek(facts: dict) -> str:
    """
    Генерирует повествование на основе механических фактов.
    """
    if not DEEPSEEK_API_KEY:
        return "ИИ недоступен. Повествование отключено."

    system_prompt = """
Ты — великий повествователь фэнтези-мира "Fantasy Quest".
Твоя задача — описать событие ярко, эмоционально и кинематографично.
НЕ упоминай цифры, HP, урон, золото.
НЕ выдумывай исход — просто опиши то, что произошло.
Пиши на русском, 2–4 предложения.
"""

    user_prompt = f"""
Игрок: {facts.get('player_name', 'Герой')}
Класс: {facts.get('class', 'неизвестен')}
Событие: {facts.get('event_summary', 'что-то произошло')}
Результат: {facts.get('outcome_description', '')}
"""

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt.strip()},
                        {"role": "user", "content": user_prompt.strip()}
                    ],
                    "temperature": 0.8,
                    "max_tokens": 300
                }
            )
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            return content.strip()
        else:
            return f"[Ошибка ИИ: {response.status_code}]"
    except Exception as e:
        return f"[ИИ недоступен: {str(e)}]"

# Fallback без ИИ
def narrate_fallback(facts: dict) -> str:
    desc = facts.get("outcome_description", "Событие произошло.")
    return f"Мастер сообщает: {desc}"