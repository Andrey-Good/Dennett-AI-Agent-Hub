# Dennett - AI Model Manager

Приложение для управления AI моделями с красивым Tauri + React интерфейсом.

**🎯 Возможности:**
- Поиск моделей на HuggingFace в реальном времени
- Загрузка и управление моделями локально
- Live поиск с умной фильтрацией
- Быстрый и красивый UI

**📸 Screenshots:**
[Добавь сюда скриншот приложения]

## ⚡ Быстрый старт (5 минут)

### Требования:
- Python 3.10+ 
- Node.js 18+
- Git

### 1️⃣ Клонировать репозиторий

\`\`\`bash
git clone https://github.com/yourusername/dennett.git
cd dennett
\`\`\`

### 2️⃣ Запустить Backend

\`\`\`bash
cd backend

# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows)
venv\Scripts\activate
# Или (macOS/Linux)
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Скопировать конфиг
copy .env.example .env

# Запустить сервер
python -m uvicorn model_manager.app.main:app --host 0.0.0.0 --port 5208 --reload
\`\`\`

**Сервер запустится на:** http://localhost:5208
**Swagger документация:** http://localhost:5208/docs

### 3️⃣ Запустить Frontend

В **новом терминале**:

\`\`\`bash
cd frontend

# Установить зависимости
npm install

# Запустить приложение
npm run tauri dev
\`\`\`

**Приложение откроется на:** http://localhost:1420

## 📁 Структура проекта

\`\`\`
dennett/
├── backend/
│   ├── model_manager/
│   │   ├── app/
│   │   ├── core/
│   │   │   ├── config/
│   │   │   ├── models/
│   │   │   └── services/
│   │   └── routers/
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── stores/
│   │   ├── api/
│   │   └── types/
│   ├── src-tauri/
│   ├── package.json
│   └── .env.example
│
├── .gitignore
└── README.md
\`\`\`

## 💾 Хранилище данных

- **Код:** Текущая папка проекта
- **Модели & агенты:** \`C:\Users\{YourUsername}\AppData\Roaming\Dennett\\` (Windows)
- **База данных:** \`AppData\Roaming\Dennett\storage.db\`

Данные автоматически создадутся при первом запуске.

## 🚀 Команды

### Backend
\`\`\`bash
# Development
python -m uvicorn model_manager.app.main:app --reload

# Tests
pytest

# Swagger UI
# Открыть http://localhost:5208/docs
\`\`\`

### Frontend
\`\`\`bash
# Development
npm run tauri dev

# Build для Windows
npm run tauri build

# Build для всех платформ
npm run tauri build -- --target all
\`\`\`

## 🛠️ Технологический стек

### Backend
- **FastAPI** - RESTful API
- **Pydantic** - Валидация данных
- **platformdirs** - Кроссплатформенные пути
- **HuggingFace Hub** - Поиск моделей

### Frontend
- **React 19** - UI фреймворк
- **TypeScript** - Типизация
- **Zustand** - State management
- **Tauri 2** - Десктоп приложение
- **Tailwind CSS** - Стили

## 📝 API Endpoints

\`\`\`
GET  /hub/search?query=llama&limit=20     - Поиск моделей
GET  /hub/model/{author}/{name}            - Детали модели
GET  /local/models                         - Список локальных моделей
POST /local/download                       - Скачать модель
GET  /local/storage/stats                  - Статистика хранилища
GET  /health                               - Health check
\`\`\`

