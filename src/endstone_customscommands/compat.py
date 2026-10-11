"""
Endstone imports that work across versions.

Recent Endstone versions removed the private `endstone._internal` module: the public
modules `endstone` and `endstone.form` are used first, and the old private module is
only a fallback for very old servers.
"""

try:
    from endstone import ColorFormat, Player
except ImportError:  # very old Endstone
    from endstone._internal.endstone_python import ColorFormat, Player

try:
    from endstone.form import (
        ActionForm,
        Dropdown,
        MessageForm,
        ModalForm,
        Slider,
        TextInput,
        Toggle,
    )
except ImportError:  # very old Endstone
    from endstone._internal.endstone_python import (
        ActionForm,
        Dropdown,
        MessageForm,
        ModalForm,
        Slider,
        TextInput,
        Toggle,
    )

__all__ = [
    "ActionForm",
    "ColorFormat",
    "Dropdown",
    "MessageForm",
    "ModalForm",
    "Player",
    "Slider",
    "TextInput",
    "Toggle",
]
