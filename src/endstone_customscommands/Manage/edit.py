from ..Utils.lang import t
from .submit import submit_command
from ..Utils.utils import (
    error_custom,
    send_custom,
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
from ..Utils.usage import USAGE
from ..Integrations import registry
from ..Utils.security import (
    MAX_ARG_INDEX,
    MAX_COOLDOWN,
    NAME_RE,
    specific_permission,
    validate_argument_rule,
    validate_condition,
    validate_execution_content,
    validate_limit,
)


def edit_command(self: Plugin, player: Player, command):
    """The command editor, used both to add a new command and to edit an existing one."""
    existing = bool(command.get("_original_name"))
    actions = [
        ("name", "ui.button.set_name"),
        ("description", "ui.button.set_description"),
        ("usages", "ui.button.manage_usages"),
        ("aliases", "ui.button.manage_aliases"),
        ("permissions", "ui.button.manage_permissions"),
        ("cooldown", "ui.button.set_cooldown"),
        ("limit", "ui.button.set_usage_limit"),
        ("arguments", "ui.button.manage_arguments"),
        ("conditions", "ui.button.manage_conditions"),
        ("functionality", "ui.button.functionality"),
    ]
    if existing:
        actions.append(("reset_usage", "ui.button.reset_usage"))
    actions.append(("submit", "ui.button.submit"))

    form = ActionFormData()
    if command.get("name"):
        form.title(t("ui.title.edit", name=command["name"]))
    else:
        form.title(t("ui.title.add_command"))
    for _, label in actions:
        form.button(t(label))

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return confirm_exit_edit_command(self, player, command)
        action = actions[result.selection][0]
        if action == "functionality" and not command.get("name"):
            error_custom(player, t("err.name_required"))
            return edit_command(self, player, command)
        handlers = {
            "name": set_command_name,
            "description": set_command_description,
            "usages": manage_usages,
            "aliases": manage_aliases,
            "permissions": manage_permissions,
            "cooldown": set_cooldown,
            "limit": set_usage_limit,
            "arguments": manage_arguments,
            "conditions": manage_conditions,
            "functionality": manage_functionality,
            "reset_usage": reset_usage_counts,
            "submit": submit_command,
        }
        handlers[action](self, player, command)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def confirm_exit_edit_command(self: Plugin, player: Player, command):
    form = MessageFormData()
    form.title(t("ui.title.confirm_exit"))
    form.body(t("ui.body.confirm_exit"))
    form.button1(t("ui.button.yes_exit"))
    form.button2(t("ui.button.no_keep_editing"))

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
    form.title(t("ui.title.manage_permissions"))
    form.body(t("ui.body.click_a_permission_to_edit_it"))
    form.button(t("ui.button.add_permission"), "textures/ui/smithing-table-plus.png")
    form.button(t("ui.button.add_specific_permission"), "textures/ui/smithing-table-plus.png")
    form.button(t("ui.button.remove_permission"), "textures/ui/dark_minus.png")
    if "permissions" in command:
        for permission in command["permissions"]:
            form.button(permission)

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return edit_command(self, player, command)
        if result.selection == 0:
            add_permission(self, player, command)
        elif result.selection == 1:
            add_specific_permission(self, player, command)
        elif result.selection == 2:
            remove_permission(self, player, command)
        else:
            edit_permission(self, player, command, result.selection - 3)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def add_permission(self: Plugin, player: Player, command):
    form = ModalFormData()
    form.title(t("ui.title.add_permission"))
    form.text_field(t("ui.field.permission"), "customscommands.command.all", "customscommands.command.all")

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command):
        if result.canceled:
            return manage_permissions(self, player, command)
        permission = str(result.formValues[0]).strip()
        if permission and permission not in command["permissions"]:
            command["permissions"].append(permission)
        manage_permissions(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command
        )
    )


