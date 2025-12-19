# main.py
import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Импорты компонентов мира — ОБЯЗАТЕЛЬНО в таком порядке
from world import get_region, Region, get_quest_by_id
from storyteller import get_ai_response, PlayerState
from state_manager import get_player_state, save_player_state

# Настройка
load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Fantasy Adventure Mini App")
app.mount("/static", StaticFiles(directory="static"), name="static")

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def _handle_purchase(state: PlayerState, action: str):
    """Обрабатывает покупки в Ебеньграде (триггеры квестов)"""
    low = action.lower()
    if "бутер" in low and ("куп" in low or "заказ" in low or "возьм" in low):
        state.inventory["Бутерброд"] = state.inventory.get("Бутерброд", 0) + 1
        return True
    if "кофе" in low and ("куп" in low or "заказ" in low or "возьм" in low):
        state.inventory["Кофе"] = state.inventory.get("Кофе", 0) + 1
        return True
    return False

def _check_quest_triggers(state: PlayerState):
    """Проверяет, активировать ли квест 'Убить Рыжую ведьму'"""
    if "kill_ryzhaya_witch" in state.active_quests:
        return  # уже активен

    # Триггер: 2 бутера + 1 кофе
    if state.inventory.get("Бутерброд", 0) >= 2 and state.inventory.get("Кофе", 0) >= 1:
        state.active_quests.append("kill_ryzhaya_witch")
        logging.info(f"Квест активирован для игрока в {state.current_region}")

# === ЭНДПОИНТЫ ===

@app.get("/", response_class=HTMLResponse)
async def home():
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>❌ static/index.html не найден</h1><p>Проверьте структуру проекта в Render → Files</p>"

@app.get("/app")
async def redirect_app():
    return RedirectResponse(url="/", status_code=302)

@app.get("/favicon.ico")
async def favicon():
    return Response(
        content=b'\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        media_type="image/x-icon"
    )

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "deepseek_configured": bool(os.getenv("DEEPSEEK_API_KEY")),
        "regions_loaded": len([r for r in [get_region("Ебеньград"), get_region("Логово Рыжей")] if r])
    }

@app.post("/api/step")
async def adventure_step(request: Request):
    try:
        data = await request.json()
        init_data = data.get("initData", "")
        user_action = data.get("action", "").strip()

        # 🔐 Валидация (минимальная — для Mini App можно и без неё на старте)
        user_id = "test_user"  # ← для демо. В продакшене — из initData
        if not user_action:
            raise HTTPException(status_code=400, detail="action required")

        # 🧩 Получаем состояние игрока
        state = get_player_state(user_id)

        # 🛒 Обработка покупок (только в Ебеньграде)
        if state.current_region == "Ебеньград":
            _handle_purchase(state, user_action)
            _check_quest_triggers(state)

        events = []  # ← новые события для ИИ

        if state.current_region == "Ебеньград":
            if _handle_purchase(state, user_action):
                # Определим, что именно куплено
                if "бутер" in user_action.lower():
                    events.append("Игрок купил бутерброд у Сани в таверне.")
                if "кофе" in user_action.lower():
                    events.append("Игрок заказал кофе у Сани.")
            _check_quest_triggers(state)

        # Передайте события в get_ai_response
        ai_response = await get_ai_response(state, user_action, events=events)

        # 🧭 Простейшая навигация (для демо)
        if "логово" in user_action.lower() and "едь" in user_action.lower():
            state.current_region = "Логово Рыжей"
        elif "город" in user_action.lower() or "назад" in user_action.lower():
            state.current_region = "Ебеньград"

        # 💾 Сохраняем
        save_player_state(user_id, state)

        # 🧠 Генерация ответа ИИ
        ai_response = await get_ai_response(state, user_action)

        return JSONResponse({
            "ok": True,
            "user_id": user_id,
            "response": ai_response,
            "debug": {
                "region": state.current_region,
                "inventory": state.inventory,
                "quests": state.active_quests
            }
        })

    except Exception as e:
        logging.error(f"Ошибка в /api/step: {e}", exc_info=True)
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)