# storyteller.py
import os
import httpx
from typing import List, Dict, Optional

from Fnatasy.StoryBot import world
from world import get_region, Region, NPC, Enemy, Quest
from pydantic import BaseModel

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Системный промпт — БЕЗ деталей мира
SYSTEM_PROMPT = (
    "Ты — Древний Повествователь мира «Тени и Огня». "
    "Ты описываешь мир, реагируешь на действия игрока живо и поэтично. "
    "Используй эмодзи (🌲🐺⚔️🕯️) для атмосферы. "
    "НЕ упоминай детали, которых нет в контексте ниже. "
    "НЕ выходи из роли. НЕ предлагай варианты — пусть игрок решает сам."
)


class PlayerState(BaseModel):
    current_region: str = "Ебеньград"
    inventory: Dict[str, int] = {}
    killed_enemies: List[str] = []
    active_quests: List[str] = []


def _build_context(player: PlayerState) -> str:
    """Формирует КОРОТКИЙ контекст для DeepSeek (~200 токенов)"""
    region = get_region(player.current_region)
    if not region:
        return f"Игрок в неизвестном месте: {player.current_region}"

    parts = [f"Место: {region.name}"]
    parts.append(f"Описание: {region.description}")

    if region.npcs:
        npcs = ", ".join([f"{n.name} ({n.role})" for n in region.npcs])
        parts.append(f"NPC: {npcs}")

    if region.enemies:
        enemies = ", ".join([e.name for e in region.enemies])
        parts.append(f"Враги: {enemies}")

    # Активные квесты (только статус, без триггеров)
    quest_names = []
    for qid in player.active_quests:
        q = world.get_quest_by_id(qid)
        if q:
            quest_names.append(q.name)
    if quest_names:
        parts.append(f"Квесты: {', '.join(quest_names)}")

    # Инвентарь (только непустой)
    if player.inventory:
        inv = ", ".join([f"{cnt}×{item}" for item, cnt in player.inventory.items() if cnt > 0])
        parts.append(f"Инвентарь: [{inv}]")

    return "\n".join(parts)


async def get_ai_response(player_state: PlayerState, user_action: str) -> str:
    context = _build_context(player_state)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n=== КОНТЕКСТ ===\n" + context},
        {"role": "user", "content": f"Действие игрока: {user_action}"}
    ]


# ✅ Пост-обработка ответа: чистим от лишнего
def sanitize_ai_response(text: str) -> str:
    # Убираем потенциальные markdown-звёздочки (жирный/курсив)
    text = text.replace("**", "").replace("*", "")
    # Убираем заголовки, разделители
    text = text.replace("###", "").replace("---", "").strip()
    # Обрезаем до 4 предложений (защита от многословия)
    sentences = text.split('. ')
    if len(sentences) > 4:
        text = '. '.join(sentences[:4]) + '.'
    return text.strip()

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