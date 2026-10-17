"""
Optional dependencies (other plugins CustomsCommands can work with).

Each integration declares itself here, then reports its state when the plugin is enabled:
"active", "missing" (plugin not installed), "disabled" (turned off in config.json) or "error".
The editor lists the execution types of the active ones under "Dependencies".
"""

from ..API.types import ExecutionTypes
from ..Utils.lang import t
from ..Utils.security import InputError

STATES = ("active", "missing", "disabled", "error")
INTEGRATIONS: dict = {}


def declare(integration_id: str, title: str) -> None:
    INTEGRATIONS.setdefault(integration_id, {"title": title, "state": "missing", "detail": ""})


def set_state(integration_id: str, state: str, detail: str = "") -> None:
    if integration_id in INTEGRATIONS and state in STATES:
        INTEGRATIONS[integration_id]["state"] = state
        INTEGRATIONS[integration_id]["detail"] = detail


def state(integration_id: str) -> str:
    return INTEGRATIONS.get(integration_id, {}).get("state", "missing")


def is_active(integration_id: str) -> bool:
    return state(integration_id) == "active"


def title(group: str) -> str:
    """Display name of a group: the plugin's name, or the group as registered by a plugin."""
    return INTEGRATIONS.get(group, {}).get("title", group)


def require_active(integration_id: str) -> None:
    """Called by the executions of an integration: a clear message if it can't work."""
    if not is_active(integration_id):
        raise InputError(t("err.dependency_missing", plugin=title(integration_id)))


def types_of(group: str) -> list:
    return [n for n in ExecutionTypes.get_types() if ExecutionTypes.get_group(n) == group]


def active_groups() -> list:
    """Groups to show under Dependencies: active integrations and groups of other plugins."""
    groups = []
    for name in ExecutionTypes.get_types():
        group = ExecutionTypes.get_group(name)
        if not group or group in groups:
            continue
        if group in INTEGRATIONS and not is_active(group):
            continue
        groups.append(group)
    return groups


def detect(server, plugin_names=(), command_names=()) -> bool:
    """True if one of the plugins is loaded, or one of their commands is registered."""
    manager = getattr(server, "plugin_manager", None)
    for name in plugin_names:
        try:
            if manager is not None and manager.get_plugin(name) is not None:
                return True
        except Exception:
            pass
    for name in command_names:
        try:
            if server.get_plugin_command(name) is not None:
                return True
        except Exception:
            pass
    return False
