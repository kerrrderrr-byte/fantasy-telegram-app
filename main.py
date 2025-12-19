# main.py
import os
import time
import hashlib
import hmac
from urllib.parse import unquote
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Fantasy Adventure Mini App",
    description="Ваше приключение в мире, управляемом DeepSeek"
)

# Подключаем папку static как корень — чтобы index.html был на /
app.mount("/static", StaticFiles(directory="static"), name="static")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN не задан в .env")

# 🎯 Главная страница — отдаём index.html
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

# 🔐 Валидация initData (обязательно для безопасности!)
def validate_telegram_data(init_data: str) -> dict:
    """
    Проверяет подлинность initData от Telegram WebApp.
    Возвращает распарсенные данные, если валидно.
    """
    try:
        # Разбираем initData в dict
        params = {}
        for part in init_data.split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                params[key] = unquote(value)

        # Проверяем, есть ли hash и auth_date
        if "hash" not in params:
            raise HTTPException(status_code=400, detail="hash missing")
        if "auth_date" not in params:
            raise HTTPException(status_code=400, detail="auth_date missing")

        # Проверяем "устаревание" (допустимо ±1 день)
        auth_date = int(params["auth_date"])
        if abs(time.time() - auth_date) > 86400:
            raise HTTPException(status_code=403, detail="auth_date expired")

        # Формируем данные для подписи (все кроме hash, отсортировано)
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(params.items()) if k != "hash"
        )

        # Генерируем секретный ключ: HMAC-SHA256("WebAppData", bot_token)
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=BOT_TOKEN.encode(),
            digestmod=hashlib.sha256
        ).digest()

        # Считаем хеш
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        # Сравниваем
        if calculated_hash != params["hash"]:
            raise HTTPException(status_code=403, detail="invalid hash")

        return params
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"validation failed: {str(e)}")

# 🧠 Эндпоинт для получения ответа от ИИ (заглушка)
@app.post("/api/adventure")
async def adventure_step(request: Request):
    data = await request.json()
    init_data = data.get("initData")
    user_action = data.get("action", "").strip()

    # 🔐 Валидируем пользователя
    user_data = validate_telegram_data(init_data)
    user_id = user_data.get("user", "{}")
    # (в user — JSON-строка, можно распарсить: json.loads(user_data["user"]))

    # 🧙‍♂️ Генерируем ответ (заглушка → замените на DeepSeek)
    if not user_action:
        response_text = (
            "🧙‍♂️ *Добро пожаловать в «Мир Теней и Огня»!*\n\n"
            "Туман стелется над землёй. Перед тобой — три пути:\n"
            "🌲 В древний лес\n"
            "🕳 В пещеру предков\n"
            "🌉 К разрушенному мосту\n\n"
            "*Что ты выберешь?*"
        )
    else:
        response_text = (
            f"«{user_action}» — прошептал ветер.\n\n"
            "Из-за деревьев вышел *серый волк* с глазами, полными боли. "
            "Он не рычит — лишь смотрит. В зубах — обрывок карты...\n\n"
            "*Что сделаешь?*"
        )

    return JSONResponse({
        "ok": True,
        "message": response_text,
        "user_id": user_data.get("user_id", "unknown")
    })

# 🩺 Health-check
@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": int(time.time())}