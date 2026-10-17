"""
Optional integration with StonePerms (plugin "stoneperms", a permission system for Endstone).

Executions that manage the permissions of the player who used the command, by running the
documented `/stoneperms user <player> ...` commands as the console:

    stoneperms_group_add         <group> [duration] [key=value ...]
    stoneperms_group_remove      <group> [key=value ...]
    stoneperms_permission_set    <node> [true|false] [duration] [key=value ...]
    stoneperms_permission_unset  <node> [key=value ...]
    stoneperms_promote           <track> [--dont-add-to-first] [key=value ...]

Every value is checked against a strict whitelist: nothing else can reach the console.
Wildcard permissions (*) are refused on purpose.
"""

import re

from ..API.types import ExecutionTypes
from ..Utils.lang import t
from ..Utils.security import InputError, PLACEHOLDER_RE
from ..Utils.utils import read_commands_config
from . import registry

ID = "stoneperms"
TITLE = "StonePerms"
PLUGIN_NAMES = ("stoneperms",)
COMMANDS = ("stoneperms",)

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$")  # groups and tracks
NODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,127}$")  # permission nodes (no wildcard)
DURATION_RE = re.compile(r"^(?:[0-9]{1,6}[smhdw]){1,6}$")  # 7d, 2h30m, 1w
CONTEXT_RE = re.compile(r"^[A-Za-z0-9_\-]{1,32}=[A-Za-z0-9_.\-]{1,64}$")  # server=lobby
FLAG = "--dont-add-to-first"

registry.declare(ID, TITLE)


def _check(value: str, regex, what_key: str) -> str:
    if not regex.match(value):
        raise InputError(t("val.integration_token", what=t(what_key), value=value))
    return value


def _contexts(tokens: list) -> list:
    return [_check(token, CONTEXT_RE, "val.what_context") for token in tokens]


def _take(tokens: list, regex, what_key: str) -> str:
    if not tokens:
        raise InputError(t("val.integration_missing", what=t(what_key)))
    return _check(tokens.pop(0), regex, what_key)


def _optional_duration(tokens: list):
    if tokens and DURATION_RE.match(tokens[0]):
        return tokens.pop(0)
    return None


### Builders: the words that follow `stoneperms user <player>` ###


def group_add(tokens: list) -> list:
    group = _take(tokens, NAME_RE, "val.what_group")
    duration = _optional_duration(tokens)
    contexts = _contexts(tokens)
    if duration:
        return ["parent", "addtemp", group, duration, *contexts]
    return ["parent", "add", group, *contexts]


def group_remove(tokens: list) -> list:
    group = _take(tokens, NAME_RE, "val.what_group")
    return ["parent", "remove", group, *_contexts(tokens)]


def permission_set(tokens: list) -> list:
    node = _take(tokens, NODE_RE, "val.what_permission")
    value = "true"
    if tokens and tokens[0] in ("true", "false"):
        value = tokens.pop(0)
    duration = _optional_duration(tokens)
    contexts = _contexts(tokens)
    if duration:
        return ["permission", "settemp", node, value, duration, *contexts]
    return ["permission", "set", node, value, *contexts]


def permission_unset(tokens: list) -> list:
    node = _take(tokens, NODE_RE, "val.what_permission")
    return ["permission", "unset", node, *_contexts(tokens)]


def promote(tokens: list) -> list:
    track = _take(tokens, NAME_RE, "val.what_track")
    flag = []
    if tokens and tokens[0] == FLAG:
        flag = [tokens.pop(0)]
    return ["promote", track, *flag, *_contexts(tokens)]


EXECUTIONS = [
    ("stoneperms_group_add", group_add, "<group> [duration] [key=value ...]", "vip 7d"),
    ("stoneperms_group_remove", group_remove, "<group> [key=value ...]", "vip"),
    ("stoneperms_permission_set", permission_set, "<node> [true|false] [duration] [key=value ...]", "fly.use 1d"),
    ("stoneperms_permission_unset", permission_unset, "<node> [key=value ...]", "fly.use"),
    ("stoneperms_promote", promote, f"<track> [{FLAG}] [key=value ...]", "staff"),
]


def build_command(builder, content: str, user: str) -> str:
    """The full console command for `content`, or InputError. `user` is the player's UUID."""
    words = builder(content.split())
    return " ".join(["stoneperms", "user", user, *words])


def _make_execution(builder, syntax: str):
    def execute(player, content, args):
        registry.require_active(ID)
        server = player.server
        command = build_command(builder, content, str(player.unique_id))
        if server.dispatch_command(server.command_sender, command) is False:
            raise InputError(t("err.dependency_failed", plugin=TITLE))

    return execute


def _make_validator(builder, syntax: str):
    def validate(content: str):
        # Placeholders are filled in later: check the structure with a stand-in value.
        sample = PLACEHOLDER_RE.sub("x", content)
        try:
            build_command(builder, sample, "uuid")
        except InputError as e:
            return t("val.integration_syntax", syntax=syntax) + " " + str(e)
        return None

    return validate


def register_types() -> None:
    """Registers the execution types (always: only their use needs the plugin)."""
    for name, builder, syntax, hint in EXECUTIONS:
        if name not in ExecutionTypes.get_types():
            ExecutionTypes.register(
                name,
                _make_execution(builder, syntax),
                strict=True,
                hint=hint,
                group=ID,
                command_start=False,
                validator=_make_validator(builder, syntax),
            )


def enable(plugin) -> bool:
    settings = read_commands_config()["settings"]["integrations"][ID]
    if not settings["enabled"]:
        registry.set_state(ID, "disabled")
        return False
    if not registry.detect(plugin.server, PLUGIN_NAMES, COMMANDS):
        registry.set_state(ID, "missing")
        return False
    registry.set_state(ID, "active")
    plugin.logger.info("StonePerms found: the stoneperms_* executions are available.")
    return True
