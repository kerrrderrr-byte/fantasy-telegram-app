import random
import sqlite3
import json
from typing import Dict, Any

# Константы (как раньше)
ENEMY_TYPES = {
    "гоблин": {"hp": 25, "damage": 8, "gold": (5, 10), "loot_chance": 0.3},
    "скелет": {"hp": 30, "damage": 7, "gold": (6, 12), "loot_chance": 0.35},
}
WEAPON_STATS = {
    "Посох ученика": {"type": "magic", "base_damage": 10},
    "Деревянный меч": {"type": "melee", "base_damage": 8},
    "Кинжал разбойника": {"type": "melee", "base_damage": 7},
    "Дубовый лук": {"type": "ranged", "base_damage": 9},
    "Железный меч": {"type": "melee", "base_damage": 12},
}

DB_PATH = "characters.db"

def get_player_damage(player_data: Dict[str, Any]) -> int:
    weapon = player_data["weapon"]
    w = WEAPON_STATS.get(weapon, {"type": "melee", "base_damage": 5})
    base = w["base_damage"]
    if w["type"] == "melee":
        return base + player_data["str"]
    elif w["type"] == "ranged":
        return base + player_data["dex"]
    else:
        return base + player_data["int"]

def start_combat(num: int = 3) -> list:
    return [{"type": "гоблин", "hp": 25, "max_hp": 25, "damage": 8, "gold_range": (5,10), "loot_chance": 0.3} for _ in range(num)]

def process_combat_round(player_data: dict, action: str, enemies: list) -> dict:
    # Найти первого живого врага
    target = None
    for e in enemies:
        if e["hp"] > 0:
            target = e
            break
    if not target:
        return {"error": "Нет целей"}

    # Урон игрока
    dmg = get_player_damage(player_data)
    target["hp"] -= dmg
    killed = target["hp"] <= 0
    if killed:
        target["hp"] = 0

    # Контратака
    player_dmg = sum(e["damage"] for e in enemies if e["hp"] > 0)

    # Лут
    gold, items = 0, []
    if killed:
        gold = random.randint(*target["gold_range"])
        if random.random() < target["loot_chance"]:
            items.append("Зелье здоровья")

    return {
        "player_damage_dealt": dmg,
        "enemy_killed": killed,
        "enemy_type": target["type"],
        "player_damage_taken": player_dmg,
        "gold": gold,
        "items": items,
        "remaining_enemies": len([e for e in enemies if e["hp"] > 0])
    }

def apply_results(user_id: int, result: dict) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT hp, max_hp, inventory FROM characters WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"error": "Игрок не найден"}
    hp, max_hp, inv_str = row
    new_hp = max(0, hp - result["player_damage_taken"])
    alive = new_hp > 0
    inventory = json.loads(inv_str) if inv_str else []
    inventory.extend(result["items"])
    cur.execute(
        "UPDATE characters SET hp = ?, inventory = ? WHERE user_id = ?",
        (new_hp, json.dumps(inventory, ensure_ascii=False), user_id)
    )
    conn.commit()
    conn.close()
    return {"new_hp": new_hp, "alive": alive, "gold": result["gold"], "items": result["items"]}