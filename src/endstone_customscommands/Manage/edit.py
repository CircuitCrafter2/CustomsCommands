from .submit import submit_command
from ..Utils.utils import (
    error_custom,
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
from ..compat import Player
from ..API.types import ConditionTypes, ExecutionTypes
from ..Utils.security import (
    MAX_COOLDOWN,
    validate_condition,
    validate_execution_content,
)


def edit_command(self: Plugin, player: Player, command):
    form = ActionFormData()
    form.title("Edit: " + command["name"])
    form.button("Set Name")
    form.button("Set Description")
    form.button("Manage Usages")
    form.button("Manage Aliases")
    form.button("Manage Permissions")
    form.button("Set Cooldown")
    form.button("Manage Conditions")
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
            set_cooldown(self, player, command)
        elif result.selection == 6:
            manage_conditions(self, player, command)
        elif result.selection == 7:
            manage_functionality(self, player, command)
        elif result.selection == 8:
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


def execution_label(type_name: str) -> str:
    if type_name == "command":
        return "Enter a command for the server to run when executed."
    if type_name == "player_command":
        return "Enter a command to run as the player (with their permissions)."
    return "Enter content to be parsed when executed."


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
    # Index 0 is the "command" execution; the others are built-in or registered types.
    execution_types = ["command"] + ExecutionTypes.get_types()
    type_name = execution_types[type]
    form = ModalFormData()
    form.title("Add Execution")
    form.text_field(execution_label(type_name), ExecutionTypes.get_hint(type_name))

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command, type):
        if result.canceled:
            return manage_functionality(self, player, command)
        if not require_manager(player):
            return
        error = validate_execution_content(type, result.formValues[0])
        if error:
            error_custom(player, error)
            return manage_functionality(self, player, command)
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
    form.text_field(
        execution_label(functions[index]["type"]),
        functions[index]["content"],
        functions[index]["content"],
    )

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command, index):
        if result.canceled:
            return manage_functionality(self, player, command)
        if not require_manager(player):
            return
        error = validate_execution_content(
            functions[index]["type"], result.formValues[0]
        )
        if error:
            error_custom(player, error)
            return manage_functionality(self, player, command)
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


### COOLDOWN & CONDITIONS ###


def set_cooldown(self: Plugin, player: Player, command):
    form = ModalFormData()
    form.title("Set Cooldown")
    current = str(command.get("cooldown", 0))
    form.text_field("Seconds between two uses per player (0 = none)", "0", current)

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command):
        if result.canceled:
            return edit_command(self, player, command)
        value = str(result.formValues[0]).strip() or "0"
        if not value.isdigit() or int(value) > MAX_COOLDOWN:
            error_custom(
                player, f"The cooldown must be a whole number between 0 and {MAX_COOLDOWN}."
            )
        else:
            command["cooldown"] = int(value)
        edit_command(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command
        )
    )


def condition_line(condition) -> str:
    return strip_color_codes(f"{condition['type']}: {condition['content']}")


def manage_conditions(self: Plugin, player: Player, command):
    command.setdefault("conditions", [])
    form = ActionFormData()
    form.title("Manage Conditions")
    form.body("The command only runs if every condition is met.")
    form.button("Add Condition", "textures/ui/smithing-table-plus.png")
    form.button("Remove Condition", "textures/ui/dark_minus.png")
    for condition in command["conditions"]:
        form.button(condition_line(condition))

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return edit_command(self, player, command)
        if result.selection == 0:
            add_condition(self, player, command)
        elif result.selection == 1:
            remove_condition(self, player, command)
        else:
            edit_condition(self, player, command, result.selection - 2)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def add_condition(self: Plugin, player: Player, command):
    types = ConditionTypes.get_types()
    form = ModalFormData()
    form.title("Add Condition")
    form.dropdown("Type", types)
    form.text_field(
        "Content (expression: {score:kills} >= 5, permission: a permission node)",
        "{score:kills} >= 5",
    )
    form.text_field("Message shown when the condition isn't met", "You can't do that yet.")

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command):
        if result.canceled:
            return manage_conditions(self, player, command)
        condition = {
            "type": types[result.formValues[0]],
            "content": str(result.formValues[1]).strip(),
            "message": str(result.formValues[2]).strip(),
        }
        error = validate_condition(condition)
        if error:
            error_custom(player, error)
        else:
            command["conditions"].append(condition)
        manage_conditions(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command
        )
    )


def remove_condition(self: Plugin, player: Player, command):
    if not command["conditions"]:
        return manage_conditions(self, player, command)
    form = ActionFormData()
    form.title("Remove Condition")
    form.body("Click a condition to remove it.")
    for condition in command["conditions"]:
        form.button(condition_line(condition))

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return manage_conditions(self, player, command)
        command["conditions"].pop(result.selection)
        manage_conditions(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def edit_condition(self: Plugin, player: Player, command, index):
    condition = command["conditions"][index]
    form = ModalFormData()
    form.title("Edit Condition (" + condition["type"] + ")")
    form.text_field("Content", condition["content"], condition["content"])
    form.text_field(
        "Message shown when the condition isn't met",
        "You can't do that yet.",
        condition.get("message", ""),
    )

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command, index):
        if result.canceled:
            return manage_conditions(self, player, command)
        updated = {
            "type": command["conditions"][index]["type"],
            "content": str(result.formValues[0]).strip(),
            "message": str(result.formValues[1]).strip(),
        }
        error = validate_condition(updated)
        if error:
            error_custom(player, error)
        else:
            command["conditions"][index] = updated
        manage_conditions(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command, index
        )
    )
