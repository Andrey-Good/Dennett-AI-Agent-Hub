# Core SDK - Плагины и Runtime

Полная реализация SDK для плагинов в Dennett AI Core с поддержкой двухрежимного исполнения (core/uv/auto).

## Структура

```text
etc/core_sdk/
├── __init__.py              # Main SDK exports
├── enums.py                 # PluginKind, RunStatus
├── models.py                # ErrorInfo, NodeResult, etc.
├── context.py               # BaseContext, NodeContext, TriggerContext
├── plugins/
│   ├── base.py              # BasePlugin (meta, deps, permissions)
│   ├── node.py              # BaseNode (для нод)
│   ├── trigger.py           # BaseTrigger (для триггеров)
│   └── registry.py          # PluginRegistry
├── runtime/
│   ├── ast_validator.py     # AST валидация
│   ├── static_analyzer.py   # Анализ без импорта
│   ├── compatibility.py     # Проверка совместимости deps
│   ├── runtime_resolver.py  # Выбор режима core/uv/auto
│   └── env_manager.py       # Управление uv-окружениями
├── worker_wrapper.py        # IPC worker (NDJSON)
└── BUNDLED_MANIFEST.json    # Bundled libs

etc/plugins/
├── math_sum_node/plugin.py     # Пример ноды
└── time_tick_trigger/plugin.py # Пример триггера
