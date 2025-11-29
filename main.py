from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import sqlite3
import os
import re
import json
from dotenv import load_dotenv

# Загружаем .env (для TELEGRAM_BOT_TOKEN, если понадобится в будущем)
load_dotenv()

# Импортируем модули — они должны лежать в той же папке
from narrator import narrate_with_deepseek, narrate_fallback  # Подключаем ИИ и резерв
from judge import start_combat, process_combat_round, apply_results

app = FastAPI()

DB_PATH = "characters.db"

# === КОНСТАНТЫ ИГРЫ ===
CLASS_DESCRIPTIONS = {
    "Маг": "Владыка стихий и древних заклинаний. Наносит огромный магический урон, но хрупок в ближнем бою.",
    "Воин": "Неудержимая сила и ярость. Высокое здоровье и урон в ближнем бою.",
    "Ассасин": "Тень, что поражает с тыла. Высокий критический урон и уклонение.",
    "Лучник": "Мастер дистанционного боя. Наносит урон издалека с высокой точностью.",
    "Рыцарь": "Щит и меч королевства. Высокая защита и выносливость.",
}

CLASS_STATS = {
    "Маг": {"str": 5, "dex": 8, "int": 18},
    "Воин": {"str": 18, "dex": 8, "int": 5},
    "Ассасин": {"str": 12, "dex": 18, "int": 8},
    "Лучник": {"str": 10, "dex": 16, "int": 10},
    "Рыцарь": {"str": 16, "dex": 10, "int": 8},
}

STARTING_GEAR = {
    "Маг": {"weapon": "Посох ученика", "armor": "Мантия новичка"},
    "Воин": {"weapon": "Деревянный меч", "armor": "Кожаный доспех"},
    "Ассасин": {"weapon": "Кинжал разбойника", "armor": "Тёмная одежда"},
    "Лучник": {"weapon": "Дубовый лук", "armor": "Лёгкая куртка"},
    "Рыцарь": {"weapon": "Железный меч", "armor": "Кольчуга"},
}

ARMOR_STATS = {
    "Мантия новичка": {"hp_bonus": 10},
    "Кожаный доспех": {"hp_bonus": 20},
    "Тёмная одежда": {"hp_bonus": 15},
    "Лёгкая куртка": {"hp_bonus": 18},
    "Кольчуга": {"hp_bonus": 25},
}

