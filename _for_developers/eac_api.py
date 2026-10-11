import typing
from endstone import Player

### Object Types ###


class SimpleFunctionality(typing.TypedDict):
    type: str
    content: str


class EasySlashCommand:
    def __init__(
        self,
        name: str,
        description: str,
        usages: list[str],
        permissions: list[str],
        aliases: list[str],
        functionality: list[SimpleFunctionality],
    ):
        self.name = name
        self.description = description
        self.usages = usages
        self.permissions = permissions
        self.aliases = aliases
        self.functionality = functionality


class EasyExecution:
    def __init__(
        self, name: str, callback: typing.Callable[[Player, str, list[str]], None]
    ):
        self.name = name
        self.callback = callback


class EasyCondition:
    def __init__(
        self, name: str, callback: typing.Callable[[Player, str, list[str]], bool]
    ):
        self.name = name
        self.callback = callback


class EasyPlaceholder:
    def __init__(
        self, identifier: str, callback: typing.Callable[[Player, list[str]], str]
    ):
        self.id = identifier
        self.callback = callback


### Main CommandManager class ###


class CommandManager:
    """
    The CommandManager class is an API for developers to easily manage and add functionality to **CustomsCommands**.

    ### Example
    ```python
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

    ```
    """

    def __init__(self):
        self.commands = self.SlashCommandManager(self)
        """
        Contains methods for managing commands.
        """
        self.executions = self.ExecutionManager(self)
        """
        Contains methods for managing execution types.
        """
        self.placeholders = self.PlaceholderManager(self)
        """
        Contains methods for managing placeholders.
        """
        self._commands = []
        self._executions = []
        self._placeholders = []

    class SlashCommandManager:
        def __init__(self, command_manager):
            self.manager: CommandManager = command_manager
            """
            CommandManager object.
            """

        def register(
            self,
            name: str,
            description: str,
            usages: list[str],
            permissions: list[str] = ["customscommands.command.op"],
            aliases: list[str] = [],
            functionality: list[SimpleFunctionality] = [],
        ):
            """
            Registers a slash command that can be managed by CustomsCommands.
            """
            self.manager._commands.append(
                EasySlashCommand(
                    name, description, usages, permissions, aliases, functionality
                )
            )

    class ExecutionManager:
        def __init__(self, command_manager):
            self.manager: CommandManager = command_manager
            """
            CommandManager object.
            """

        def register(
            self, name: str, callback: typing.Callable[[Player, str, list[str]], None]
        ):
            """
            Registers an execution type for use in commands.
            """
            self.manager._executions.append(EasyExecution(name, callback))

    class PlaceholderManager:
        def __init__(self, command_manager):
            self.manager: CommandManager = command_manager
            """
            CommandManager object.
            """

        def register(
            self,
            identifier: str,
            callback: typing.Callable[[Player, list[str]], str],
        ):
            """
            Registers a placeholder for use in commands.
            """
            self.manager._placeholders.append(EasyPlaceholder(identifier, callback))
