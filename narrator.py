import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

async def narrate_with_deepseek(facts: dict) -> str:
    """
    Генерирует повествование через DeepSeek на основе подробного сценария.
    """
    if not DEEPSEEK_API_KEY:
        return "ИИ повествования недоступен. Попробуйте позже."

    system_prompt = """
Ты — мастер художественного повествования в фэнтези-мире "Fantasy Quest".
Твоя задача — превратить предоставленный сценарий в яркое, кинематографичное описание сцены боя.
Ты — не игрок, не помощник, не комментатор. Ты — **независимый повествователь**.
Ты **никогда** не упоминаешь:
- HP, урон, цифры, логику, переменные.
- Слова "атака", "урон", "HP", "игрок" (используй имя героя).
- Не описывай мысли ИИ, не объясняй, что ты делаешь.
Ты просто **описываешь события**, как будто это сцена из книги. Используй яркие глаголы, образные описания, эмоции.
"""

    # Формируем детализированный промпт на основе facts
    event_summary = facts.get("event_summary", "")
    player_name = facts.get("player_name", "Герой")
    player_class = facts.get("player_class", "неизвестный")
    action = facts.get("action", "что-то делает")
    enemy_killed = facts.get("enemy_killed", False)
    enemy_type_killed = facts.get("enemy_type_killed", "")
    remaining_enemies = facts.get("remaining_enemies", 0)
    player_damage_taken = facts.get("player_damage_taken", 0)
    new_hp = facts.get("new_hp", 100)
    max_hp = facts.get("max_hp", 100)
    combat_continues = facts.get("combat_continues", False)
    victory = facts.get("victory", False)
    defeat = facts.get("defeat", False)

    # --- Формируем user_prompt ---
    user_prompt = f"""
Сценарий:
- Герой: {player_name} ({player_class}).
- Действие героя: {action}.
- Результат действия: """

    if enemy_killed:
        user_prompt += f"{player_name} убивает {enemy_type_killed}. "
    else:
        user_prompt += f"{player_name} атакует, но {enemy_type_killed or 'враг'} выживает. "

    if player_damage_taken > 0:
        user_prompt += f"Оставшиеся враги контратакуют и наносят {player_damage_taken} урона {player_name}. "
    else:
        user_prompt += f"{player_name} избегает вражеских атак. "

    if victory:
        user_prompt += f"Все враги повержены. {player_name} одерживает победу."
    elif defeat:
        user_prompt += f"{player_name} падает в бою."
    else:
        user_prompt += f"Бой продолжается. Осталось врагов: {remaining_enemies}."
    # user_prompt += f" (Внутренние данные: HP игрока: было {facts.get('prev_hp', 'N/A')}, стало {new_hp}/{max_hp})" # <-- Это не включаем в промпт ИИ

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
                    "temperature": 0.85, # Выше для творческого стиля
                    "max_tokens": 350
                }
            )
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            return content.strip()
        else:
            print(f"[DEBUG] DeepSeek error: {response.status_code}, {response.text}")
            return "Мастер говорит: Что-то пошло не так при генерации повествования. Попробуйте снова."
    except Exception as e:
        print(f"[DEBUG] Narrator error: {e}")
        return "Мастер говорит: ИИ повествования временно недоступен. Попробуйте позже."

# Резервный вариант (не идеален, но хотя бы без цифр)
def narrate_fallback(facts: dict) -> str:
    player_name = facts.get("player_name", "Герой")
    action = facts.get("action", "что-то делает")
    enemy_killed = facts.get("enemy_killed", False)
    enemy_type_killed = facts.get("enemy_type_killed", "")
    player_damage_taken = facts.get("player_damage_taken", 0)
    remaining_enemies = facts.get("remaining_enemies", 0)
    victory = facts.get("victory", False)
    defeat = facts.get("defeat", False)

    if defeat:
        return f"{player_name} пал в бою... Тьма окутывает сознание."

    if victory:
        return f"{player_name} одерживает победу! Последний враг падает, и тишина вновь окутывает место схватки."

    desc = f"{player_name} {action}. "
    if enemy_killed:
        desc += f"Один {enemy_type_killed} падает замертво. "
    if player_damage_taken > 0:
        desc += f"Контратака врагов рвет плоть, причиняя боль. "
    else:
        desc += f"Ты уворачиваешься от ответных ударов. "
    desc += f"Бой продолжается. Осталось врагов: {remaining_enemies}."
    return desc
