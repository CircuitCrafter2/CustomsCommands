"""Built-in execution types, conditions and placeholders."""

import math
from datetime import datetime

from .types import ConditionTypes, ExecutionTypes, PlaceholderTypes
from ..Utils.render import render_template
from ..Utils.security import InputError, compare_values, parse_expression

### EXECUTION TYPES ###
# Each callback receives the already-rendered content.


def _message(player, content, args):
    player.send_message(content)


def _broadcast(player, content, args):
    player.server.broadcast_message(content)


def _title(player, content, args):
    title, _, subtitle = content.partition("|")
    player.send_title(title.strip(), subtitle.strip())


def _popup(player, content, args):
    player.send_popup(content)


def _player_command(player, content, args):
    # Runs with the player's own permissions (safer than the console).
    player.server.dispatch_command(player, content)


def _delay(player, content, args):
    # Handled by the plugin (it pauses the following lines); never called directly.
    pass


### CONDITION TYPES ###


def _permission_condition(player, content, args) -> bool:
    return bool(player.has_permission(content.strip()))


def _expression_condition(player, content, args) -> bool:
    left, op, right = parse_expression(content)
    left = render_template(player, left, args, strict=False)
    right = render_template(player, right, args, strict=False)
    return compare_values(left, op, right)


### PLACEHOLDERS ###


def _require(player, attribute: str, label: str):
    value = getattr(player, attribute, None)
    if value is None:
        raise InputError(f"{{{label}}} isn't available on this server version.")
    return value


def _coordinate(axis: str):
    def get(player, args):
        return str(math.floor(getattr(_require(player, "location", axis), axis)))

    return get


def _dimension(player, args):
    return str(_require(player, "dimension", "dimension").name).replace(" ", "")


def _online(player, args):
    return str(len(player.server.online_players))


def _gamemode(player, args):
    mode = _require(player, "game_mode", "gamemode")
    return str(getattr(mode, "name", mode)).lower()


def _health(player, args):
    return str(round(float(_require(player, "health", "health"))))


def _ping(player, args):
    return str(_require(player, "ping", "ping"))


def _uuid(player, args):
    return str(_require(player, "unique_id", "uuid"))


def _time(player, args):
    return datetime.now().strftime("%H:%M")


def _date(player, args):
    return datetime.now().strftime("%Y-%m-%d")


def register_builtins():
    """Registers the built-ins (safe to call several times)."""
    executions = [
        ("player_command", _player_command, True, False, "spawn"),
        ("message", _message, False, True, "§aHello {player}!"),
        ("broadcast", _broadcast, False, True, "{player} used a command"),
        ("title", _title, False, True, "Welcome|{player}"),
        ("popup", _popup, False, True, "Hello {player}"),
        ("delay", _delay, False, False, "5  (seconds before the next lines)"),
    ]
    for name, callback, strict, strip, hint in executions:
        if name not in ExecutionTypes.get_types():
            ExecutionTypes.register(name, callback, strict, strip, hint)

    conditions = [
        ("expression", _expression_condition, "{score:kills} >= 5"),
        ("permission", _permission_condition, "my.permission"),
    ]
    for name, callback, hint in conditions:
        if name not in ConditionTypes.get_types():
            ConditionTypes.register(name, callback, hint)

    placeholders = {
        "x": _coordinate("x"),
        "y": _coordinate("y"),
        "z": _coordinate("z"),
        "dimension": _dimension,
        "online": _online,
        "gamemode": _gamemode,
        "health": _health,
        "ping": _ping,
        "uuid": _uuid,
        "time": _time,
        "date": _date,
    }
    for identifier, callback in placeholders.items():
        if identifier not in PlaceholderTypes.get_types():
            PlaceholderTypes.register(identifier, callback)