def add_specific_permission(self: Plugin, player: Player, command):
    """Adds customscommands.custom.<name>, the permission dedicated to this command."""
    name = command.get("name")
    if not name:
        error_custom(player, t("err.name_required"))
    elif not NAME_RE.match(name):
        error_custom(player, t("err.name_invalid_for_permission"))
    else:
        node = specific_permission(name)
        if node in command["permissions"]:
            error_custom(player, t("err.permission_exists", node=node))
        else:
            command["permissions"].append(node)
            send_custom(player, t("msg.permission_added", node=node))
    manage_permissions(self, player, command)


def remove_permission(self: Plugin, player: Player, command):
    form = ActionFormData()
    form.title(t("ui.title.remove_permission"))
    form.body(t("ui.body.click_a_permission_to_remove_it"))
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
    form.title(t("ui.title.edit_permission"))
    form.text_field(
        t("ui.field.permission"), command["permissions"][index], command["permissions"][index]
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
    form.title(t("ui.title.manage_aliases"))
    form.body(t("ui.body.click_an_alias_to_edit_it"))
    form.button(t("ui.button.add_alias"), "textures/ui/smithing-table-plus.png")
    form.button(t("ui.button.remove_alias"), "textures/ui/dark_minus.png")
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
    form.title(t("ui.title.add_alias"))
    form.text_field(t("ui.field.alias"), "...")

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
    form.title(t("ui.title.remove_alias"))
    form.body(t("ui.body.click_an_alias_to_remove_it"))
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
    form.title(t("ui.title.edit_alias"))
    form.text_field(t("ui.field.alias"), command["aliases"][index], command["aliases"][index])

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
    form.title(t("ui.title.manage_usages"))
    form.body(t("ui.body.click_a_usage_to_edit_it"))
    form.button(t("ui.button.add_usage"), "textures/ui/smithing-table-plus.png")
    form.button(t("ui.button.remove_usage"), "textures/ui/dark_minus.png")
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
    form.title(t("ui.title.add_usage"))
    if "name" in command:
        form.text_field(t("ui.field.usage"), "/" + command["name"] + " <arg1: str> <arg2: int>")
    else:
        form.text_field(t("ui.field.usage"), "/command <arg1: str> <arg2: int>")

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
    form.title(t("ui.title.remove_usage"))
    form.body(t("ui.body.click_a_usage_to_remove_it"))
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
    form.title(t("ui.title.edit_usage"))
    if "usages" in command:
        form.text_field(t("ui.field.usage"), command["usages"][index], command["usages"][index])
    else:
        if "name" in command:
            form.text_field(t("ui.field.usage"), "/" + command["name"] + " <arg1: str> <arg2: int>")
        else:
            form.text_field(t("ui.field.usage"), "/command <arg1: str> <arg2: int>")

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
    form.title(t("ui.title.set_command_description"))
    if "description" in command:
        form.text_field(t("ui.field.description"), command["description"], command["description"])
    else:
        form.text_field(t("ui.field.description"), "...")

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
    form.title(t("ui.title.set_command_name"))
    if "name" in command:
        form.text_field(t("ui.field.name"), command["name"], command["name"])
    else:
        form.text_field(t("ui.field.name"), "helloworld")

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
        return t("ui.field.exec_command")
    if type_name == "player_command":
        return t("ui.field.exec_player_command")
    return t("ui.field.exec_content")


def functions_key(command):
    """Key under which the command's functionality is stored in the JSON."""
    return command.get("_original_name") or command["name"]


def manage_functionality(self: Plugin, player: Player, command):
    form = ActionFormData()
    form.title(t("ui.title.manage_functionality"))
    form.body(t("ui.body.functionality_help"))
    form.button(t("ui.button.add_execution"), "textures/ui/smithing-table-plus.png")
    form.button(t("ui.button.remove_execution"), "textures/ui/dark_minus.png")
    commandData = read_commands_config()
    functions = commandData["functions"]
    if functions_key(command) in functions:
        for func in functions[functions_key(command)]:
            line = func["type"] + ": " + func["content"]
            if func.get("conditions"):
                line += f" [{len(func['conditions'])}]"
            form.button(strip_color_codes(line))

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return edit_command(self, player, command)
        if result.selection == 0:
            select_functionality(self, player, command)
        elif result.selection == 1:
            remove_functionality(self, player, command)
        else:
            execution_menu(self, player, command, result.selection - 2)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def select_functionality(self: Plugin, player: Player, command):
    """Choose the type of a new execution. Types of other plugins are under Dependencies."""
    main_types = [n for n in ExecutionTypes.get_types() if not ExecutionTypes.get_group(n)]
    actions = [("type", "command")] + [("type", n) for n in main_types]
    if registry.active_groups():
        actions.append(("dependencies",))
    form = ActionFormData()
    form.title(t("ui.title.select_execution"))
    form.body(t("ui.body.select_an_execution_type"))
    for action in actions:
        if action[0] == "dependencies":
            form.button(t("ui.button.dependencies_submenu"))
        elif action[1] == "command":
            form.button(t("ui.button.command"))
        else:
            form.button(action[1])

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return manage_functionality(self, player, command)
        action = actions[result.selection]
        if action[0] == "dependencies":
            select_dependency_group(self, player, command)
        else:
            add_functionality(self, player, command, action[1])

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def select_dependency_group(self: Plugin, player: Player, command):
    """The plugins CustomsCommands works with (only the ones that are active)."""
    groups = registry.active_groups()
    form = ActionFormData()
    form.title(t("ui.title.dependencies"))
    form.body(t("ui.body.select_dependency"))
    for group in groups:
        form.button(registry.title(group))

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return select_functionality(self, player, command)
        select_dependency_type(self, player, command, groups[result.selection])

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def select_dependency_type(self: Plugin, player: Player, command, group: str):
    types = registry.types_of(group)
    form = ActionFormData()
    form.title(registry.title(group))
    form.body(t("ui.body.select_an_execution_type"))
    for name in types:
        form.button(name)

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return select_dependency_group(self, player, command)
        add_functionality(self, player, command, types[result.selection])

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def _append_execution(self: Plugin, player: Player, command, type_name: str, content: str):
    if not require_manager(player):
        return
    error = validate_execution_content(type_name, content)
    if error:
        error_custom(player, error)
        return manage_functionality(self, player, command)
    commandData = read_commands_config()
    key = functions_key(command)
    commandData["functions"].setdefault(key, []).append(
        {"type": type_name, "content": content}
    )
    write_commands_config(commandData)
    manage_functionality(self, player, command)


def add_functionality(self: Plugin, player: Player, command, type_name: str):
    if not ExecutionTypes.needs_content(type_name):
        # Nothing to type (for example media_pause): the line is added right away.
        return _append_execution(self, player, command, type_name, "-")
    form = ModalFormData()
    form.title(t("ui.title.add_execution"))
    form.text_field(execution_label(type_name), ExecutionTypes.get_hint(type_name))

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command, type):
        if result.canceled:
            return manage_functionality(self, player, command)
        _append_execution(self, player, command, type, result.formValues[0])

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command, type_name
        )
    )


