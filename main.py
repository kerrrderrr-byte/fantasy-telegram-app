from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import sqlite3
import os
import re

app = FastAPI()

DB_PATH = "characters.db"

# Описания классов
CLASS_DESCRIPTIONS = {
    "Маг": "Владыка стихий и древних заклинаний. Наносит огромный магический урон, но хрупок в ближнем бою. Идеален для тех, кто любит стратегию и контроль.",
    "Воин": "Неудержимая сила и ярость. Высокое здоровье и урон в ближнем бою. Лучший выбор для лобовых столкновений.",
    "Ассасин": "Тень, что поражает с тыла. Высокий критический урон и уклонение. Идеален для быстрых, смертоносных атак.",
    "Лучник": "Мастер дистанционного боя. Наносит урон издалека, имеет высокую точность и подвижность. Отличен для тактических игроков.",
    "Рыцарь": "Щит и меч королевства. Высокая защита и выносливость. Может отвлекать врагов и защищать союзников.",
}

# Базовые параметры
CLASS_STATS = {
    "Маг": {"str": 5, "dex": 8, "int": 18},
    "Воин": {"str": 18, "dex": 8, "int": 5},
    "Ассасин": {"str": 12, "dex": 18, "int": 8},
    "Лучник": {"str": 10, "dex": 16, "int": 10},
    "Рыцарь": {"str": 16, "dex": 10, "int": 8},
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            user_id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            name TEXT,
            class TEXT,
            level INTEGER DEFAULT 1,
            str INTEGER DEFAULT 0,
            dex INTEGER DEFAULT 0,
            int INTEGER DEFAULT 0,
            stat_points INTEGER DEFAULT 3,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# Модели
class UsernameCreate(BaseModel):
    user_id: int
    username: str


class CharacterCreate(BaseModel):
    user_id: int
    class_name: str


# === ЭКРАН 1: ВВОД НИКА ===
@app.get("/app", response_class=HTMLResponse)
def screen_username():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ввести ник</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #0f0c1a;
                color: white;
                padding: 20px;
                margin: 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
            }
            .container {
                width: 100%;
                max-width: 350px;
                text-align: center;
            }
            h1 {
                color: #8a6bff;
            }
            input {
                width: 100%;
                padding: 12px;
                border-radius: 8px;
                border: 1px solid #8a6bff;
                background: #1a1726;
                color: white;
                margin: 20px 0;
                box-sizing: border-box;
            }
            .btn {
                background: #8a6bff;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 16px;
                cursor: pointer;
                width: 100%;
            }
            .error {
                color: #ff6b6b;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧙 Введи ник</h1>
            <p>Выбери уникальное имя героя (3–16 символов, буквы и цифры)</p>
            <input type="text" id="username" placeholder="Например: DarkMage" maxlength="16">
            <div class="error" id="error"></div>
            <button class="btn" onclick="submitUsername()">Далее</button>
        </div>

        <script>
            Telegram.WebApp.ready();
            Telegram.WebApp.expand();

            const user = Telegram.WebApp.initDataUnsafe?.user;
            if (!user) {
                document.body.innerHTML = '<div style="text-align:center;padding:50px;color:red;">❌ Вне Telegram!</div>';
            }

            async function submitUsername() {
                const username = document.getElementById('username').value.trim();
                const errorDiv = document.getElementById('error');
                errorDiv.textContent = '';

                if (!username || username.length < 3) {
                    errorDiv.textContent = 'Ник должен быть от 3 символов';
                    return;
                }
                if (!/^[a-zA-Z0-9_]{3,16}$/.test(username)) {
                    errorDiv.textContent = 'Только буквы, цифры, _';
                    return;
                }

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
                } catch (e) {
                    errorDiv.textContent = 'Ошибка сети';
                }
            }
        </script>
    </body>
    </html>
    """


# === ЭКРАН 2: ВЫБОР КЛАССА ===
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
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #0f0c1a;
                color: white;
                padding: 20px;
                margin: 0;
            }
            .container {
                max-width: 500px;
                margin: 0 auto;
            }
            h1 {
                color: #8a6bff;
                text-align: center;
            }
            .class-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 12px;
                margin-top: 20px;
            }
            .class-btn {
                background: #1a1726;
                color: white;
                border: 2px solid #8a6bff;
                border-radius: 12px;
                padding: 16px;
                font-size: 16px;
                cursor: pointer;
                transition: all 0.2s;
                text-align: center;
            }
            .class-btn:hover {
                background: #8a6bff;
                transform: scale(1.03);
            }
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
            Telegram.WebApp.ready();
            Telegram.WebApp.expand();
            const urlParams = new URLSearchParams(window.location.search);
            const userId = urlParams.get('user_id');

            function showClass(className) {
                window.location.href = '/app/class_info?class=' + encodeURIComponent(className) + '&user_id=' + userId;
            }
        </script>
    </body>
    </html>
    """


