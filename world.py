# world.py
from typing import Dict, List, Optional
from enum import Enum

class Region(str, Enum):
    EBENGRAD = "Ебеньград"
    LOGOVO_RYZHAYA = "Логово Рыжей"

class NPC:
    def __init__(self, name: str, role: str, description: str, dialogue: str):
        self.name = name
        self.role = role
        self.description = description
        self.dialogue = dialogue

class Enemy:
    def __init__(self, name: str, description: str, hp: int = 100):
        self.name = name
        self.description = description
        self.hp = hp

class Quest:
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        trigger_condition: str,
        completion_condition: str,
        reward: str
    ):
        self.id = id
        self.name = name
        self.description = description
        self.trigger_condition = trigger_condition  # например: "куплено 2 бутера и кофе"
        self.completion_condition = completion_condition  # "Рыжая ведьма побеждена"
        self.reward = reward

class RegionData:
    def __init__(
        self,
        name: Region,
        description: str,
        npcs: List[NPC],
        enemies: List[Enemy],
        quests: List[Quest],
        exits: List[Region]
    ):
        self.name = name
        self.description = description
        self.npcs = npcs
        self.enemies = enemies
        self.quests = quests
        self.exits = exits

# ====== ОПИСАНИЕ МИРА ======
REGIONS: Dict[Region, RegionData] = {}

# NPC
sanja = NPC(
    name="Саня",
    role="Бармен",
    description="Полный, добродушный мужик в фартуке. Всегда с тряпкой и чашкой кофе.",
    dialogue="«Эй, странник! Бутер с колбасой — 10 монет. Кофе — 5. А у той ведьмы в логове... эх, забыл, что собирался сказать»."
)

# Враги
ryzhaya_witch = Enemy(
    name="Рыжая ведьма",
    description="Высокая женщина в лохмотьях, с огненно-рыжими волосами и пустыми глазницами. В руках — костяной посох, из которого сочится чёрная слизь.",
    hp = 250
)

# Квесты
quest_kill_witch = Quest(
    id="kill_ryzhaya_witch",
    name="Избавь Ебеньград от проклятия",
    description="Саня шепнул, что ведьма похищает детей по ночам. Найди её логово и уничтожь.",
    trigger_condition="player.inventory.get('Бутерброд') >= 2 and player.inventory.get('Кофе') >= 1",
    completion_condition="player.killed_enemies.contains('Рыжая ведьма')",
    reward="50 золотых, +репутация 'Защитник Ебеньграда'"
)

# Регионы
REGIONS[Region.EBENGRAD] = RegionData(
    name=Region.EBENGRAD,
    description=(
        "Городок на болоте. Кривые домишки на сваях, вонь тины и жареной колбасы. "
        "В центре — таверна «Бутерброды у Сани», откуда доносится гул голосов и звон кружек."
    ),
    npcs=[sanja],
    enemies=[],
    quests=[quest_kill_witch],
    exits=[Region.LOGOVO_RYZHAYA]
)

REGIONS[Region.LOGOVO_RYZHAYA] = RegionData(
    name=Region.LOGOVO_RYZHAYA,
    description=(
        "Тёмная пещера под корнями гнилого дуба. Стены покрыты слизью и рунами. "
        "Воздух гудит от магии. В глубине — алтарь из черепов."
    ),
    npcs=[],
    enemies=[ryzhaya_witch],
    quests=[],
    exits=[Region.EBENGRAD]
)

def get_region(name: str) -> Optional[RegionData]:
    return REGIONS.get(Region(name), None)

def get_quest_by_id(quest_id: str) -> Optional[Quest]:
    for region in REGIONS.values():
        for q in region.quests:
            if q.id == quest_id:
                return q
    return None