def remove_functionality(self: Plugin, player: Player, command):
    form = ActionFormData()
    form.title(t("ui.title.remove_execution"))
    form.body(t("ui.body.click_an_execution_to_remove_it"))
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
    form.title(t("ui.title.edit_execution"))
    form.text_field(
        execution_label(functions[index]["type"]),
        functions[index]["content"],
        functions[index]["content"],
    )

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command, index):
        if result.canceled:
            return execution_menu(self, player, command, index)
        if not require_manager(player):
            return
        error = validate_execution_content(
            functions[index]["type"], result.formValues[0]
        )
        if error:
            error_custom(player, error)
            return execution_menu(self, player, command, index)
        updated = dict(functions[index])  # keeps the line's conditions
        updated["content"] = result.formValues[0]
        commandData["functions"][functions_key(command)][index] = updated
        write_commands_config(commandData)
        execution_menu(self, player, command, index)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command, index
        )
    )


def execution_menu(self: Plugin, player: Player, command, index):
    """One execution line: edit it, give it conditions, or move it."""
    lines = read_commands_config()["functions"].get(functions_key(command), [])
    if not 0 <= index < len(lines):
        return manage_functionality(self, player, command)
    line = lines[index]
    form = ActionFormData()
    form.title(t("ui.title.execution", n=index + 1))
    form.body(
        t(
            "ui.body.execution",
            type=line["type"],
            content=strip_color_codes(line["content"]),
            conditions=len(line.get("conditions", [])),
        )
    )
    form.button(t("ui.button.edit_content"))
    form.button(t("ui.button.line_conditions", count=len(line.get("conditions", []))))
    form.button(t("ui.button.move_up"))
    form.button(t("ui.button.move_down"))

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command, index):
        if result.canceled:
            return manage_functionality(self, player, command)
        if result.selection == 0:
            edit_functionality(self, player, command, index)
        elif result.selection == 1:
            manage_line_conditions(self, player, command, index)
        elif result.selection == 2:
            move_execution(self, player, command, index, -1)
        else:
            move_execution(self, player, command, index, +1)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command, index
        )
    )


