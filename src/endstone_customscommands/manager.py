import math

from .Utils.lang import t
from .compat import Player

from .form_wrapper import (
    ActionFormData,
    ActionFormResponse,
    MessageFormData,
    MessageFormResponse,
    ModalFormData,
    ModalFormResponse,
)
from .Manage.add import add_command
from .Manage.edit import edit_command
from .API.types import ExecutionTypes
from .Utils import transfer
from .Integrations import registry
from .Utils.utils import (
    BUILTIN_COMMANDS,
    backup_commands,
    read_commands_config,
    write_commands_config,
    send_custom,
    error_custom,
    require_manager,
)

from endstone.plugin import Plugin

### COMMAND MANAGER FUNCTIONALITY ###

ICON_ADD = "textures/ui/smithing-table-plus.png"
ICON_REMOVE = "textures/ui/dark_minus.png"
ICON_COMMAND = "textures/ui/user_icon_white.png"
MAX_REPORTED_ERRORS = 5


def editable_commands(commandData):
    """Commands shown in the manager (the plugin's own commands are hidden)."""
    return {
        name: cmd
        for name, cmd in commandData["commands"].items()
        if name not in BUILTIN_COMMANDS
    }


def filter_names(commands: dict, query: str) -> list:
    """Names of the commands whose name or description contains `query`."""
    query = query.strip().lower()
    if not query:
        return list(commands)
    return [
        name
        for name, command in commands.items()
        if query in name.lower() or query in str(command.get("description", "")).lower()
    ]


def page_window(total: int, page: int, size: int):
    """(page, pages, start, end) with the page clamped to a valid one."""
    pages = max(1, math.ceil(total / size))
    page = min(max(page, 0), pages - 1)
    return page, pages, page * size, page * size + size


def editor_payload(name: str, command: dict) -> dict:
    """The data shown in the editor. Lists are copied: cancelling an edit changes nothing."""
    return {
        "name": name,
        "_original_name": name,
        "description": command["description"],
        "usages": list(command["usages"]),
        "aliases": list(command["aliases"]),
        "permissions": list(command["permissions"]),
        "cooldown": command.get("cooldown", 0),
        "conditions": [dict(c) for c in command.get("conditions", [])],
        "arguments": [dict(r) for r in command.get("arguments", [])],
        "limit": dict(command["limit"]) if command.get("limit") else None,
    }


def command_manager(self: Plugin, player: Player, page: int = 0, query: str = ""):
    if not require_manager(player):
        return
    commandData = read_commands_config()
    commands = editable_commands(commandData)
    names = filter_names(commands, query)
    page, pages, start, end = page_window(
        len(names), page, commandData["settings"]["page_size"]
    )

    actions = [("add",), ("remove",), ("search",), ("transfer",), ("dependencies",)]
    if page > 0:
        actions.append(("previous",))
    if page < pages - 1:
        actions.append(("next",))
    actions += [("command", name) for name in names[start:end]]

    form = ActionFormData()
    form.title(t("ui.title.command_manager"))
    body = t("ui.body.manager_page", page=page + 1, pages=pages, count=len(names))
    if query.strip():
        body += "\n" + t("ui.body.manager_filter", query=query.strip())
    form.body(body)
    for action in actions:
        if action[0] == "add":
            form.button(t("ui.button.add_command"), ICON_ADD)
        elif action[0] == "remove":
            form.button(t("ui.button.remove_command"), ICON_REMOVE)
        elif action[0] == "search":
            form.button(t("ui.button.search"))
        elif action[0] == "transfer":
            form.button(t("ui.button.export_import"))
        elif action[0] == "dependencies":
            form.button(t("ui.button.dependencies"))
        elif action[0] == "previous":
            form.button(t("ui.button.previous_page"))
        elif action[0] == "next":
            form.button(t("ui.button.next_page"))
        else:
            form.button(
                f"{action[1]}\n{commands[action[1]]['description']}", ICON_COMMAND
            )

    def submit(self: Plugin, player: Player, result: ActionFormResponse):
        if result.canceled:
            return
        action = actions[result.selection]
        if action[0] == "add":
            add_command(
                self,
                player,
                {
                    "usages": [],
                    "aliases": [],
                    "permissions": [],
                    "cooldown": 0,
                    "conditions": [],
                    "arguments": [],
                    "limit": None,
                },
            )
        elif action[0] == "remove":
            remove_command(self, player)
        elif action[0] == "search":
            search_commands(self, player, query)
        elif action[0] == "transfer":
            transfer_menu(self, player)
        elif action[0] == "dependencies":
            dependencies_menu(self, player)
        elif action[0] == "previous":
            command_manager(self, player, page - 1, query)
        elif action[0] == "next":
            command_manager(self, player, page + 1, query)
        else:
            edit_command(self, player, editor_payload(action[1], commands[action[1]]))

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response
        )
    )


