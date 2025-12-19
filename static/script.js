// static/script.js
let currentView = 'menu';
let storyHistory = [];

const WebApp = window.Telegram.WebApp;
WebApp.ready();
WebApp.expand();
WebApp.setBackgroundColor("#0d0b16");

// DOM элементы
const menuView = document.getElementById('menuView');
const adventureView = document.getElementById('adventureView');
const storyEl = document.getElementById('story');
const inputEl = document.getElementById('actionInput');
const sendBtn = document.getElementById('sendBtn');
const backBtn = document.getElementById('backBtn');
const startBtn = document.getElementById('startBtn');
const loadingEl = document.getElementById('loading');


function typeTextWithWrap(container, text, onDone) {
    container.innerHTML = ''; // очищаем контейнер
    let i = 0;
    const speed = 25; // ms per char

    // Создаём span для "курсора"
    const cursor = document.createElement('span');
    cursor.textContent = '|';
    cursor.style.color = '#c05bff';
    cursor.style.marginLeft = '2px';
    cursor.style.animation = 'blink 1s infinite';
    container.appendChild(cursor);

    function type() {
        if (i < text.length) {
            // Вставляем символ и ПЕРЕСЧИТЫВАЕМ переносы автоматически
            const char = text.charAt(i);
            const textNode = document.createTextNode(char);
            container.insertBefore(textNode, cursor);
            i++;

            // Прокручиваем плавно вниз КАЖДЫЙ РАЗ
            requestAnimationFrame(() => {
                storyEl.scrollTo({
                    top: storyEl.scrollHeight,
                    behavior: 'smooth'
                });
            });

            setTimeout(type, speed);
        } else {
            // Убираем курсор
            container.removeChild(cursor);
            if (onDone) onDone();
        }
    }

    type();
}


// Переключение вида
function showView(view) {
    menuView.style.display = view === 'menu' ? 'flex' : 'none';
    adventureView.style.display = view === 'adventure' ? 'flex' : 'none';
    currentView = view;
}

// Автоскролл вниз
function scrollToBottom(smooth = false) {
    storyEl.scrollTo({
        top: storyEl.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto'
    });
}





// Отправка действия
async function sendAction(action) {
    if (!action.trim()) return;

    // 🔹 ШАГ 1: сразу добавляем сообщение игрока в чат
    const playerMsg = document.createElement('p');
    playerMsg.innerHTML = `<strong>Ты:</strong> ${action}`;
    storyEl.appendChild(playerMsg);
    inputEl.value = ''; // 🔹 сразу очищаем поле
    scrollToBottom(true); // плавная прокрутка

    // 🔹 ШАГ 2: показываем "печатает повествователь..."
    const aiMsg = document.createElement('p');
    aiMsg.innerHTML = `<strong>Повествователь:</strong> <span id="ai-typing"></span>`;
    storyEl.appendChild(aiMsg);
    const typingSpan = aiMsg.querySelector('#ai-typing');
    typingSpan.textContent = '';
    scrollToBottom(true);

    try {
        const response = await fetch("/api/step", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ initData: WebApp.initData, action })
        });

        const data = await response.json();

        if (data.ok) {
            // 🔹 ШАГ 3: заменяем "печатает..." на реальный типинг с переносом
            typeTextWithWrap(typingSpan, data.response, () => {
                // Готово
            });
        } else {
            typingSpan.textContent = `❌ Ошибка: ${data.error}`;
        }
    } catch (err) {
        typingSpan.textContent = `💥 ${err.message}`;
    }
}

// Обработчики
startBtn.addEventListener("click", () => {
    showView('adventure');
    sendAction(""); // стартовое описание
});

backBtn.addEventListener("click", () => {
    showView('menu');
});

sendBtn.addEventListener("click", () => {
    const action = inputEl.value.trim();
    if (action) {
        sendAction(action);
    }
});

inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendBtn.click();
    }
});

// Старт
if (!WebApp.initData) {
    document.body.innerHTML = `<div style="padding:40px;text-align:center;color:#ff6b6b">⚠️ Только в Telegram!</div>`;
} else {
    showView('menu');
}