def move_execution(self: Plugin, player: Player, command, index, delta):
    if not require_manager(player):
        return
    data = read_commands_config()
    lines = data["functions"].get(functions_key(command), [])
    target = index + delta
    if 0 <= target < len(lines):
        lines[index], lines[target] = lines[target], lines[index]
        write_commands_config(data)
        index = target
    execution_menu(self, player, command, index)


def manage_line_conditions(self: Plugin, player: Player, command, index):
    """Conditions of ONE line: the line only runs when they are all met."""
    key = functions_key(command)
    lines = read_commands_config()["functions"].get(key, [])
    if not 0 <= index < len(lines):
        return manage_functionality(self, player, command)
    conditions = [dict(c) for c in lines[index].get("conditions", [])]

    def persist():
        if not require_manager(player):
            return
        data = read_commands_config()
        if conditions:
            data["functions"][key][index]["conditions"] = conditions
        else:
            data["functions"][key][index].pop("conditions", None)
        write_commands_config(data)

    conditions_menu(
        self,
        player,
        conditions,
        persist,
        back=lambda: execution_menu(self, player, command, index),
        body_key="ui.body.line_conditions_help",
    )


### COOLDOWN & CONDITIONS ###


def set_cooldown(self: Plugin, player: Player, command):
    form = ModalFormData()
    form.title(t("ui.title.set_cooldown"))
    current = str(command.get("cooldown", 0))
    form.text_field(t("ui.field.cooldown_seconds"), "0", current)

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command):
        if result.canceled:
            return edit_command(self, player, command)
        value = str(result.formValues[0]).strip() or "0"
        if not value.isdigit() or int(value) > MAX_COOLDOWN:
            error_custom(player, t("err.cooldown_invalid", max=MAX_COOLDOWN))
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
    """Conditions of the whole command (saved with Submit)."""
    command.setdefault("conditions", [])
    conditions_menu(
        self,
        player,
        command["conditions"],
        persist=lambda: None,
        back=lambda: edit_command(self, player, command),
        body_key="ui.body.conditions_help",
    )


def conditions_menu(self: Plugin, player: Player, conditions, persist, back, body_key):
    """
    Edits `conditions` in place. `persist()` is called after every change and `back()`
    after closing the menu: this lets the same screens serve a whole command and a line.
    """
    form = ActionFormData()
    form.title(t("ui.title.manage_conditions"))
    form.body(t(body_key))
    form.button(t("ui.button.add_condition"), "textures/ui/smithing-table-plus.png")
    form.button(t("ui.button.remove_condition"), "textures/ui/dark_minus.png")
    for condition in conditions:
        form.button(condition_line(condition))

    def again():
        conditions_menu(self, player, conditions, persist, back, body_key)

    def submit(self: Plugin, player: Player, result: ActionFormResponse):
        if result.canceled:
            return back()
        if result.selection == 0:
            add_condition(self, player, conditions, persist, again)
        elif result.selection == 1:
            remove_condition(self, player, conditions, persist, again)
        else:
            edit_condition(self, player, conditions, result.selection - 2, persist, again)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response
        )
    )


