from types import SimpleNamespace

from ..compat import Player


class ExecutionTypes:
    """
    Execution types usable in a command's functionality.

    An entry has: name, callback(player, content, args), and optional attributes:
    - strict: validate player input as a server command (see Utils/security.py).
    - strip_formatting: remove '§' formatting codes from inserted values.
    - hint: example content shown in the editor.
    Entries added by the legacy discovery may only have name/callback.
    """

    executions = []

    @staticmethod
    def register(
        name: str,
        callback,
        strict: bool = False,
        strip_formatting: bool = False,
        hint: str = "",
    ):
        """Registers an execution type (callback(player, content, args))."""
        if not isinstance(name, str) or not name or name == "command":
            raise ValueError("Invalid execution type name.")
        if name in ExecutionTypes.get_types():
            raise ValueError(f"Execution type '{name}' is already registered.")
        ExecutionTypes.executions.append(
            SimpleNamespace(
                name=name,
                callback=callback,
                strict=strict,
                strip_formatting=strip_formatting,
                hint=hint,
            )
        )

    @staticmethod
    def get_types():
        return [execution.name for execution in ExecutionTypes.executions]

    @staticmethod
    def _find(name):
        for execution in ExecutionTypes.executions:
            if execution.name == name:
                return execution
        return None

    @staticmethod
    def get_execution(
        name,
    ):
        execution = ExecutionTypes._find(name)
        return execution.callback if execution else None

    @staticmethod
    def is_strict(name) -> bool:
        """Server commands are always validated strictly."""
        if name == "command":
            return True
        execution = ExecutionTypes._find(name)
        return bool(getattr(execution, "strict", False))

    @staticmethod
    def strips_formatting(name) -> bool:
        execution = ExecutionTypes._find(name)
        return bool(getattr(execution, "strip_formatting", False))

    @staticmethod
    def get_hint(name) -> str:
        if name == "command":
            return "say Hello, {0} {1}!"
        execution = ExecutionTypes._find(name)
        return getattr(execution, "hint", "") or "{0} {1}"


class PlaceholderTypes:
    placeholders = []

    @staticmethod
    def register(identifier: str, callback):
        """Registers a placeholder {identifier} (callback(player, args) -> str)."""
        if (
            not isinstance(identifier, str)
            or not identifier
            or identifier == "player"
            or identifier.isdigit()
            or identifier.startswith("score:")
            or identifier.startswith("random:")
            or "{" in identifier
            or "}" in identifier
        ):
            raise ValueError("Invalid placeholder identifier.")
        if identifier in PlaceholderTypes.get_types():
            raise ValueError(f"Placeholder '{identifier}' is already registered.")
        PlaceholderTypes.placeholders.append(
            SimpleNamespace(id=identifier, callback=callback)
        )

    @staticmethod
    def get_types():
        return [placeholder.id for placeholder in PlaceholderTypes.placeholders]

    @staticmethod
    def get_placeholder(
        id,
    ):
        for placeholder in PlaceholderTypes.placeholders:
            if placeholder.id == id:
                return placeholder.callback
        return None


class ConditionTypes:
    """Conditions: callback(player, content, args) -> bool."""

    conditions = []

    @staticmethod
    def register(name: str, callback, hint: str = ""):
        if not isinstance(name, str) or not name:
            raise ValueError("Invalid condition type name.")
        if name in ConditionTypes.get_types():
            raise ValueError(f"Condition type '{name}' is already registered.")
        ConditionTypes.conditions.append(
            SimpleNamespace(name=name, callback=callback, hint=hint)
        )

    @staticmethod
    def get_types():
        return [condition.name for condition in ConditionTypes.conditions]

    @staticmethod
    def get_condition(
        name,
    ):
        for condition in ConditionTypes.conditions:
            if condition.name == name:
                return condition.callback
        return None

    @staticmethod
    def get_hint(name) -> str:
        for condition in ConditionTypes.conditions:
            if condition.name == name:
                return getattr(condition, "hint", "") or ""
        return ""
