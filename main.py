from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import sqlite3
import os

# Инициализация FastAPI
app = FastAPI()

# Путь к БД (в Render будет в ephemeral storage, но для MVP сойдёт)
DB_PATH = "characters.db"


# Создаём БД при старте
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            class TEXT,
            level INTEGER DEFAULT 1,
            hp INTEGER DEFAULT 100,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# Модель для создания персонажа
class CharacterCreate(BaseModel):
    user_id: int
    name: str
    class_name: str


# Главная Mini App страница
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
                        statusDiv.innerHTML = `✅ Герой создан!<br>Класс: <strong>${className}</strong>`;
                        // Отключим кнопки
                        document.querySelectorAll('.class-btn').forEach(btn => {
                            btn.disabled = true;
                            btn.style.opacity = '0.6';
                        });
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


# Эндпоинт создания персонажа
@app.post("/api/create_character")
async def create_character(data: CharacterCreate):
    allowed_classes = {"Маг", "Воин", "Ассасин", "Лучник", "Рыцарь"}
    if data.class_name not in allowed_classes:
        raise HTTPException(status_code=400, detail="Неверный класс")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO characters (user_id, name, class) VALUES (?, ?, ?)",
            (data.user_id, data.name, data.class_name)
        )
        conn.commit()
        return {"status": "success", "class": data.class_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка БД")
    finally:
        conn.close()


# Эндпоинт для проверки
@app.get("/health")
def health():
    init_db()  # Инициализируем БД при первом запросе
    return {"status": "ok", "message": "Fantasy Quest is ready!"}


# Инициализация БД при запуске
@app.on_event("startup")
def startup():
    init_db()


# Для локального запуска
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)