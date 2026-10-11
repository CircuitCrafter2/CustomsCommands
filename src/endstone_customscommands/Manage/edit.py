from .submit import submit_command
from ..Utils.utils import (
    read_commands_config,
    require_manager,
    strip_color_codes,
    write_commands_config,
)

from endstone.plugin import Plugin
from ..form_wrapper import (
    ActionFormData,
    ActionFormResponse,
    MessageFormData,
    MessageFormResponse,
    ModalFormData,
    ModalFormResponse,
)
from endstone._internal.endstone_python import Player
from ..API.types import ExecutionTypes


def edit_command(self: Plugin, player: Player, command):
    form = ActionFormData()
    form.title("Edit: " + command["name"])
    form.button("Set Name")
    form.button("Set Description")
    form.button("Manage Usages")
    form.button("Manage Aliases")
    form.button("Manage Permissions")
    form.button("§9Functionality")
    form.button("Submit")

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return confirm_exit_edit_command(self, player, command)
        if result.selection == 0:
            set_command_name(self, player, command)
        elif result.selection == 1:
            set_command_description(self, player, command)
        elif result.selection == 2:
            manage_usages(self, player, command)
        elif result.selection == 3:
            manage_aliases(self, player, command)
        elif result.selection == 4:
            manage_permissions(self, player, command)
        elif result.selection == 5:
            manage_functionality(self, player, command)
        elif result.selection == 6:
            submit_command(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def confirm_exit_edit_command(self: Plugin, player: Player, command):
    form = MessageFormData()
    form.title("Confirm Exit")
    form.body("Are you sure you want to exit without saving?")
    form.button1("Yes, exit")
    form.button2("No, keep editing")

    def exit_edit_command(
        self: Plugin, player: Player, result: MessageFormResponse, command
    ):
        if result.canceled or result.selection == 0:
            return
        else:
            edit_command(self, player, command)

    form.show(player).then(
        lambda player=Player, response=MessageFormResponse: exit_edit_command(
            self, player, response, command
        )
    )


def manage_permissions(self: Plugin, player: Player, command):
    form = ActionFormData()
    form.title("Manage Permissions")
    form.body("Click a permission to edit it.")
    form.button("Add Permission", "textures/ui/smithing-table-plus.png")
    form.button("Remove Permission", "textures/ui/dark_minus.png")
    if "permissions" in command:
        for permission in command["permissions"]:
            form.button(permission)

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return edit_command(self, player, command)
        if result.selection == 0:
            add_permission(self, player, command)
        elif result.selection == 1:
            remove_permission(self, player, command)
        else:
            edit_permission(self, player, command, result.selection - 2)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def add_permission(self: Plugin, player: Player, command):
    form = ModalFormData()
    form.title("Add Permission")
    form.text_field("Permission", "customscommands.command.all", "customscommands.command.all")

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command):
        if result.canceled:
            return manage_permissions(self, player, command)
        command["permissions"].append(result.formValues[0])
        manage_permissions(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command
        )
    )


def remove_permission(self: Plugin, player: Player, command):
    form = ActionFormData()
    form.title("Remove Permission")
    form.body("Click a permission to remove it.")
    for permission in command["permissions"]:
        form.button(permission)

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return manage_permissions(self, player, command)
        command["permissions"].pop(result.selection)
        manage_permissions(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def edit_permission(self: Plugin, player: Player, command, index):
    form = ModalFormData()
    form.title("Edit Permission")
    form.text_field(
        "Permission", command["permissions"][index], command["permissions"][index]
    )

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command, index):
        if result.canceled:
            return manage_permissions(self, player, command)
        command["permissions"][index] = result.formValues[0]
        manage_permissions(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command, index
        )
    )


