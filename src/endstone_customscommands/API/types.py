import types

from endstone._internal.endstone_python import Player


class ExecutionTypes:
    executions = []

    @staticmethod
    def register(name: str, callback):
        """Registers an execution type (callback(player, content, args))."""
        if not isinstance(name, str) or not name or name == "command":
            raise ValueError("Invalid execution type name.")
        if name in ExecutionTypes.get_types():
            raise ValueError(f"Execution type '{name}' is already registered.")
        ExecutionTypes.executions.append(
            types.SimpleNamespace(name=name, callback=callback)
        )

    @staticmethod
    def get_types():
        types = []
        for execution in ExecutionTypes.executions:
            types.append(execution.name)
        return types

    @staticmethod
    def get_execution(
        name,
    ):
        for execution in ExecutionTypes.executions:
            if execution.name == name:
                return execution.callback
        return None


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
            or "{" in identifier
            or "}" in identifier
        ):
            raise ValueError("Invalid placeholder identifier.")
        if identifier in PlaceholderTypes.get_types():
            raise ValueError(f"Placeholder '{identifier}' is already registered.")
        PlaceholderTypes.placeholders.append(
            types.SimpleNamespace(id=identifier, callback=callback)
        )

    @staticmethod
    def get_types():
        types = []
        for placeholder in PlaceholderTypes.placeholders:
            types.append(placeholder.id)
        return types

    @staticmethod
    def get_placeholder(
        id,
    ):
        for placeholder in PlaceholderTypes.placeholders:
            if placeholder.id == id:
                return placeholder.callback
        return None


class ConditionTypes:
    conditions = []

    @staticmethod
    def get_types():
        types = []
        for condition in ConditionTypes.conditions:
            types.append(condition.name)
        return types

    @staticmethod
    def get_condition(
        name,
    ):
        for condition in ConditionTypes.conditions:
            if condition.name == name:
                return condition.callback
        return None
