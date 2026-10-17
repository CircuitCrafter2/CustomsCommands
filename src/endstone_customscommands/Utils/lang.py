"""
Translations. Every message and every piece of UI text is a key (see lang/en_US.json).

Customising: edit plugins/customscommands/lang/en_US.json, or create another file
(e.g. fr_FR.json) and set "language" in config.json. Missing keys fall back to the
packaged English texts, so a language file can contain only the keys you changed.
"""

import json
import re
from pathlib import Path

from . import paths

DEFAULT_LANGUAGE = "en_US"
PACKAGED_DIR = Path(__file__).resolve().parent.parent / "lang"
_PARAM_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")

_messages: dict = {}
_language = None


def _read(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}


def packaged_messages(language: str = DEFAULT_LANGUAGE) -> dict:
    return _read(PACKAGED_DIR / f"{language}.json")


def ensure_default_file() -> None:
    """Writes lang/en_US.json in the data folder (once) so it can be customised."""
    target = paths.file("lang", f"{DEFAULT_LANGUAGE}.json")
    if target.exists():
        return
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(packaged_messages(), f, indent=4, ensure_ascii=False)
    except OSError:
        pass


def configure(language: str = DEFAULT_LANGUAGE) -> None:
    """(Re)loads the texts. Later sources override earlier ones."""
    global _messages, _language
    merged = packaged_messages(DEFAULT_LANGUAGE)
    if not merged:
        print(
            f"[CustomsCommands] Default language file not found in {PACKAGED_DIR}: "
            "texts will show as keys. Reinstall the plugin."
        )
    merged.update(_read(paths.file("lang", f"{DEFAULT_LANGUAGE}.json")))
    if language != DEFAULT_LANGUAGE:
        merged.update(packaged_messages(language))
        merged.update(_read(paths.file("lang", f"{language}.json")))
    _messages, _language = merged, language


def t(key: str, **params) -> str:
    """The text for `key`. `{name}` is replaced when `name` is given, otherwise kept."""
    if _language is None:
        configure()
    text = _messages.get(key)
    if text is None:
        return key  # visible, so a missing translation is easy to spot
    if not params:
        return text
    return _PARAM_RE.sub(
        lambda m: str(params[m.group(1)]) if m.group(1) in params else m.group(0), text
    )


def known_keys() -> set:
    return set(packaged_messages(DEFAULT_LANGUAGE))
