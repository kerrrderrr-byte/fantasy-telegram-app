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

// Эффект печатания текста
function typeText(element, text, callback) {
    element.classList.add('typing');
    element.textContent = ''; // очищаем

    let i = 0;
    const speed = 25; // ms per char

    function type() {
        if (i < text.length) {
            element.textContent += text.charAt(i);
            i++;
            requestAnimationFrame(() => setTimeout(type, speed));
            scrollToBottom();
        } else {
            element.classList.remove('typing');
            element.style.borderRight = 'none';
            if (callback) callback();
        }
    }

    type();
}

// Добавить сообщение в историю
function addMessage(sender, text) {
    const p = document.createElement('p');
    p.innerHTML = `<strong>${sender}:</strong> ${text}`;
    storyEl.appendChild(p);
    scrollToBottom();
}

// Отправка действия
async function sendAction(action = "") {
    try {
        loadingEl.textContent = "🧙‍♂️ Повествователь думает...";
        loadingEl.style.display = "block";
        sendBtn.disabled = true;

        const response = await fetch("/api/step", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                initData: WebApp.initData || "",
                action: action
            })
        });

        const data = await response.json();

        if (data.ok) {
            // Очищаем поле ввода СРАЗУ
            inputEl.value = "";

            // Добавляем действие игрока
            if (action) {
                addMessage("Ты", action);
            } else {
                storyEl.innerHTML = ''; // чистим при старте
            }

            // Анимация печатания ответа
            const p = document.createElement('p');
            p.innerHTML = "<strong>Повествователь:</strong> ";
            const span = document.createElement('span');
            p.appendChild(span);
            storyEl.appendChild(p);
            scrollToBottom();

            typeText(span, data.response, () => {
                loadingEl.style.display = "none";
                sendBtn.disabled = false;
                inputEl.focus();
            });

        } else {
            throw new Error(data.error || "Неизвестная ошибка");
        }
    } catch (err) {
        console.error("Ошибка:", err);
        loadingEl.textContent = `❌ ${err.message}`;
        setTimeout(() => loadingEl.style.display = "none", 3000);
        sendBtn.disabled = false;
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