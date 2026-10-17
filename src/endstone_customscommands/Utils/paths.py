"""
Locations of the plugin's files, like a classic plugin: plugins/<plugin name>/

    config.json      settings
    commands.json    commands and their executions
    lang/            translations (any language can be customised)
    data/            usage counters (usage limits)
    exports/         exported command files (also where imports are read from)
    backups/         automatic backups made before risky operations
"""

import os
from pathlib import Path

PLUGIN_NAME = "customscommands"  # the entry point name, i.e. Endstone's plugin name

# Commands are registered from class attributes when the module is imported, which is
# before Endstone gives us `plugin.data_folder`. We start from Endstone's convention and
# the plugin aligns it with the real folder in on_load (see set_data_dir).
_data_dir = Path("plugins") / PLUGIN_NAME


def data_dir() -> Path:
    return _data_dir


def set_data_dir(path) -> None:
    global _data_dir
    _data_dir = Path(path)


def file(*parts: str) -> Path:
    return _data_dir.joinpath(*parts)


def legacy_config_file() -> str:
    """Where EasyAsCommands / CustomsCommands < 0.6 stored the configuration."""
    return os.path.abspath(os.path.join("config", "command_manager.json"))