def add_condition(self: Plugin, player: Player, conditions, persist, again):
    types = ConditionTypes.get_types()
    form = ModalFormData()
    form.title(t("ui.title.add_condition"))
    form.dropdown(t("ui.field.type"), types)
    form.text_field(t("ui.field.condition_content"), "{score:kills} >= 5")
    form.text_field(t("ui.field.condition_message"), t("ui.hint.condition_message"))

    def submit(self: Plugin, player: Player, result: ModalFormResponse):
        if result.canceled:
            return again()
        condition = {
            "type": types[result.formValues[0]],
            "content": str(result.formValues[1]).strip(),
            "message": str(result.formValues[2]).strip(),
        }
        error = validate_condition(condition)
        if error:
            error_custom(player, error)
        else:
            conditions.append(condition)
            persist()
        again()

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(self, player, response)
    )


def remove_condition(self: Plugin, player: Player, conditions, persist, again):
    if not conditions:
        return again()
    form = ActionFormData()
    form.title(t("ui.title.remove_condition"))
    form.body(t("ui.body.click_a_condition_to_remove_it"))
    for condition in conditions:
        form.button(condition_line(condition))

    def submit(self: Plugin, player: Player, result: ActionFormResponse):
        if result.canceled:
            return again()
        conditions.pop(result.selection)
        persist()
        again()

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response
        )
    )


def edit_condition(self: Plugin, player: Player, conditions, index, persist, again):
    condition = conditions[index]
    form = ModalFormData()
    form.title(t("ui.title.edit_condition", type=condition["type"]))
    form.text_field(t("ui.field.content"), condition["content"], condition["content"])
    form.text_field(
        t("ui.field.condition_message"),
        t("ui.hint.condition_message"),
        condition.get("message", ""),
    )

    def submit(self: Plugin, player: Player, result: ModalFormResponse):
        if result.canceled:
            return again()
        updated = {
            "type": conditions[index]["type"],
            "content": str(result.formValues[0]).strip(),
            "message": str(result.formValues[1]).strip(),
        }
        error = validate_condition(updated)
        if error:
            error_custom(player, error)
        else:
            conditions[index] = updated
            persist()
        again()

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(self, player, response)
    )


### ARGUMENT RULES ###


def rule_line(rule) -> str:
    if rule["type"] == "choices":
        return strip_color_codes(
            t("ui.line.rule_choices", n=rule["index"] + 1, values=", ".join(rule["values"]))
        )
    return t("ui.line.rule_range", n=rule["index"] + 1, min=rule["min"], max=rule["max"])


def _number(text: str):
    """'5' -> 5, '2.5' -> 2.5, anything else -> None."""
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return None


def manage_arguments(self: Plugin, player: Player, command):
    command.setdefault("arguments", [])
    form = ActionFormData()
    form.title(t("ui.title.manage_arguments"))
    form.body(t("ui.body.arguments_help"))
    form.button(t("ui.button.add_rule"), "textures/ui/smithing-table-plus.png")
    form.button(t("ui.button.remove_rule"), "textures/ui/dark_minus.png")
    for rule in command["arguments"]:
        form.button(rule_line(rule))

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if result.canceled:
            return edit_command(self, player, command)
        if result.selection == 0:
            add_argument_rule(self, player, command)
        elif result.selection == 1:
            remove_argument_rule(self, player, command)
        else:
            edit_argument_rule(self, player, command, result.selection - 2)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def add_argument_rule(self: Plugin, player: Player, command):
    form = ModalFormData()
    form.title(t("ui.title.add_rule"))
    form.dropdown(
        t("ui.field.rule_type"), [t("ui.option.rule_choices"), t("ui.option.rule_range")]
    )
    form.text_field(t("ui.field.rule_number"), "1", "1")
    form.text_field(t("ui.field.rule_choices"), "diamond, emerald")
    form.text_field(t("ui.field.rule_min"), "1")
    form.text_field(t("ui.field.rule_max"), "16")
    form.text_field(t("ui.field.rule_message"), t("ui.hint.rule_message"))

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command):
        if result.canceled:
            return manage_arguments(self, player, command)
        kind, number, choices, low, high, message = result.formValues
        digits = str(number).strip()
        rule = {
            "index": int(digits) - 1 if digits.isdigit() else -1,
            "type": "choices" if kind == 0 else "range",
        }
        if kind == 0:
            rule["values"] = [v.strip() for v in str(choices).split(",") if v.strip()]
        else:
            rule["min"], rule["max"] = _number(str(low).strip()), _number(str(high).strip())
        if str(message).strip():
            rule["message"] = str(message).strip()
        error = validate_argument_rule(rule)
        if error:
            error_custom(player, error)
        else:
            command["arguments"].append(rule)
        manage_arguments(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command
        )
    )