def manage_aliases(self: Plugin, player: Player, command):
    form = ActionFormData()
    form.title("Manage Aliases")
    form.body("Click an alias to edit it.")
    form.button("Add Alias", "textures/ui/smithing-table-plus.png")
    form.button("Remove Alias", "textures/ui/dark_minus.png")
    if "aliases" in command:
        for alias in command["aliases"]:
            form.button(alias)

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return edit_command(self, player, command)
        if result.selection == 0:
            add_alias(self, player, command)
        elif result.selection == 1:
            remove_alias(self, player, command)
        else:
            edit_alias(self, player, command, result.selection - 2)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def add_alias(self: Plugin, player: Player, command):
    form = ModalFormData()
    form.title("Add Alias")
    form.text_field("Alias", "...")

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command):
        if result.canceled:
            return manage_aliases(self, player, command)
        command["aliases"].append(result.formValues[0])
        manage_aliases(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command
        )
    )


def remove_alias(self: Plugin, player: Player, command):
    form = ActionFormData()
    form.title("Remove Alias")
    form.body("Click an alias to remove it.")
    for alias in command["aliases"]:
        form.button(alias)

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return manage_aliases(self, player, command)
        command["aliases"].pop(result.selection)
        manage_aliases(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def edit_alias(self: Plugin, player: Player, command, index):
    form = ModalFormData()
    form.title("Edit Alias")
    form.text_field("Alias", command["aliases"][index], command["aliases"][index])

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command, index):
        if result.canceled:
            return manage_aliases(self, player, command)
        command["aliases"][index] = result.formValues[0]
        manage_aliases(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command, index
        )
    )


def manage_usages(self: Plugin, player: Player, command):
    form = ActionFormData()
    form.title("Manage Usages")
    form.body("Click a usage to edit it.")
    form.button("Add Usage", "textures/ui/smithing-table-plus.png")
    form.button("Remove Usage", "textures/ui/dark_minus.png")
    if "usages" in command:
        for usage in command["usages"]:
            form.button(usage)

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return edit_command(self, player, command)
        if result.selection == 0:
            add_usage(self, player, command)
        elif result.selection == 1:
            remove_usage(self, player, command)
        else:
            edit_usage(self, player, command, result.selection - 2)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def add_usage(self: Plugin, player: Player, command):
    form = ModalFormData()
    form.title("Add Usage")
    if "name" in command:
        form.text_field("Usage", "/" + command["name"] + " <arg1: str> <arg2: int>")
    else:
        form.text_field("Usage", "/command <arg1: str> <arg2: int>")

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command):
        if result.canceled:
            return manage_usages(self, player, command)
        command["usages"].append(result.formValues[0])
        manage_usages(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command
        )
    )


def remove_usage(self: Plugin, player: Player, command):
    form = ActionFormData()
    form.title("Remove Usage")
    form.body("Click a usage to remove it.")
    for usage in command["usages"]:
        form.button(usage)

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return manage_usages(self, player, command)
        command["usages"].pop(result.selection)
        manage_usages(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def edit_usage(self: Plugin, player: Player, command, index):
    form = ModalFormData()
    form.title("Edit Usage")
    if "usages" in command:
        form.text_field("Usage", command["usages"][index], command["usages"][index])
    else:
        if "name" in command:
            form.text_field("Usage", "/" + command["name"] + " <arg1: str> <arg2: int>")
        else:
            form.text_field("Usage", "/command <arg1: str> <arg2: int>")

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command, index):
        if result.canceled:
            return manage_usages(self, player, command)
        command["usages"][index] = result.formValues[0]
        manage_usages(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command, index
        )
    )


def set_command_description(self: Plugin, player: Player, command):
    form = ModalFormData()
    form.title("Set Command Description")
    if "description" in command:
        form.text_field("Description", command["description"], command["description"])
    else:
        form.text_field("Description", "...")

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command):
        if result.canceled:
            return edit_command(self, player, command)
        command["description"] = result.formValues[0]
        edit_command(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command
        )
    )


