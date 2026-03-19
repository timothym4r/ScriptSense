import re

TITLE_PREFIXES = {"MR", "MRS", "MS", "MISS", "DR", "SGT", "LT", "CAPT", "CAPTAIN"}


def normalize_character_name(text: str) -> str:
    stripped = re.sub(r"\s+", " ", text.strip())
    stripped = stripped.replace("’", "'")
    stripped = re.sub(r"[^A-Za-z0-9'. ]+", "", stripped)
    return stripped.upper().strip()


def derive_alias_variants(text: str) -> list[str]:
    normalized = normalize_character_name(text)
    if not normalized:
        return []

    aliases = {normalized}
    tokens = normalized.replace(".", "").split()
    if tokens and tokens[0] in TITLE_PREFIXES and len(tokens) > 1:
        aliases.add(" ".join(tokens[1:]))
        aliases.add(tokens[-1])
    elif len(tokens) > 1:
        aliases.add(tokens[-1])

    aliases.update(token for token in tokens if len(token) > 1)
    return sorted(alias for alias in aliases if alias)
