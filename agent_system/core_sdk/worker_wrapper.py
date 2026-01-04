#!/usr/bin/env python3
"""
Worker wrapper - запускается в uv-окружении плагина.
Читает NDJSON из stdin, исполняет плагины, пишет результаты в stdout (NDJSON).
"""
import os
import sys
import json
import logging
import traceback
import importlib.util
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("worker_wrapper")


def write_response(response: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


def load_plugin_class(plugin_path: str):
    path = Path(plugin_path)
    if not path.exists():
        raise FileNotFoundError(f"Plugin file not found: {plugin_path}")

    spec = importlib.util.spec_from_file_location("plugin_module", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {plugin_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["plugin_module"] = module
    spec.loader.exec_module(module)

    for attr_name in ("PLUGIN_CLASS", "NODE_CLASS", "TRIGGER_CLASS"):
        if hasattr(module, attr_name):
            return getattr(module, attr_name)

    raise ValueError("No PLUGIN_CLASS/NODE_CLASS/TRIGGER_CLASS found")


def handle_describe(plugin_path: str) -> None:
    try:
        plugin_cls = load_plugin_class(plugin_path)
        spec = plugin_cls.get_spec()
        write_response({"type": "describe_result", "plugin_id": spec["meta"]["id"], "spec": spec})
    except Exception as exc:
        logger.exception("Error in describe")
        write_response(
            {
                "type": "error",
                "code": "DESCRIBE_ERROR",
                "message": str(exc),
                "trace": traceback.format_exc(),
            }
        )


def handle_execute(plugin_path: str, inputs: Dict, config: Optional[Dict] = None) -> None:
    try:
        from core_sdk.context import NodeContext
        from core_sdk.plugins.node import BaseNode

        plugin_cls = load_plugin_class(plugin_path)
        if not issubclass(plugin_cls, BaseNode):
            raise TypeError("Plugin is not a BaseNode")

        ctx = NodeContext(
            run_id="worker-exec",
            plugin_id=plugin_cls.PLUGIN_ID,
            logger=logger,
            debug=True,
        )
        result = plugin_cls.execute(ctx, inputs, config)

        response = {
            "type": "result",
            "plugin_id": plugin_cls.PLUGIN_ID,
            "result": {
                "status": result.status.value,
                "output": result.output,
                "error": {
                    "code": result.error.code,
                    "message": result.error.message,
                    "traceback": result.error.traceback,
                }
                if result.error
                else None,
            },
        }
        write_response(response)
    except Exception as exc:
        logger.exception("Error in execute")
        write_response(
            {
                "type": "error",
                "code": "EXECUTE_ERROR",
                "message": str(exc),
                "trace": traceback.format_exc(),
            }
        )


def main() -> None:
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                cmd = json.loads(line)
            except json.JSONDecodeError as exc:
                write_response({"type": "error", "code": "INVALID_JSON", "message": str(exc)})
                continue

            cmd_type = cmd.get("type")
            if cmd_type == "describe":
                handle_describe(cmd["plugin_path"])
            elif cmd_type == "execute":
                handle_execute(cmd["plugin_path"], cmd.get("inputs", {}), cmd.get("config"))

            else:
                write_response(
                    {
                        "type": "error",
                        "code": "UNKNOWN_COMMAND",
                        "message": f"Unknown command: {cmd_type}",
                    }
                )

    except KeyboardInterrupt:
        logger.info("Worker interrupted")
        sys.exit(0)
    except Exception as exc:
        logger.exception("Unexpected error")
        write_response(
            {
                "type": "error",
                "code": "WORKER_FATAL",
                "message": str(exc),
                "trace": traceback.format_exc(),
            }
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
