from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import sqlite3
import os

app = FastAPI()

DB_PATH = "characters.db"

# Базовые параметры по классам
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
class CharacterCreate(BaseModel):
    user_id: int
    name: str
    class_name: str


class StatUpdate(BaseModel):
    user_id: int
    stat: str  # "str", "dex", "int"


# Главная страница — выбор класса
@app.get("/app", response_class=HTMLResponse)
def mini_app():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fantasy Quest</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #0f0c1a;
                color: white;
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 20px;
                margin: 0;
            }
            .container {
                width: 100%;
                max-width: 500px;
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
            }
            .class-btn:hover {
                background: #8a6bff;
                transform: scale(1.03);
            }
            .status {
                margin-top: 20px;
                padding: 12px;
                background: #1a1726;
                border-radius: 8px;
                text-align: center;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧙 Fantasy Quest</h1>
            <p>Выбери класс своего героя:</p>

            <div class="class-grid" id="classButtons">
                <button class="class-btn" onclick="selectClass('Маг')">Маг</button>
                <button class="class-btn" onclick="selectClass('Воин')">Воин</button>
                <button class="class-btn" onclick="selectClass('Ассасин')">Ассасин</button>
                <button class="class-btn" onclick="selectClass('Лучник')">Лучник</button>
                <button class="class-btn" onclick="selectClass('Рыцарь')">Рыцарь</button>
            </div>

            <div class="status" id="status"></div>
        </div>

        <script>
            Telegram.WebApp.ready();
            Telegram.WebApp.expand();

            const user = Telegram.WebApp.initDataUnsafe?.user;
            if (!user) {
                document.getElementById('classButtons').innerHTML = '<p>❌ Запущено вне Telegram!</p>';
            }

            async function selectClass(className) {
                if (!user) return;

                const statusDiv = document.getElementById('status');
                statusDiv.style.display = 'block';
                statusDiv.innerHTML = 'Создание персонажа...';

                try {
                    const response = await fetch('/api/create_character', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            user_id: user.id,
                            name: user.first_name || 'Герой',
                            class_name: className
                        })
                    });

                    const data = await response.json();

                    if (response.ok) {
                        // Перенаправляем на экран персонажа
                        window.location.href = '/app/character?user_id=' + user.id;
                    } else {
                        statusDiv.innerHTML = `❌ Ошибка: ${data.detail}`;
                    }
                } catch (err) {
                    statusDiv.innerHTML = '❌ Не удалось подключиться к серверу';
                }
            }
        </script>
    </body>
    </html>
    """


# Экран персонажа
@app.get("/app/character", response_class=HTMLResponse)
def character_screen():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Мой персонаж</title>
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
            .stat {
                background: #1a1726;
                padding: 15px;
                border-radius: 12px;
                margin: 12px 0;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .btn {
                background: #8a6bff;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                cursor: pointer;
            }
            .points {
                text-align: center;
                margin: 20px 0;
                font-size: 18px;
                color: gold;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ Мой персонаж</h1>
            <div class="points" id="points">Очки характеристик: 3</div>

            <div class="stat">
                <span>Сила</span>
                <div><span id="str-val">5</span> <button class="btn" onclick="addStat('str')" id="str-btn">+</button></div>
            </div>
            <div class="stat">
                <span>Ловкость</span>
                <div><span id="dex-val">8</span> <button class="btn" onclick="addStat('dex')" id="dex-btn">+</button></div>
            </div>
            <div class="stat">
                <span>Интеллект</span>
                <div><span id="int-val">18</span> <button class="btn" onclick="addStat('int')" id="int-btn">+</button></div>
            </div>
        </div>

        <script>
            Telegram.WebApp.ready();
            Telegram.WebApp.expand();

            const urlParams = new URLSearchParams(window.location.search);
            const userId = urlParams.get('user_id');
            let points = 3;

            // Загрузим данные персонажа
            async function loadCharacter() {
                try {
                    const res = await fetch(`/api/character/${userId}`);
                    const data = await res.json();
                    if (res.ok) {
                        document.getElementById('str-val').textContent = data.str;
                        document.getElementById('dex-val').textContent = data.dex;
                        document.getElementById('int-val').textContent = data.int;
                        points = data.stat_points;
                        updatePoints();
                        updateButtons();
                    }
                } catch (e) {
                    console.error(e);
                }
            }

            function updatePoints() {
                document.getElementById('points').textContent = `Очки характеристик: ${points}`;
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
                    const data = await res.json();
                    if (res.ok) {
                        points -= 1;
                        // Обновим значение на экране
                        const val = parseInt(document.getElementById(`${stat}-val`).textContent) + 1;
                        document.getElementById(`${stat}-val`).textContent = val;
                        updatePoints();
                        updateButtons();
                    }
                } catch (e) {
                    alert('Ошибка');
                }
            }

            loadCharacter();
        </script>
    </body>
    </html>
    """


# Создание персонажа
@app.post("/api/create_character")
async def create_character(data: CharacterCreate):
    if data.class_name not in CLASS_STATS:
        raise HTTPException(status_code=400, detail="Неверный класс")

    base = CLASS_STATS[data.class_name]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO characters 
            (user_id, name, class, str, dex, int, stat_points) 
            VALUES (?, ?, ?, ?, ?, ?, 3)
        """, (data.user_id, data.name, data.class_name, base["str"], base["dex"], base["int"]))
        conn.commit()
        return {"status": "success", "class": data.class_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка БД")
    finally:
        conn.close()


# Получение данных персонажа
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


# Добавление очка характеристики
@app.post("/api/add_stat")
async def add_stat(data: StatUpdate):
    if data.stat not in ["str", "dex", "int"]:
        raise HTTPException(status_code=400, detail="Неверная характеристика")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Проверим, есть ли очки
        cursor.execute("SELECT stat_points FROM characters WHERE user_id = ?", (data.user_id,))
        row = cursor.fetchone()
        if not row or row[0] <= 0:
            raise HTTPException(status_code=400, detail="Нет очков характеристик")

        # Увеличим характеристику и уменьшим очки
        cursor.execute(
            f"UPDATE characters SET {data.stat} = {data.stat} + 1, stat_points = stat_points - 1 WHERE user_id = ?",
            (data.user_id,))
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()


# Health check
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