WEAPON_STATS = {
    "Посох ученика": {"type": "magic", "base_damage": 10},
    "Деревянный меч": {"type": "melee", "base_damage": 8},
    "Кинжал разбойника": {"type": "melee", "base_damage": 7},
    "Дубовый лук": {"type": "ranged", "base_damage": 9},
    "Железный меч": {"type": "melee", "base_damage": 12},
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Проверяем, есть ли столбец combat_state
    cursor.execute("PRAGMA table_info(characters)")
    columns = [column[1] for column in cursor.fetchall()]
    if "combat_state" not in columns:
        cursor.execute("ALTER TABLE characters ADD COLUMN combat_state TEXT DEFAULT '{}'")
        print("Столбец 'combat_state' добавлен в таблицу 'characters'.")
    else:
        print("Столбец 'combat_state' уже существует.")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            user_id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            nickname TEXT,
            name TEXT,
            class TEXT,
            level INTEGER DEFAULT 1,
            str INTEGER DEFAULT 0,
            dex INTEGER DEFAULT 0,
            int INTEGER DEFAULT 0,
            stat_points INTEGER DEFAULT 3,
            hp INTEGER DEFAULT 100,
            max_hp INTEGER DEFAULT 100,
            mana INTEGER DEFAULT 100,
            max_mana INTEGER DEFAULT 100,
            weapon TEXT,
            armor TEXT,
            inventory TEXT DEFAULT '[]',
            adventure_log TEXT DEFAULT '[]'
            -- combat_state добавлен через ALTER TABLE выше
        )
    """)
    conn.commit()
    conn.close()


# === МОДЕЛИ ===
class UsernameCreate(BaseModel):
    user_id: int
    username: str


class CharacterCreate(BaseModel):
    user_id: int
    class_name: str


class StatUpdate(BaseModel):
    user_id: int
    stat: str


# === HTML ЭКРАНЫ ===

@app.get("/app", response_class=HTMLResponse)
def screen_username():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fantasy Quest</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { font-family: system-ui; background: #0f0c1a; color: white; padding: 20px; margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; }
            .container { width: 100%; max-width: 350px; text-align: center; }
            h1 { color: #8a6bff; }
            input { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #8a6bff; background: #1a1726; color: white; margin: 20px 0; box-sizing: border-box; }
            .btn { background: #8a6bff; color: white; border: none; border-radius: 8px; padding: 12px 24px; font-size: 16px; cursor: pointer; width: 100%; }
            .error { color: #ff6b6b; margin: 10px 0; }
            .loading { color: #8a6bff; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧙 Fantasy Quest</h1>
            <div class="loading" id="loading">Проверка аккаунта...</div>
            <div id="form" style="display:none;">
                <p>Выбери уникальное имя героя (3–16 символов, буквы и цифры)</p>
                <input type="text" id="username" placeholder="Например: DarkMage" maxlength="16">
                <div class="error" id="error"></div>
                <button class="btn" onclick="submitUsername()">Далее</button>
            </div>
        </div>
        <script>
            Telegram.WebApp.ready(); Telegram.WebApp.expand();
            const user = Telegram.WebApp.initDataUnsafe?.user;
            if (!user) {
                document.body.innerHTML = '<div style="text-align:center;padding:50px;color:red;">❌ Вне Telegram!</div>';
            } else {
                fetch(`/api/character/${user.id}`)
                    .then(res => {
                        if (res.ok) {
                            window.location.href = '/app/main_menu?user_id=' + user.id;
                        } else {
                            document.getElementById('loading').style.display = 'none';
                            document.getElementById('form').style.display = 'block';
                        }
                    });
            }
            async function submitUsername() {
                const username = document.getElementById('username').value.trim();
                const errorDiv = document.getElementById('error');
                errorDiv.textContent = '';
                if (!username || username.length < 3) { errorDiv.textContent = 'Ник от 3 символов'; return; }
                if (!/^[a-zA-Z0-9_]{3,16}$/.test(username)) { errorDiv.textContent = 'Только буквы, цифры, _'; return; }
                try {
                    const res = await fetch('/api/check_username', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({user_id: user.id, username: username})
                    });
                    const data = await res.json();
                    if (res.ok) {
                        window.location.href = '/app/class_select?user_id=' + user.id;
                    } else {
                        errorDiv.textContent = data.detail;
                    }
                } catch (e) { errorDiv.textContent = 'Ошибка сети'; }
            }
        </script>
    </body>
    </html>
    """


