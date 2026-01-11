# Dennett — AI Agent Hub (Tauri 2 + React + FastAPI)

Этот репозиторий состоит из двух частей:

- **backend**: `apps/ai_core` — FastAPI (порт **8000**)
- **frontend**: `frontend` — React (Vite, порт **1420**) + Tauri 2

Если у тебя раньше были ошибки **pydantic-core / PyO3** при `pip install`, смотри раздел **"Важно про версию Python"**.

---

## Важно про версию Python

Backend использует `pydantic` (через `pydantic-core`), который **не собирается на Python 3.14** (ошибка вида: *"Python 3.14 is newer than PyO3 max supported 3.13"*).

✅ Используй **Python 3.12.x** (или 3.11 / 3.13). Для Windows это самый беспроблемный вариант.

Если у тебя уже создано `venv` на Python 3.14 — удали его и создай заново под Python 3.12.

---

## Быстрый старт (Windows)

### 1) Backend (FastAPI)

Открой PowerShell в корне проекта.

```powershell
cd apps\ai_core

# создать venv
py -3.12 -m venv venv

# активировать venv
venv\Scripts\Activate.ps1

# обновить pip
python -m pip install --upgrade pip

# установить зависимости
pip install -r requirements.txt

# запустить API
python -m uvicorn apps.ai_core.ai_core.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir apps\ai_core\ai_core
```

Проверка: открой в браузере `http://127.0.0.1:8000/docs` — должна открыться Swagger UI.

### 2) Frontend (React + Tauri)

Открой **второй** терминал в корне проекта:

```powershell
cd frontend

# установить npm зависимости
npm install

# проверить, что CLI именно локальный
npx tauri -V

# запуск Tauri (поднимется Vite на 1420 и запустится окно)
npm run tauri dev
```

---

## Структура

- `frontend/src/App.tsx` — основной shell приложения (икон-бар слева, панель моделей/агентов, центральные страницы)
- `frontend/src/components/app/*` — страницы и компоненты UI
- `frontend/src/components/ui/*` — **shadcn/ui** компоненты
- `apps/ai_core/ai_core` — backend логика

---

## Если UI всё ещё пустой

1) Запусти Vite отдельно и открой `http://localhost:1420/` в браузере:

```powershell
cd frontend
npm run dev
```

Если в браузере **есть UI**, а в Tauri пусто — почти всегда проблема в `tauri.conf.json` или в несовпадении версий.

2) Версии должны совпадать по ветке **2.x**:

- `npx tauri -V` показывает **2.9.0**
- `@tauri-apps/api` в `frontend/package.json` тоже **2.9.0**
- `tauri` и `tauri-build` в `frontend/src-tauri/Cargo.toml` должны быть из доступных на crates.io версий (в этом проекте выставлены совместимые значения)

3) Открой DevTools в окне Tauri (обычно Ctrl+Shift+I) и посмотри ошибки в Console.
