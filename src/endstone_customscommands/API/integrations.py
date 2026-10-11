import os
import zipfile
import importlib.util
from endstone._internal.endstone_python import ColorFormat
from endstone.plugin import Plugin
from .types import ExecutionTypes, PlaceholderTypes
from ..Utils.utils import BUILTIN_COMMANDS, read_commands_config, write_commands_config
from ..Utils.security import migrate_permission, validate_command


### API HANDLER ###

# Define paths
plugins_file_path = os.path.abspath("./plugins/")
extraction_base_path = os.path.join(
    os.getcwd(), "plugins", ".processes", "CustomsCommands"
)


def _is_safe_member(base: str, member: str) -> bool:
    """True if extracting `member` stays inside `base`."""
    target = os.path.abspath(os.path.join(base, member))
    return target == os.path.abspath(base) or target.startswith(
        os.path.abspath(base) + os.sep
    )


class APIHandler:
    def discover_integrations(self: Plugin):
        self.logger.info("§b§lDiscovering integrations...")

        # Check if directory exists; if not, create it.
        if not os.path.exists(extraction_base_path):
            os.makedirs(extraction_base_path)

        # Iterate through plugins.
        success = ""
        successes = 0
        for file_name in os.listdir(plugins_file_path):
            if file_name.endswith(".whl") and file_name.startswith("endstone_"):
                plugin_name = file_name.split("_")[1].split("-")[0]
                try:
                    wheel_file_path = os.path.join(plugins_file_path, file_name)

                    with zipfile.ZipFile(wheel_file_path, "r") as whl:
                        if not all(
                            _is_safe_member(extraction_base_path, n)
                            for n in whl.namelist()
                        ):
                            self.logger.warning(
                                f"Skipping {file_name}: unsafe paths in archive."
                            )
                            continue
                        # Extract plugin contents.
                        whl.extractall(extraction_base_path)

                    extracted_folders = [
                        folder
                        for folder in os.listdir(extraction_base_path)
                        if not folder.endswith(".dist-info")
                    ]
                    if not extracted_folders:
                        continue

                    # Use the first valid folder
                    valid_folder = os.path.join(
                        extraction_base_path, extracted_folders[0]
                    )
                    # Locate __init__.py
                    init_file_path = os.path.join(valid_folder, "__init__.py")
                    if not os.path.exists(init_file_path):
                        continue

                    # Find module name from __init__.py
                    with open(init_file_path, "r") as f:
                        lines = f.readlines()
                    module_name = None
                    for line in lines:
                        if line.startswith("from ") and " import " in line:
                            module_name = line.split()[1].split(".")[1]
                            break
                    if not module_name:
                        continue

                    # Find module path
                    module_file_path = os.path.join(valid_folder, f"{module_name}.py")
                    if not os.path.exists(module_file_path):
                        continue

                    # Process module
                    # self.logger.info("Processing plugin module: " + module_name)
                    with open(module_file_path, "r") as f:
                        lines = f.readlines()

                    # Search for the CommandManager class in the first 100 lines
                    class_name = None
                    for i, line in enumerate(lines):
                        if i >= 100:
                            break
                        if "class " in line and "(CommandManager)" in line:
                            class_name = line.split()[1].split("(")[0]
                            break
                    if not class_name:
                        continue

                    # Import
                    relative_folder = os.path.relpath(
                        valid_folder, extraction_base_path
                    )
                    package_name = relative_folder.replace(os.sep, ".")
                    spec = importlib.util.spec_from_file_location(
                        f"{package_name}.{module_name}", module_file_path
                    )
                    module = importlib.util.module_from_spec(spec)
                    module.__package__ = package_name
                    spec.loader.exec_module(module)

                    # Initialize class
                    command_manager_class = getattr(module, class_name)
                    command_manager = command_manager_class()

                    # Call integrations

                    # Sort Commands
                    for command in command_manager._commands:
                        try:
                            commandData = read_commands_config()
                            command.permissions = [
                                migrate_permission(p) for p in command.permissions
                            ]
                            error = validate_command(
                                {
                                    "name": command.name,
                                    "description": command.description,
                                    "usages": command.usages,
                                    "aliases": command.aliases,
                                    "permissions": command.permissions,
                                },
                                commandData["commands"],
                                BUILTIN_COMMANDS,
                                original_name=command.name,
                            )
                            if error:
                                raise ValueError(error)
                            if not command.name in commandData["commands"]:
                                commandData["commands"][command.name] = {
                                    "description": command.description,
                                    "usages": command.usages,
                                    "permissions": command.permissions,
                                    "aliases": command.aliases,
                                }
                            else:
                                commandData["commands"][command.name][
                                    "usages"
                                ] = command.usages
                            if len(command.functionality) > 0:
                                if not command.name in commandData["functions"]:
                                    commandData["functions"][command.name] = []
                                    for functionality in command.functionality:
                                        commandData["functions"][command.name].append(
                                            {
                                                "type": functionality["type"],
                                                "content": functionality["content"],
                                            }
                                        )
                            write_commands_config(commandData)
                            success += f"\n    §8> {ColorFormat.YELLOW}Command §8-> §9{command.name} §rfrom §d{plugin_name}"
                            successes += 1
                        except Exception as e:
                            self.logger.error(f"Failed to register command: {e}")

                    # Sort Executions
                    for execution in command_manager._executions:
                        try:
                            ExecutionTypes.executions.append(execution)
                            success += f"\n    §8> {ColorFormat.MATERIAL_AMETHYST}Execution Type §8-> §9{execution.name if execution else '?'} §rfrom §d{plugin_name}"
                            successes += 1
                        except Exception as e:
                            self.logger.error(f"Failed to register execution: {e}")

                    # Sort Placeholders
                    for placeholder in command_manager._placeholders:
                        try:
                            PlaceholderTypes.placeholders.append(placeholder)
                            success += f"\n    §8> {ColorFormat.GOLD}Placeholder §8-> §9{placeholder.id if placeholder else '?'} §rfrom §d{plugin_name}"
                            successes += 1
                        except Exception as e:
                            self.logger.error(f"Failed to register placeholder: {e}")
                except Exception as e:
                    self.logger.warning(f"Skipped {file_name}: {e}")
                finally:
                    # Clean up directory
                    for root, dirs, files in os.walk(
                        extraction_base_path, topdown=False
                    ):
                        for name in files:
                            os.remove(os.path.join(root, name))
                        for name in dirs:
                            os.rmdir(os.path.join(root, name))
        self.logger.info(
            f"\n§9[CC]§r §aSuccessful Registrations §8(§c{successes}§8):§r" + success
        )