def remove_argument_rule(self: Plugin, player: Player, command):
    if not command["arguments"]:
        return manage_arguments(self, player, command)
    form = ActionFormData()
    form.title(t("ui.title.remove_rule"))
    form.body(t("ui.body.click_a_rule_to_remove_it"))
    for rule in command["arguments"]:
        form.button(rule_line(rule))

    def submit(self: Plugin, player: Player, result: ActionFormResponse, command):
        if not result.canceled:
            command["arguments"].pop(result.selection)
        manage_arguments(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response, command
        )
    )


def edit_argument_rule(self: Plugin, player: Player, command, index):
    rule = command["arguments"][index]
    form = ModalFormData()
    form.title(t("ui.title.edit_rule"))
    form.text_field(t("ui.field.rule_number"), "1", str(rule["index"] + 1))
    if rule["type"] == "choices":
        form.text_field(t("ui.field.rule_choices"), "diamond, emerald", ", ".join(rule["values"]))
    else:
        form.text_field(t("ui.field.rule_min"), "1", str(rule["min"]))
        form.text_field(t("ui.field.rule_max"), "16", str(rule["max"]))
    form.text_field(t("ui.field.rule_message"), t("ui.hint.rule_message"), rule.get("message", ""))

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command, index):
        if result.canceled:
            return manage_arguments(self, player, command)
        old = command["arguments"][index]
        digits = str(result.formValues[0]).strip()
        updated = {
            "index": int(digits) - 1 if digits.isdigit() else -1,
            "type": old["type"],
        }
        if old["type"] == "choices":
            updated["values"] = [
                v.strip() for v in str(result.formValues[1]).split(",") if v.strip()
            ]
        else:
            updated["min"] = _number(str(result.formValues[1]).strip())
            updated["max"] = _number(str(result.formValues[2]).strip())
        message = str(result.formValues[-1]).strip()
        if message:
            updated["message"] = message
        error = validate_argument_rule(updated)
        if error:
            error_custom(player, error)
        else:
            command["arguments"][index] = updated
        manage_arguments(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command, index
        )
    )


### USAGE LIMIT ###


def set_usage_limit(self: Plugin, player: Player, command):
    limit = command.get("limit") or {}
    form = ModalFormData()
    form.title(t("ui.title.set_usage_limit"))
    form.text_field(t("ui.field.limit_uses"), "0", str(limit.get("uses", 0)))
    form.text_field(t("ui.field.limit_period"), "0", str(limit.get("period", 0)))

    def submit(self: Plugin, player: Player, result: ModalFormResponse, command):
        if result.canceled:
            return edit_command(self, player, command)
        uses = str(result.formValues[0]).strip() or "0"
        period = str(result.formValues[1]).strip() or "0"
        if not uses.isdigit() or not period.isdigit():
            error_custom(player, validate_limit(None))
        elif int(uses) == 0:
            command.pop("limit", None)
        else:
            new_limit = {"uses": int(uses), "period": int(period)}
            error = validate_limit(new_limit)
            if error:
                error_custom(player, error)
            else:
                command["limit"] = new_limit
        edit_command(self, player, command)

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(
            self, player, response, command
        )
    )


def reset_usage_counts(self: Plugin, player: Player, command):
    if require_manager(player):
        USAGE.reset(command["_original_name"])
        send_custom(player, t("msg.usage_reset", name=command["_original_name"]))
    edit_command(self, player, command)
