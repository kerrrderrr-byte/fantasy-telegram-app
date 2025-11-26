from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os

app = FastAPI()

# Простая HTML-страница для Telegram Mini App
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
                justify-content: center;
                height: 100vh;
                margin: 0;
                text-align: center;
            }
            .container {
                padding: 20px;
            }
            h1 {
                color: #8a6bff;
            }
            .user-info {
                background: #1a1726;
                padding: 15px;
                border-radius: 12px;
                margin-top: 20px;
                width: 90%;
                max-width: 300px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧙 Fantasy Quest</h1>
            <p>Добро пожаловать в фэнтези-мир!</p>
            <div class="user-info" id="userInfo">
                Загрузка...
            </div>
        </div>

        <script>
            // Инициализация Telegram WebApp
            if (window.Telegram && Telegram.WebApp) {
                Telegram.WebApp.ready();
                Telegram.WebApp.expand();

                const user = Telegram.WebApp.initDataUnsafe?.user;
                const userInfoDiv = document.getElementById('userInfo');

                if (user) {
                    userInfoDiv.innerHTML = `
                        <strong>ID:</strong> ${user.id}<br>
                        <strong>Имя:</strong> ${user.first_name || ''} ${user.last_name || ''}<br>
                        <strong>Username:</strong> ${user.username || '—'}
                    `;
                } else {
                    userInfoDiv.innerHTML = "❌ Не удалось загрузить данные пользователя.";
                }
            } else {
                document.getElementById('userInfo').innerHTML = "⚠️ Запущено вне Telegram!";
            }
        </script>
    </body>
    </html>
    """

# Эндпоинт для проверки работоспособности
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is ready for Telegram Mini App!"}

# Главная страница (опционально)
@app.get("/")
def home():
    return {"message": "Fantasy Quest Backend"}

# Запуск (для локальной разработки)
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)