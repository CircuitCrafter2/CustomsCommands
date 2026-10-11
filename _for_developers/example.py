from endstone import Player
from .eac_api import CommandManager


class EAC(CommandManager):
    def __init__(self):
        super().__init__()

        self.commands.register(
            "jellydonut",
            "This is a test command.",
            ["/jellydonut <count: int>"],
            ["customscommands.command.all"],
            ["jd"],
            [
                {
                    "type": "donut_example",
                    "content": "{donut_count}!",
                }
            ],
        )
        self.placeholders.register("donut_count", example_placeholder)
        self.executions.register("donut_example", example_execution)


def example_placeholder(player: Player, args):
    if len(args) == 0:
        return "0 donuts"
    else:
        return f"{args[0]} donuts"


def example_execution(player: Player, content: str, args):
    player.send_message(f"§9How many donuts? §c{content}")