def set_command_name(self: Plugin, player: Player, command):
    form = ModalFormData()
    form.title("Set Command Name")
    if "name" in command:
        form.text_field("Name", command["name"], command["name"])
    else:
        form.text_field("Name", "helloworld")

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command):
        if result.canceled:
            return edit_command(self, player, command)
        command["name"] = result.formValues[0]
        edit_command(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command
        )
    )


def functions_key(command):
    """Key under which the command's functionality is stored in the JSON."""
    return command.get("_original_name") or command["name"]


def manage_functionality(self: Plugin, player: Player, command):
    form = ActionFormData()
    form.title("Manage Functionality")
    form.body("Functionality determines what happens when your command is executed.")
    form.button("Add Execution", "textures/ui/smithing-table-plus.png")
    form.button("Remove Execution", "textures/ui/dark_minus.png")
    commandData = read_commands_config()
    functions = commandData["functions"]
    if functions_key(command) in functions:
        for func in functions[functions_key(command)]:
            line = func["type"] + ": " + func["content"]
            form.button(strip_color_codes(line))

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return edit_command(self, player, command)
        if result.selection == 0:
            select_functionality(self, player, command)
        elif result.selection == 1:
            remove_functionality(self, player, command)
        else:
            edit_functionality(self, player, command, result.selection - 2)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def select_functionality(self: Plugin, player: Player, command):
    form = ActionFormData()
    form.title("Select Execution")
    form.body("Select an execution type:")
    form.button("Command")
    for type in ExecutionTypes.get_types():
        form.button(type)

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return manage_functionality(self, player, command)
        else:
            add_functionality(self, player, command, result.selection)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def add_functionality(self: Plugin, player: Player, command, type: int):
    # Index 0 is the built-in "command" execution; the others come from integrations.
    execution_types = ["command"] + ExecutionTypes.get_types()
    type_name = execution_types[type]
    form = ModalFormData()
    form.title("Add Execution")
    if type_name == "command":
        form.text_field(
            "Enter a command for the server to run when executed.",
            "say Hello, {0} {1}!",
        )
    else:
        form.text_field("Enter content to be parsed when executed.", "{0} {1}")

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command, type):
        if result.canceled:
            return manage_functionality(self, player, command)
        if not require_manager(player):
            return
        commandData = read_commands_config()
        key = functions_key(command)
        if key not in commandData["functions"]:
            commandData["functions"][key] = []
        commandData["functions"][key].append(
            {"type": type, "content": result.formValues[0]}
        )
        write_commands_config(commandData)
        manage_functionality(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command, type_name
        )
    )


def remove_functionality(self: Plugin, player: Player, command):
    form = ActionFormData()
    form.title("Remove Execution")
    form.body("Click an execution to remove it.")
    commandData = read_commands_config()
    functions = commandData["functions"]
    if functions_key(command) not in functions:
        return manage_functionality(self, player, command)
    for func in functions[functions_key(command)]:
        line = func["type"] + ": " + func["content"]
        form.button(strip_color_codes(line))

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return manage_functionality(self, player, command)
        if not require_manager(player):
            return
        commandData = read_commands_config()
        commandData["functions"][functions_key(command)].pop(result.selection)
        write_commands_config(commandData)
        manage_functionality(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def edit_functionality(self: Plugin, player: Player, command, index):
    commandData = read_commands_config()
    functions = commandData["functions"][functions_key(command)]
    form = ModalFormData()
    form.title("Edit Execution")
    if functions[index]["type"] == "command":
        form.text_field(
            "Enter a command for the server to run when executed.",
            functions[index]["content"],
            functions[index]["content"],
        )
    else:
        form.text_field(
            "Enter content to be parsed when executed.",
            functions[index]["content"],
            functions[index]["content"],
        )

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command, index):
        if result.canceled:
            return manage_functionality(self, player, command)
        if not require_manager(player):
            return
        commandData["functions"][functions_key(command)][index] = {
            "type": functions[index]["type"],
            "content": result.formValues[0],
        }
        write_commands_config(commandData)
        manage_functionality(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command, index
        )
    )
