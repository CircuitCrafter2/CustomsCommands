"""
Optional integration with the MediaPlayer plugin (plugin "endstone_mediaplayer", plays .nbs
songs and is controlled with /mpm commands).

Executions: media_play <song>, media_pause, media_resume, media_stop.

The /mpm commands are built from templates stored in config.json
("integrations" -> "mediaplayer" -> "commands"), because they are the plugin's own syntax:
if its commands differ from the defaults, change the templates there (see /help mpm).
Only the song name is filled in, after a strict check.
"""

import re

from ..API.types import ExecutionTypes
from ..Utils.lang import t
from ..Utils.security import InputError, PLACEHOLDER_RE
from ..Utils.utils import read_commands_config
from . import registry

ID = "mediaplayer"
TITLE = "MediaPlayer"
PLUGIN_NAMES = ("endstone_mediaplayer", "mediaplayer")
COMMANDS = ("mpm",)

# A file name: starts with a letter or digit, then letters, digits, spaces and a few symbols.
# No quotes, slashes, backslashes, semicolons or control characters.
SONG_RE = re.compile(r"^[^\W_][\w .\-()\[\]&',+]{0,99}$")

registry.declare(ID, TITLE)


def parse_song(content: str) -> str:
    """The song name inside the content (one pair of surrounding quotes is allowed)."""
    song = content.strip()
    if len(song) >= 2 and song[0] == song[-1] == '"':
        song = song[1:-1].strip()
    if not SONG_RE.match(song):
        raise InputError(t("val.integration_token", what=t("val.what_song"), value=song))
    return song


def build_command(action: str, template: str, content: str = "") -> str:
    if action != "play":
        return template
    song = parse_song(content)
    return template.replace("{song}", f'"{song}"' if " " in song else song)


def _make_execution(action: str):
    def execute(player, content, args):
        registry.require_active(ID)
        server = player.server
        settings = read_commands_config()["settings"]["integrations"][ID]
        command = build_command(action, settings["commands"][action], content)
        sender = player if settings["run_as"] == "player" else server.command_sender
        if server.dispatch_command(sender, command) is False:
            raise InputError(t("err.dependency_failed", plugin=TITLE))

    return execute


def _validate_song(content: str):
    try:
        parse_song(PLACEHOLDER_RE.sub("x", content))
    except InputError as e:
        return t("val.integration_syntax", syntax="<song>") + " " + str(e)
    return None


def register_types() -> None:
    if "media_play" not in ExecutionTypes.get_types():
        ExecutionTypes.register(
            "media_play",
            _make_execution("play"),
            strict=True,
            hint="My Song.nbs",
            group=ID,
            command_start=False,
            validator=_validate_song,
        )
    for action in ("pause", "resume", "stop"):
        name = f"media_{action}"
        if name not in ExecutionTypes.get_types():
            ExecutionTypes.register(
                name,
                _make_execution(action),
                hint="-",
                group=ID,
                needs_content=False,
            )


def enable(plugin) -> bool:
    settings = read_commands_config()["settings"]["integrations"][ID]
    if not settings["enabled"]:
        registry.set_state(ID, "disabled")
        return False
    if not registry.detect(plugin.server, PLUGIN_NAMES, COMMANDS):
        registry.set_state(ID, "missing")
        return False
    registry.set_state(ID, "active", "/" + " | /".join(settings["commands"].values()))
    shown = ""
    try:  # show the plugin's real syntax so the templates can be compared with it
        shown = f" Its /mpm usages: {list(plugin.server.get_plugin_command('mpm').usages)}."
    except Exception:
        pass
    plugin.logger.info(
        "MediaPlayer found: the media_* executions are available. "
        f"Commands used: {settings['commands']} (run as {settings['run_as']}).{shown} "
        "If they don't match, change them in config.json."
    )
    return True
