// script.js
(async () => {
    const WebApp = window.Telegram.WebApp;
    WebApp.ready();
    WebApp.expand();
    WebApp.setHeaderColor("#0b0912");
    WebApp.setBackgroundColor("#0b0912");

    const storyEl = document.getElementById('story');
    const inputEl = document.getElementById('actionInput');
    const sendBtn = document.getElementById('sendBtn');
    const loadingEl = document.getElementById('loading');

    // 🚀 Получаем initData (подписанные данные пользователя)
    const initData = WebApp.initData || "";

    // 🧪 Проверка: если запущено не в Telegram
    if (!initData && !WebApp.isVersionAtLeast("6.0")) {
        storyEl.innerHTML = `
            <p>⚠️ Это приложение работает только внутри Telegram.</p>
            <p>Откройте его через меню бота или по ссылке из чата.</p>
        `;
        sendBtn.disabled = true;
        return;
    }

    // 💬 Функция отправки действия
    async function sendAction(action = "") {
        try {
            loadingEl.style.display = "block";
            sendBtn.disabled = true;

            const response = await fetch("/api/adventure", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ initData, action })
            });

            const data = await response.json();

            if (data.ok) {
                // Добавляем в историю
                storyEl.innerHTML += `
                    <p><strong>Ты:</strong> ${action || "начал приключение"}</p>
                    <p><strong>Повествователь:</strong> ${data.message}</p>
                    <hr style="border:0;border-top:1px solid #2a1e4a;margin:20px 0;">
                `;
                // Прокрутка вниз
                storyEl.scrollTop = storyEl.scrollHeight;
                inputEl.value = "";
            } else {
                throw new Error(data.detail || "Ошибка");
            }
        } catch (err) {
            console.error("Ошибка:", err);
            storyEl.innerHTML += `<p style="color:#ff6b6b">❌ ${err.message}</p>`;
        } finally {
            loadingEl.style.display = "none";
            sendBtn.disabled = false;
        }
    }

    // 🎬 Старт при загрузке
    sendAction(""); // пустое действие → стартовое описание

    // 🔘 Кнопка
    sendBtn.addEventListener("click", () => {
        const action = inputEl.value.trim();
        if (action) {
            sendAction(action);
        } else {
            inputEl.focus();
        }
    });

    // ↵ Enter
    inputEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendBtn.click();
        }
    });
})();