# === ЭКРАН 3: ОПИСАНИЕ КЛАССА ===
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
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #0f0c1a;
                color: white;
                padding: 20px;
                margin: 0;
            }
            .container {
                max-width: 500px;
                margin: 0 auto;
            }
            .back {
                color: #8a6bff;
                cursor: pointer;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            h1 {
                color: #8a6bff;
                text-align: center;
            }
            .desc {
                background: #1a1726;
                padding: 20px;
                border-radius: 12px;
                margin: 20px 0;
                line-height: 1.5;
            }
            .confirm-btn {
                background: #8a6bff;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 14px;
                font-size: 18px;
                cursor: pointer;
                width: 100%;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="back" onclick="goBack()">
                <span>←</span> Назад к выбору
            </div>
            <h1 id="class-title">Загрузка...</h1>
            <div class="desc" id="class-desc">...</div>
            <button class="confirm-btn" onclick="confirmClass()">Выбрать этот класс</button>
        </div>

        <script>
            Telegram.WebApp.ready();
            Telegram.WebApp.expand();

            const urlParams = new URLSearchParams(window.location.search);
            const className = decodeURIComponent(urlParams.get('class'));
            const userId = urlParams.get('user_id');

            const descriptions = {
                "Маг": "Владыка стихий и древних заклинаний. Наносит огромный магический урон, но хрупок в ближнем бою. Идеален для тех, кто любит стратегию и контроль.",
                "Воин": "Неудержимая сила и ярость. Высокое здоровье и урон в ближнем бою. Лучший выбор для лобовых столкновений.",
                "Ассасин": "Тень, что поражает с тыла. Высокий критический урон и уклонение. Идеален для быстрых, смертоносных атак.",
                "Лучник": "Мастер дистанционного боя. Наносит урон издалека, имеет высокую точность и подвижность. Отличен для тактических игроков.",
                "Рыцарь": "Щит и меч королевства. Высокая защита и выносливость. Может отвлекать врагов и защищать союзников."
            };

            document.getElementById('class-title').textContent = className;
            document.getElementById('class-desc').textContent = descriptions[className] || 'Описание отсутствует';

            function goBack() {
                window.location.href = '/app/class_select?user_id=' + userId;
            }

            async function confirmClass() {
                try {
                    const res = await fetch('/api/create_character', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({user_id: userId, class_name: className})
                    });
                    if (res.ok) {
                        window.location.href = '/app/main_menu?user_id=' + userId;
                    } else {
                        alert('Ошибка создания персонажа');
                    }
                } catch (e) {
                    alert('Ошибка сети');
                }
            }
        </script>
    </body>
    </html>
    """


# === ЭКРАН 4: ГЛАВНОЕ МЕНЮ ===
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
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #0f0c1a;
                color: white;
                padding: 20px;
                margin: 0;
            }
            .container {
                max-width: 500px;
                margin: 0 auto;
            }
            h1 {
                color: #8a6bff;
                text-align: center;
            }
            .menu-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 16px;
                margin-top: 30px;
            }
            .menu-btn {
                background: #1a1726;
                color: white;
                border: 2px solid #8a6bff;
                border-radius: 12px;
                padding: 20px;
                font-size: 18px;
                cursor: pointer;
                transition: all 0.2s;
                text-align: center;
            }
            .menu-btn:hover {
                background: #8a6bff;
                transform: scale(1.03);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏰 Главное меню</h1>
            <div class="menu-grid">
                <div class="menu-btn" onclick="goTo('/app/adventure')">Приключение</div>
                <div class="menu-btn" onclick="goTo('/app/friends')">Друзья</div>
                <div class="menu-btn" onclick="goTo('/app/clans')">Кланы</div>
                <div class="menu-btn" onclick="goTo('/app/profile')">Профиль</div>
                <div class="menu-btn" onclick="goTo('/app/character')">Персонаж</div>
            </div>
        </div>

        <script>
            Telegram.WebApp.ready();
            Telegram.WebApp.expand();
            const urlParams = new URLSearchParams(window.location.search);
            const userId = urlParams.get('user_id');

            function goTo(path) {
                window.location.href = path + '?user_id=' + userId;
            }
        </script>
    </body>
    </html>
    """


# === API ENDPOINTS ===

# Проверка уникальности ника
@app.post("/api/check_username")
async def check_username(UsernameCreate):
    if not re.match(r"^[a-zA-Z0-9_]{3,16}$", data.username):
        raise HTTPException(status_code=400, detail="Неверный формат ника")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM characters WHERE username = ?", (data.username,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Такой ник уже занят")

    # Сохраняем временно (можно и без этого, но для MVP — ок)
    cursor.execute("""
        INSERT OR REPLACE INTO characters (user_id, username, name) 
        VALUES (?, ?, ?)
    """, (data.user_id, data.username, data.username))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# Создание персонажа (класс)
@app.post("/api/create_character")
async def create_character(CharacterCreate):
    if data.class_name not in CLASS_STATS:
        raise HTTPException(status_code=400, detail="Неверный класс")

    base = CLASS_STATS[data.class_name]
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE characters 
        SET class = ?, str = ?, dex = ?, int = ?, stat_points = 3
        WHERE user_id = ?
    """, (data.class_name, base["str"], base["dex"], base["int"], data.user_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# === СТАРЫЕ ЭНДПОИНТЫ (для совместимости) ===
@app.get("/api/character/{user_id}")
async def get_character(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT str, dex, int, stat_points FROM characters WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Персонаж не найден")
    return {
        "str": row[0],
        "dex": row[1],
        "int": row[2],
        "stat_points": row[3]
    }


@app.post("/api/add_stat")
async def add_stat(StatUpdate):
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
        (data.user_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# Health
@app.get("/health")
def health():
    init_db()
    return {"status": "ok"}


@app.on_event("startup")
def startup():
    init_db()


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)