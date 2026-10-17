from endstone.plugin import Plugin

from ..compat import Player
from .edit import edit_command


def add_command(self: Plugin, player: Player, command):
    """Adding a command uses the same editor as editing one."""
    edit_command(self, player, command)
