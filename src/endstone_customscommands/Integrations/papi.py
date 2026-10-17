"""
Optional integration with PlaceholderAPI for Endstone (plugin "papi", soft dependency).

When it is installed, placeholders written {identifier:params} that CustomsCommands doesn't
know are resolved through PlaceholderAPI, for example {vault:balance} in an execution or
in an expression condition. Anything PlaceholderAPI can't resolve is left as written.

The values still go through the same validation as every other placeholder.
"""

from ..Utils.render import add_external_resolver
from ..Utils.utils import read_commands_config
from . import registry

ID = "papi"
PLUGIN_NAME = "papi"  # for soft_depend

registry.declare(ID, "PlaceholderAPI")


def enable(plugin) -> bool:
    """Connects to PlaceholderAPI if it is installed. Returns True when it is active."""
    if not read_commands_config()["settings"]["integrations"][ID]["enabled"]:
        registry.set_state(ID, "disabled")
        return False
    try:
        from endstone_papi import PlaceholderAPI
    except ImportError:
        registry.set_state(ID, "missing")
        return False
    try:
        service = PlaceholderAPI.load(plugin.server.service_manager)
    except Exception as e:  # the service can't be loaded: keep running without it
        plugin.logger.warning(f"PlaceholderAPI integration disabled: {e}")
        registry.set_state(ID, "error", str(e))
        return False
    if service is None or not getattr(service, "active", False):
        registry.set_state(ID, "missing")
        return False
    parse = getattr(service, "set_placeholders", None)
    if parse is None:
        plugin.logger.warning(
            "PlaceholderAPI integration disabled: this version has no set_placeholders()."
        )
        registry.set_state(ID, "error", "no set_placeholders()")
        return False

    def resolve(player, key: str):
        text = "{" + key + "}"
        result = parse(player, text)
        return None if result == text else result  # unresolved placeholders stay as is

    add_external_resolver(resolve)
    registry.set_state(ID, "active")
    plugin.logger.info("PlaceholderAPI found: {identifier:params} placeholders are available.")
    return True