def search_commands(self: Plugin, player: Player, query: str):
    form = ModalFormData()
    form.title(t("ui.title.search"))
    form.text_field(t("ui.field.search"), "", query)

    def submit(self: Plugin, player: Player, result: ModalFormResponse):
        if result.canceled:
            return command_manager(self, player, 0, query)
        command_manager(self, player, 0, str(result.formValues[0]).strip())

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(self, player, response)
    )


def remove_command(self: Plugin, player: Player, page: int = 0):
    commandData = read_commands_config()
    commands = editable_commands(commandData)
    names = list(commands.keys())
    page, pages, start, end = page_window(
        len(names), page, commandData["settings"]["page_size"]
    )
    actions = []
    if page > 0:
        actions.append(("previous",))
    if page < pages - 1:
        actions.append(("next",))
    actions += [("command", name) for name in names[start:end]]

    form = ActionFormData()
    form.title(t("ui.title.remove_command"))
    form.body(t("ui.body.click_a_command_to_remove_it"))
    for action in actions:
        if action[0] == "previous":
            form.button(t("ui.button.previous_page"))
        elif action[0] == "next":
            form.button(t("ui.button.next_page"))
        else:
            form.button(
                f"{action[1]}\n§7{commands[action[1]]['description']}", ICON_COMMAND
            )

    def submit(self: Plugin, player: Player, result: ActionFormResponse):
        if result.canceled:
            return
        action = actions[result.selection]
        if action[0] == "previous":
            remove_command(self, player, page - 1)
        elif action[0] == "next":
            remove_command(self, player, page + 1)
        else:
            confirm_remove_command(self, player, action[1])

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response
        )
    )


def confirm_remove_command(self: Plugin, player: Player, command_name: str):
    form = MessageFormData()
    form.title(t("ui.title.confirm_removal"))
    form.body(t("ui.body.confirm_remove", name=command_name))
    form.button1(t("ui.button.yes"))
    form.button2(t("ui.button.no"))

    def do_remove(self: Plugin, player: Player, result: MessageFormResponse, name):
        # button1 ("Yes") -> 0, button2 ("No") -> 1
        if result.canceled or result.selection != 0:
            return
        if not require_manager(player):
            return
        commandData = read_commands_config()
        commandData["commands"].pop(name, None)
        commandData["functions"].pop(name, None)
        write_commands_config(commandData)
        send_custom(player, t("msg.command_removed", name=name))
        try:
            self.server.reload()
        except Exception as e:
            error_custom(player, t("err.reload_failed", error=e))

    form.show(player).then(
        lambda player=Player, response=MessageFormResponse: do_remove(
            self, player, response, command_name
        )
    )


### DEPENDENCIES ###

STATE_KEYS = {
    "active": "dep.state.active",
    "missing": "dep.state.missing",
    "disabled": "dep.state.disabled",
    "error": "dep.state.error",
}
DESCRIPTION_KEYS = {
    "papi": "dep.papi.description",
    "stoneperms": "dep.stoneperms.description",
    "mediaplayer": "dep.mediaplayer.description",
}


def dependencies_menu(self: Plugin, player: Player):
    """Status of the optional plugins CustomsCommands works with."""
    lines = [t("ui.body.dependencies_intro")]
    for integration_id, info in registry.INTEGRATIONS.items():
        lines.append(
            t("ui.line.dependency", name=info["title"], state=t(STATE_KEYS[info["state"]]))
        )
        if integration_id in DESCRIPTION_KEYS:
            lines.append("§7" + t(DESCRIPTION_KEYS[integration_id]))
        types = registry.types_of(integration_id)
        if info["state"] == "active" and types:
            lines.append(t("ui.line.dependency_types", types=", ".join(types)))
        if info["detail"]:
            lines.append("§7" + info["detail"])
        lines.append("")
    form = ActionFormData()
    form.title(t("ui.title.dependencies"))
    form.body("\n".join(lines))
    form.button(t("ui.button.back"))

    def submit(self: Plugin, player: Player, result: ActionFormResponse):
        command_manager(self, player)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(self, player, response)
    )


