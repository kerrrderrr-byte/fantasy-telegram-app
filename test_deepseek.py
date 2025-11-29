import httpx
import os
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    print("❌ DEEPSEEK_API_KEY не найден в .env")
    exit()

async def test_deepseek():
    print("📡 Отправляем тестовый запрос в DeepSeek...")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "user", "content": "Привет! Скажи коротко: ты жив?"}
                ],
                "temperature": 0.7
            },
            timeout=30.0
        )

    if response.status_code != 200:
        print(f"❌ Ошибка: {response.status_code}")
        print(response.text)
        return

    try:
        result = response.json()
        message = result["choices"][0]["message"]["content"]
        print(f"✅ DeepSeek ответил: {message}")
    except Exception as e:
        print(f"❌ Ошибка разбора JSON: {e}")
        print(response.text)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_deepseek())