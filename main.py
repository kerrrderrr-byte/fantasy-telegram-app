# main.py
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from dotenv import load_dotenv
from utils import validate_init_data
from storyteller import get_deepseek_response

load_dotenv()

app = FastAPI(title="Fantasy Adventure Mini App")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Главная страница (меню)
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

# Эндпоинт для хода приключения
@app.post("/api/step")
async def adventure_step(request: Request):
    try:
        data = await request.json()
        init_data = data.get("initData", "")
        user_action = data.get("action", "").strip()

        # 🔐 Валидация
        user_info = validate_init_data(init_data)
        user_id = user_info.get("user_id", "anon")

        # Формируем контекст: только последнее сообщение (можно расширить до истории)
        messages = []
        if user_action:
            messages.append({"role": "user", "content": user_action})
        else:
            messages.append({"role": "user", "content": "Начни приключение"})

        # 🧙‍♂️ Получаем ответ от DeepSeek
        ai_response = await get_deepseek_response(messages)

        return JSONResponse({
            "ok": True,
            "user_id": user_id,
            "response": ai_response
        })

    except Exception as e:
        return JSONResponse({
            "ok": False,
            "error": str(e)
        }, status_code=400)

# Health-check
@app.get("/health")
async def health():
    return {"status": "ok", "deepseek_configured": bool(os.getenv("DEEPSEEK_API_KEY"))}