### EXPORT / IMPORT ###


def transfer_menu(self: Plugin, player: Player):
    form = ActionFormData()
    form.title(t("ui.title.transfer"))
    form.body(t("ui.body.transfer"))
    form.button(t("ui.button.export_all"))
    form.button(t("ui.button.import_commands"))

    def submit(self: Plugin, player: Player, result: ActionFormResponse):
        if result.canceled:
            return command_manager(self, player)
        if result.selection == 0:
            export_commands(self, player)
        else:
            import_files_menu(self, player)

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response
        )
    )


def export_commands(self: Plugin, player: Player):
    if not require_manager(player):
        return
    try:
        name = transfer.export_all()
    except OSError as e:
        error_custom(player, t("err.export_failed", error=e))
    else:
        send_custom(player, t("msg.exported", file=f"exports/{name}"))
    command_manager(self, player)


def import_files_menu(self: Plugin, player: Player, page: int = 0):
    files = transfer.list_files()
    if not files:
        error_custom(player, t("err.no_import_files"))
        return transfer_menu(self, player)
    size = read_commands_config()["settings"]["page_size"]
    page, pages, start, end = page_window(len(files), page, size)
    actions = []
    if page > 0:
        actions.append(("previous",))
    if page < pages - 1:
        actions.append(("next",))
    actions += [("file", name) for name in files[start:end]]

    form = ActionFormData()
    form.title(t("ui.title.import_files"))
    form.body(t("ui.body.import_files"))
    for action in actions:
        if action[0] == "previous":
            form.button(t("ui.button.previous_page"))
        elif action[0] == "next":
            form.button(t("ui.button.next_page"))
        else:
            form.button(action[1])

    def submit(self: Plugin, player: Player, result: ActionFormResponse):
        if result.canceled:
            return transfer_menu(self, player)
        action = actions[result.selection]
        if action[0] == "previous":
            import_files_menu(self, player, page - 1)
        elif action[0] == "next":
            import_files_menu(self, player, page + 1)
        else:
            import_options(self, player, action[1])

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response
        )
    )


def import_options(self: Plugin, player: Player, file_name: str):
    form = ModalFormData()
    form.title(t("ui.title.import_options", file=file_name))
    form.dropdown(
        t("ui.field.import_mode"),
        [
            t("ui.option.import_add"),
            t("ui.option.import_overwrite"),
            t("ui.option.import_replace"),
        ],
    )

    def submit(self: Plugin, player: Player, result: ModalFormResponse):
        if result.canceled:
            return import_files_menu(self, player)
        perform_import(self, player, file_name, transfer.MODES[result.formValues[0]])

    form.show(player).then(
        lambda player=Player, response=ModalFormResponse: submit(self, player, response)
    )


def perform_import(self: Plugin, player: Player, file_name: str, mode: str):
    if not require_manager(player):
        return
    try:
        raw = transfer.read_file(file_name)
    except transfer.TransferError as e:
        error_custom(player, str(e))
        return
    current = read_commands_config()
    plan = transfer.plan_import(current, raw, mode, ExecutionTypes.get_types())
    for name, reason in plan["skipped"][:MAX_REPORTED_ERRORS]:
        send_custom(player, t("msg.import_skipped_line", name=name, reason=reason))
    if not plan["imported"]:
        error_custom(player, t("err.nothing_imported", skipped=len(plan["skipped"])))
        return
    backup_commands("import")  # the previous state can be restored from backups/
    current["commands"], current["functions"] = plan["commands"], plan["functions"]
    write_commands_config(current)
    send_custom(
        player,
        t("msg.import_done", imported=len(plan["imported"]), skipped=len(plan["skipped"])),
    )
    try:
        self.server.reload()
    except Exception as e:
        error_custom(player, t("err.reload_failed", error=e))