@app.get("/app/class_select", response_class=HTMLResponse)
def screen_class_select():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Выбор класса</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { font-family: system-ui; background: #0f0c1a; color: white; padding: 20px; margin: 0; }
            .container { max-width: 500px; margin: 0 auto; }
            h1 { color: #8a6bff; text-align: center; }
            .class-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 20px; }
            .class-btn { background: #1a1726; color: white; border: 2px solid #8a6bff; border-radius: 12px; padding: 16px; font-size: 16px; cursor: pointer; transition: all 0.2s; text-align: center; }
            .class-btn:hover { background: #8a6bff; transform: scale(1.03); }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚔️ Выбери класс</h1>
            <div class="class-grid">
                <div class="class-btn" onclick="showClass('Маг')">Маг</div>
                <div class="class-btn" onclick="showClass('Воин')">Воин</div>
                <div class="class-btn" onclick="showClass('Ассасин')">Ассасин</div>
                <div class="class-btn" onclick="showClass('Лучник')">Лучник</div>
                <div class="class-btn" onclick="showClass('Рыцарь')">Рыцарь</div>
            </div>
        </div>
        <script>
            Telegram.WebApp.ready(); Telegram.WebApp.expand();
            const urlParams = new URLSearchParams(window.location.search);
            const userId = parseInt(urlParams.get('user_id'));
            function showClass(className) {
                window.location.href = '/app/class_info?class=' + encodeURIComponent(className) + '&user_id=' + userId;
            }
        </script>
    </body>
    </html>
    """


@app.get("/app/class_info", response_class=HTMLResponse)
def screen_class_info():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Описание класса</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { font-family: system-ui; background: #0f0c1a; color: white; padding: 20px; margin: 0; }
            .container { max-width: 500px; margin: 0 auto; }
            .back { color: #8a6bff; cursor: pointer; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; }
            h1 { color: #8a6bff; text-align: center; }
            .desc { background: #1a1726; padding: 20px; border-radius: 12px; margin: 20px 0; line-height: 1.5; }
            .confirm-btn { background: #8a6bff; color: white; border: none; border-radius: 8px; padding: 14px; font-size: 18px; cursor: pointer; width: 100%; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="back" onclick="goBack()"><span>←</span> Назад к выбору</div>
            <h1 id="class-title">Загрузка...</h1>
            <div class="desc" id="class-desc">...</div>
            <button class="confirm-btn" onclick="confirmClass()">Выбрать этот класс</button>
        </div>
        <script>
            Telegram.WebApp.ready(); Telegram.WebApp.expand();
            const urlParams = new URLSearchParams(window.location.search);
            const className = decodeURIComponent(urlParams.get('class'));
            const userId = parseInt(urlParams.get('user_id')); // <-- parseInt добавлен
            const descriptions = {
                "Маг": "Владыка стихий и древних заклинаний. Наносит огромный магический урон, но хрупок в ближнем бою.",
                "Воин": "Неудержимая сила и ярость. Высокое здоровье и урон в ближнем бою.",
                "Ассасин": "Тень, что поражает с тыла. Высокий критический урон и уклонение.",
                "Лучник": "Мастер дистанционного боя. Наносит урон издалека с высокой точности.",
                "Рыцарь": "Щит и меч королевства. Высокая защита и выносливость."
            };
            document.getElementById('class-title').textContent = className;
            document.getElementById('class-desc').textContent = descriptions[className] || 'Описание отсутствует';
            function goBack() { window.location.href = '/app/class_select?user_id=' + userId; }
            async function confirmClass() {
                try {
                    const res = await fetch('/api/create_character', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        // Убедимся, что user_id - число
                        body: JSON.stringify({user_id: parseInt(userId), class_name: className}) 
                    });
                    if (res.ok) window.location.href = '/app/main_menu?user_id=' + userId;
                    else {
                        const errorData = await res.json();
                        console.error("Ошибка API:", errorData);
                        alert('Ошибка создания персонажа: ' + (errorData.detail || 'Неизвестная ошибка'));
                    }
                } catch (e) { 
                    console.error("Ошибка сети:", e); 
                    alert('Ошибка сети'); 
                }
            }
        </script>
    </body>
    </html>
    """


@app.get("/app/main_menu", response_class=HTMLResponse)
def screen_main_menu():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Главное меню</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { font-family: system-ui; background: #0f0c1a; color: white; padding: 20px; margin: 0; }
            .container { max-width: 500px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 20px; }
            .nickname { color: gold; font-size: 20px; }
            h1 { color: #8a6bff; }
            .menu-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-top: 20px; }
            .menu-btn { background: #1a1726; color: white; border: 2px solid #8a6bff; border-radius: 12px; padding: 20px; font-size: 16px; cursor: pointer; transition: all 0.2s; text-align: center; }
            .menu-btn:hover { background: #8a6bff; transform: scale(1.03); }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="nickname" id="nickname">Загрузка...</div>
                <h1>🏰 Главное меню</h1>
            </div>
            <div class="menu-grid">
                <div class="menu-btn" onclick="goTo('/app/adventure')">Приключение</div>
                <div class="menu-btn" onclick="goTo('/app/friends')">Друзья</div>
                <div class="menu-btn" onclick="goTo('/app/clans')">Кланы</div>
                <div class="menu-btn" onclick="goTo('/app/profile')">Профиль</div>
                <div class="menu-btn" onclick="goTo('/app/character')">Персонаж</div>
                <div class="menu-btn" onclick="goTo('/app/inventory')">Инвентарь</div>
            </div>
        </div>
        <script>
            Telegram.WebApp.ready(); Telegram.WebApp.expand();
            const urlParams = new URLSearchParams(window.location.search);
            const userId = parseInt(urlParams.get('user_id'));
            async function loadNickname() {
                try {
                    const res = await fetch(`/api/character/${userId}`);
                    const data = await res.json();
                    if (res.ok) {
                        document.getElementById('nickname').textContent = data.nickname || 'Герой';
                    }
                } catch (e) { console.error(e); }
            }
            function goTo(path) {
                window.location.href = path + '?user_id=' + userId;
            }
            loadNickname();
        </script>
    </body>
    </html>
    """


@app.get("/app/character", response_class=HTMLResponse)
def screen_character():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Мой персонаж</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { font-family: system-ui; background: #0f0c1a; color: white; padding: 20px; margin: 0; }
            .container { max-width: 500px; margin: 0 auto; }
            .back { color: #8a6bff; cursor: pointer; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; }
            h1 { color: #8a6bff; text-align: center; }
            .stat { background: #1a1726; padding: 15px; border-radius: 12px; margin: 12px 0; display: flex; justify-content: space-between; align-items: center; }
            .btn { background: #8a6bff; color: white; border: none; border-radius: 8px; padding: 8px 16px; cursor: pointer; }
            .points { text-align: center; margin: 20px 0; font-size: 18px; color: gold; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="back" onclick="goBack()"><span>←</span> Назад в меню</div>
            <h1>🛡️ <span id="nickname">Герой</span></h1>
            <div class="points" id="points">Загрузка...</div>
            <div class="stat">
                <span>Сила</span>
                <div><span id="str-val">0</span> <button class="btn" onclick="addStat('str')" id="str-btn">+</button></div>
            </div>
            <div class="stat">
                <span>Ловкость</span>
                <div><span id="dex-val">0</span> <button class="btn" onclick="addStat('dex')" id="dex-btn">+</button></div>
            </div>
            <div class="stat">
                <span>Интеллект</span>
                <div><span id="int-val">0</span> <button class="btn" onclick="addStat('int')" id="int-btn">+</button></div>
            </div>
        </div>
        <script>
            Telegram.WebApp.ready(); Telegram.WebApp.expand();
            const urlParams = new URLSearchParams(window.location.search);
            const userId = parseInt(urlParams.get('user_id'));
            let points = 0;
            function goBack() {
                window.location.href = '/app/main_menu?user_id=' + userId;
            }
            async function loadCharacter() {
                try {
                    const res = await fetch(`/api/character/${userId}`);
                    const data = await res.json();
                    if (res.ok) {
                        document.getElementById('nickname').textContent = data.nickname || 'Герой';
                        document.getElementById('str-val').textContent = data.str;
                        document.getElementById('dex-val').textContent = data.dex;
                        document.getElementById('int-val').textContent = data.int;
                        points = data.stat_points;
                        document.getElementById('points').textContent = `Очки характеристик: ${points}`;
                        updateButtons();
                    }
                } catch (e) { console.error(e); }
            }
            function updateButtons() {
                const btns = ['str', 'dex', 'int'];
                btns.forEach(stat => {
                    const btn = document.getElementById(`${stat}-btn`);
                    btn.disabled = points <= 0;
                    btn.style.opacity = points > 0 ? '1' : '0.5';
                });
            }
            async function addStat(stat) {
                if (points <= 0) return;
                try {
                    const res = await fetch('/api/add_stat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: userId, stat: stat })
                    });
                    if (res.ok) {
                        points -= 1;
                        const val = parseInt(document.getElementById(`${stat}-val`).textContent) + 1;
                        document.getElementById(`${stat}-val`).textContent = val;
                        document.getElementById('points').textContent = `Очки характеристик: ${points}`;
                        updateButtons();
                    }
                } catch (e) { alert('Ошибка'); }
            }
            loadCharacter();
        </script>
    </body>
    </html>
    """


@app.get("/app/inventory", response_class=HTMLResponse)
def screen_inventory():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Инвентарь</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { font-family: system-ui; background: #0f0c1a; color: white; padding: 20px; margin: 0; }
            .container { max-width: 500px; margin: 0 auto; }
            .back { color: #8a6bff; cursor: pointer; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; }
            h1 { color: #8a6bff; text-align: center; }
            .item { background: #1a1726; padding: 12px; border-radius: 8px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="back" onclick="goBack()"><span>←</span> Назад в меню</div>
            <h1>🎒 Инвентарь</h1>
            <div id="items">Загрузка...</div>
        </div>
        <script>
            Telegram.WebApp.ready(); Telegram.WebApp.expand();
            const urlParams = new URLSearchParams(window.location.search);
            const userId = parseInt(urlParams.get('user_id'));
            function goBack() {
                window.location.href = '/app/main_menu?user_id=' + userId;
            }
            async function loadInventory() {
                try {
                    const res = await fetch(`/api/character/${userId}`);
                    const data = await res.json();
                    if (res.ok) {
                        let html = '';
                        const weapon = data.weapon;
                        const WEAPON_STATS = {
                            "Посох ученика": {type: "magic", base: 10},
                            "Деревянный меч": {type: "melee", base: 8},
                            "Кинжал разбойника": {type: "melee", base: 7},
                            "Дубовый лук": {type: "ranged", base: 9},
                            "Железный меч": {type: "melee", base: 12},
                        };
                        const weaponStat = WEAPON_STATS[weapon] || {base: 0, type: "melee"};
                        let bonus = 0;
                        if (weaponStat.type === "melee") bonus = data.str;
                        else if (weaponStat.type === "ranged") bonus = data.dex;
                        else if (weaponStat.type === "magic") bonus = data.int;
                        const totalDamage = weaponStat.base + bonus;
                        html += `<div class="item"><strong>Оружие:</strong> ${weapon} (${weaponStat.base} + ${bonus} = ${totalDamage} урона)</div>`;
                        html += `<div class="item"><strong>Броня:</strong> ${data.armor}</div>`;
                        html += `<div class="item">Доп. предметы: (пока нет)</div>`;
                        document.getElementById('items').innerHTML = html;
                    }
                } catch (e) { console.error(e); }
            }
            loadInventory();
        </script>
    </body>
    </html>
    """


@app.get("/app/adventure", response_class=HTMLResponse)
def adventure_screen():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Приключение</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { font-family: system-ui; background: #0f0c1a; color: white; padding: 20px; margin: 0; }
            .container { max-width: 500px; margin: 0 auto; }
            .back { color: #8a6bff; cursor: pointer; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; }
            h1 { color: #8a6bff; text-align: center; }
            .log { background: #1a1726; padding: 15px; border-radius: 12px; margin: 10px 0; height: 300px; overflow-y: auto; line-height: 1.5; }
            .input-area { display: flex; gap: 10px; margin-top: 15px; }
            input { flex: 1; padding: 12px; border-radius: 8px; border: 1px solid #8a6bff; background: #1a1726; color: white; }
            button { background: #8a6bff; color: white; border: none; border-radius: 8px; padding: 12px 16px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="back" onclick="goBack()"><span>←</span> Назад в меню</div>
            <h1>🌲 Приключение</h1>
            <div class="log" id="log">Нажми "Начать", чтобы начать приключение...</div>
            <div class="input-area">
                <input type="text" id="action" placeholder="Что ты делаешь?" />
                <button onclick="sendAction()">Отправить</button>
            </div>
        </div>
        <script>
            Telegram.WebApp.ready(); Telegram.WebApp.expand();
            const urlParams = new URLSearchParams(window.location.search);
            const userId = parseInt(urlParams.get('user_id'));
            let conversation = [];

            function goBack() {
                window.location.href = '/app/main_menu?user_id=' + userId;
            }

            async function startAdventure() {
                try {
                    const res = await fetch(`/api/adventure?user_id=${userId}&action=start`);
                    const data = await res.json();
                    if (res.ok) {
                        conversation = [{role: "assistant", content: data.narrative}];
                        document.getElementById('log').innerHTML = formatLog(conversation);
                    } else {
                        document.getElementById('log').textContent = 'Ошибка: ' + data.detail;
                    }
                } catch (e) {
                    document.getElementById('log').textContent = 'Ошибка сети';
                }
            }

            async function sendAction() {
                const input = document.getElementById('action');
                const action = input.value.trim();
                if (!action) return;

                conversation.push({role: "user", content: action});
                document.getElementById('log').innerHTML = formatLog(conversation);

                try {
                    const res = await fetch(`/api/adventure?user_id=${userId}&action=${encodeURIComponent(action)}`);
                    const data = await res.json();
                    if (res.ok) {
                        conversation.push({role: "assistant", content: data.narrative});
                        document.getElementById('log').innerHTML = formatLog(conversation);
                    } else {
                        conversation.push({role: "assistant", content: "Ошибка: " + data.detail});
                        document.getElementById('log').innerHTML = formatLog(conversation);
                    }
                } catch (e) {
                    conversation.push({role: "assistant", content: "Ошибка сети"});
                    document.getElementById('log').innerHTML = formatLog(conversation);
                }

                input.value = '';
            }

            function formatLog(log) {
                return log.map(msg => {
                    if (msg.role === "user") return `<div><strong>Ты:</strong> ${msg.content}</div>`;
                    else return `<div><strong>Мастер:</strong> ${msg.content}</div>`;
                }).join('<br>');
            }

            startAdventure();
        </script>
    </body>
    </html>
    """


# === Заглушки ===
@app.get("/app/friends", response_class=HTMLResponse)
def friends():
    return """
    <div style="color:white;background:#0f0c1a;padding:20px;">
        <div style="color:#8a6bff;cursor:pointer;margin-bottom:20px;" onclick="history.back()">← Назад в меню</div>
        <h1>👥 Друзья скоро будут!</h1>
    </div>
    <script>Telegram.WebApp.ready();</script>
    """


@app.get("/app/clans", response_class=HTMLResponse)
def clans():
    return """
    <div style="color:white;background:#0f0c1a;padding:20px;">
        <div style="color:#8a6bff;cursor:pointer;margin-bottom:20px;" onclick="history.back()">← Назад в меню</div>
        <h1>🏰 Кланы скоро будут!</h1>
    </div>
    <script>Telegram.WebApp.ready();</script>
    """


@app.get("/app/profile", response_class=HTMLResponse)
def profile():
    return """
    <div style="color:white;background:#0f0c1a;padding:20px;">
        <div style="color:#8a6bff;cursor:pointer;margin-bottom:20px;" onclick="history.back()">← Назад в меню</div>
        <h1>👤 Профиль скоро будет!</h1>
    </div>
    <script>Telegram.WebApp.ready();</script>
    """


# === API ЭНДПОИНТЫ ===

@app.post("/api/check_username")
async def check_username(data: UsernameCreate): # <-- Явно указываем имя и тип параметра
    if not re.match(r"^[a-zA-Z0-9_]{3,16}$", data.username):
        raise HTTPException(status_code=400, detail="Неверный формат ника")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM characters WHERE username = ?", (data.username,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Такой ник уже занят")
    cursor.execute("INSERT OR REPLACE INTO characters (user_id, username) VALUES (?, ?)", (data.user_id, data.username))
    conn.commit()
    conn.close()


@app.post("/api/create_character")
async def create_character(data: CharacterCreate): # <-- Явно указываем имя и тип параметра
    if data.class_name not in CLASS_STATS:
        raise HTTPException(status_code=400, detail="Неверный класс")
    base = CLASS_STATS[data.class_name]
    gear = STARTING_GEAR[data.class_name]
    weapon = gear["weapon"]
    armor = gear["armor"]
    armor_bonus = ARMOR_STATS[armor]["hp_bonus"]
    max_hp = 80 + base["str"] * 4 + armor_bonus
    max_mana = 50 + base["int"] * 5
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE characters 
        SET class = ?, str = ?, dex = ?, int = ?, stat_points = 3,
            nickname = username,
            weapon = ?, armor = ?,
            hp = ?, max_hp = ?,
            mana = ?, max_mana = ?,
            inventory = ?
        WHERE user_id = ?
    """, (
        data.class_name, base["str"], base["dex"], base["int"],
        weapon, armor,
        max_hp, max_hp,
        max_mana, max_mana,
        '[]',
        data.user_id
    ))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/api/character/{user_id}")
async def get_character(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nickname, class, str, dex, int, stat_points, 
               hp, max_hp, mana, max_mana, weapon, armor, inventory
        FROM characters WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Персонаж не найден")
    return {
        "nickname": row[0],
        "class": row[1],
        "str": row[2],
        "dex": row[3],
        "int": row[4],
        "stat_points": row[5],
        "hp": row[6],
        "max_hp": row[7],
        "mana": row[8],
        "max_mana": row[9],
        "weapon": row[10],
        "armor": row[11],
        "inventory": row[12],
    }


@app.post("/api/add_stat")
async def add_stat(data: StatUpdate): # <-- Явно указываем имя и тип параметра
    if data.stat not in ["str", "dex", "int"]:
        raise HTTPException(status_code=400, detail="Неверная характеристика")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT stat_points FROM characters WHERE user_id = ?", (data.user_id,))
    row = cursor.fetchone()
    if not row or row[0] <= 0:
        raise HTTPException(status_code=400, detail="Нет очков характеристик")
    cursor.execute(
        f"UPDATE characters SET {data.stat} = {data.stat} + 1, stat_points = stat_points - 1 WHERE user_id = ?",
        (data.user_id,)
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


# === ГЛАВНЫЙ ИЗМЕНЁННЫЙ ЭНДПОИНТ ПРИКЛЮЧЕНИЯ ===
@app.get("/api/adventure")
async def adventure_endpoint(user_id: int, action: str = "start"):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT nickname, class, str, dex, int, hp, max_hp, weapon, armor, combat_state
        FROM characters WHERE user_id = ?
    """, (user_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Персонаж не найден")

    player_data = {
        "nickname": row[0],
        "class": row[1], "str": row[2], "dex": row[3], "int": row[4],
        "hp": row[5], "max_hp": row[6], "weapon": row[7], "armor": row[8]
    }
    combat_state = json.loads(row[9] or "{}")

    if action == "start":
        enemies = start_combat(3)
        new_state = {"active": True, "enemies": enemies}
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE characters SET combat_state = ? WHERE user_id = ?", (json.dumps(new_state), user_id))
        conn.commit()
        conn.close()

        facts = {
            "player_name": player_data["nickname"],
            "player_class": player_data["class"],
            "event_summary": "Начало боя",
            "action": "вступил в схватку",
            "remaining_enemies": 3,
            "combat_continues": True
        }
        # Используем ИИ для генерации повествования
        narrative = await narrate_with_deepseek(facts)
        return {"narrative": narrative}

    else:
        if not combat_state.get("active"):
            return {"narrative": "Нет активного боя."}

        prev_hp = player_data["hp"] # Сохраняем HP до боя

        result = process_combat_round(player_data, action, combat_state["enemies"])
        if "error" in result:
            return {"narrative": result["error"]}

        apply_res = apply_results(user_id, result)
        if apply_res.get("error"):
            return {"narrative": apply_res["error"]}

        if not apply_res["alive"]:
            facts = {
                "player_name": player_data["nickname"],
                "player_class": player_data["class"],
                "defeat": True
            }
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("UPDATE characters SET combat_state = '{}' WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            narrative = await narrate_with_deepseek(facts)
            return {"narrative": narrative}

        alive_enemies = [e for e in combat_state["enemies"] if e["hp"] > 0]

        # --- ФОРМИРОВАНИЕ ФАКТОВ ДЛЯ НАРРАТОРА ---
        facts = {
            "player_name": player_data["nickname"],
            "player_class": player_data["class"],
            "event_summary": "Боевой раунд",
            "action": action,
            "enemy_killed": result["enemy_killed"],
            "enemy_type_killed": result["enemy_type_killed"],
            "player_damage_taken": result["player_damage_taken"],
            "prev_hp": prev_hp,
            "new_hp": apply_res["new_hp"],
            "max_hp": apply_res["max_hp"],
            "remaining_enemies": result["remaining_enemies"],
            "combat_continues": result["combat_continues"]
        }

        # --- СОХРАНЕНИЕ СОСТОЯНИЯ ---
        if result["combat_continues"]:
            new_state = {"active": True, "enemies": alive_enemies}
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("UPDATE characters SET combat_state = ? WHERE user_id = ?", (json.dumps(new_state), user_id))
            conn.commit()
            conn.close()
        else:
            facts["victory"] = True
            facts["combat_continues"] = False
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("UPDATE characters SET combat_state = '{}' WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()

        narrative = await narrate_with_deepseek(facts)
        return {"narrative": narrative}


# === HEALTH CHECK ===
@app.get("/health")
def health():
    init_db()
    return {"status": "ok"}


@app.on_event("startup")
def startup():
    init_db()


# === ЗАПУСК ===
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)