"""Placeholder resolution shared by command execution and conditions."""

import random
import re

from .lang import t
from .security import InputError, PLACEHOLDER_RE, Unresolved, render_line
from ..API.types import PlaceholderTypes

MAX_RANDOM = 1_000_000_000

# Resolvers added by soft-dependency integrations: resolver(player, key) -> str | None.
# They are only asked about placeholders this plugin doesn't know ({identifier:params}).
EXTERNAL_RESOLVERS = []


def add_external_resolver(resolver) -> None:
    if resolver not in EXTERNAL_RESOLVERS:
        EXTERNAL_RESOLVERS.append(resolver)


def _ask_external(player, key: str) -> str:
    for resolver in EXTERNAL_RESOLVERS:
        try:
            value = resolver(player, key)
        except Exception:
            continue
        if value is not None:
            return str(value)
    raise Unresolved()


def replace_scores(player, string: str, warn=None) -> str:
    """Replaces {score:objective} with the player's score."""
    server = player.server
    for placeholder in re.findall(r"\{(.*?)\}", string):
        if placeholder.startswith("score:"):
            objective_name = placeholder.split(":", 1)[1]
            objective = server.scoreboard.get_objective(objective_name)
            if objective is None:
                if warn:
                    warn(f"Scoreboard objective '{objective_name}' does not exist.")
                continue
            value = objective.get_score(player).value
            string = re.sub(
                r"\{" + re.escape(placeholder) + r"\}", str(value), string
            )
    return string


def _random(key: str) -> str:
    parts = key.split(":")
    try:
        if len(parts) != 3:
            raise ValueError
        low, high = int(parts[1]), int(parts[2])
    except ValueError:
        raise InputError(t("err.random_invalid", placeholder="{" + key + "}"))
    if low > high or abs(low) > MAX_RANDOM or abs(high) > MAX_RANDOM:
        raise InputError(t("err.random_range", placeholder="{" + key + "}"))
    return str(random.randint(low, high))


def resolve_custom(player, args, template: str) -> dict:
    """{placeholder id: callable} for the registered placeholders used in `template`."""
    custom = {}
    registered = PlaceholderTypes.get_types()
    for key in set(PLACEHOLDER_RE.findall(template)):
        if key.startswith("random:"):
            custom[key] = lambda key=key: _random(key)
        elif key in registered:
            custom[key] = lambda key=key: PlaceholderTypes.get_placeholder(key)(
                player, args
            )
        elif EXTERNAL_RESOLVERS and ":" in key and not key.startswith("score:"):
            custom[key] = lambda key=key: _ask_external(player, key)
    return custom


def render_template(
    player,
    template: str,
    args,
    allow_selectors: bool = False,
    strict: bool = True,
    strip_formatting: bool = False,
    warn=None,
    check_start: bool = True,
) -> str:
    template = replace_scores(player, template, warn)
    return render_line(
        template,
        player.name,
        args,
        resolve_custom(player, args, template),
        allow_selectors=allow_selectors,
        strict=strict,
        strip_formatting=strip_formatting,
        check_start=check_start,
    )
