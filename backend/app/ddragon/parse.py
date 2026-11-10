"""Pretvorba Data Dragon JSON v podatke za tabeli champions in items.

Data Dragon ne pove, koliko CC, zdravljenja ali engage ima šampion. Osnovne ocene zato
izpeljemo iz Riotovih oznak (Tank, Mage ...), izrazite primere pa popravimo ročno v
champion_overrides.json. Administrator jih lahko kasneje ureja (US-14).
"""

import json
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from app.models.champion import RATED_ATTRIBUTES, RATING_MAX, RATING_MIN, DamageProfile

OVERRIDES_FILE = Path(__file__).parent / "champion_overrides.json"

# Ocene, ki jih da posamezna oznaka; stranska (druga) oznaka da eno točko manj.
TAG_RATINGS: dict[str, dict[str, int]] = {
    "Tank": {"tank": 3, "engage": 2, "cc": 2},
    "Fighter": {"tank": 1, "burst": 1},
    "Assassin": {"burst": 3},
    "Mage": {"burst": 2, "poke": 1, "cc": 1},
    "Marksman": {"poke": 1},
    "Support": {"cc": 1},
}

# Osnovne statistike za izračun moči po levelu (US-05); mana ni pomembna za primerjavo.
CHAMPION_STATS = (
    "hp",
    "hpperlevel",
    "armor",
    "armorperlevel",
    "spellblock",
    "spellblockperlevel",
    "attackdamage",
    "attackdamageperlevel",
    "attackspeed",
    "attackspeedperlevel",
    "attackrange",
    "movespeed",
    "hpregen",
    "hpregenperlevel",
)
SPELL_KEYS = ("Q", "W", "E", "R")
HTML_TAG = re.compile(r"<[^>]+>")
MAX_SPELL_DESCRIPTION = 400

# Razlika med info.attack in info.magic, od katere velja šampion za fizičnega/magičnega.
DAMAGE_PROFILE_MARGIN = 3

SUMMONERS_RIFT = "11"
# Šestmestni ID-ji so različice predmetov za druge načine igre (Arena, ARAM ...).
MAX_ITEM_ID = 10_000

ITEM_TAG_ALIASES = {"ArmorPenetration": "armor_pen", "MagicPenetration": "magic_pen"}
ANTI_HEAL_PATTERN = re.compile(r"\bWounds\b")
# Predmeti s temi oznakami niso del "dokončanega" builda (US-04).
NOT_COMPLETED_TAGS = frozenset({"Boots", "Consumable", "Trinket"})
# Cenejši "dokončani" predmeti so nadgradnje podpornih predmetov, čevlji in Mejai.
LEGENDARY_MIN_COST = 2000


@dataclass(frozen=True)
class ChampionData:
    id: int
    slug: str
    name: str
    damage_profile: DamageProfile
    ratings: dict[str, int]
    classes: list[str] = field(default_factory=list)
    stats: dict[str, float] = field(default_factory=dict)
    spells: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ItemData:
    id: int
    name: str
    cost: int
    tags: list[str]
    completed: bool = False


@cache
def load_overrides() -> dict[str, dict[str, int]]:
    return json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))


def parse_champions(
    data: dict[str, dict[str, Any]], overrides: dict[str, dict[str, int]] | None = None
) -> list[ChampionData]:
    """data je slovar "data" iz champion.json (ključ = slug)."""
    overrides = load_overrides() if overrides is None else overrides
    return [_parse_champion(raw, overrides.get(raw["id"], {})) for raw in data.values()]


def _parse_champion(raw: dict[str, Any], override: dict[str, int]) -> ChampionData:
    ratings = dict.fromkeys(RATED_ATTRIBUTES, RATING_MIN)
    for position, tag in enumerate(raw.get("tags", [])):
        for attribute, value in TAG_RATINGS.get(tag, {}).items():
            ratings[attribute] = max(ratings[attribute], value - min(position, 1))

    for attribute, value in override.items():
        valid = attribute in ratings and isinstance(value, int)
        if not valid or not RATING_MIN <= value <= RATING_MAX:
            raise ValueError(f"Neveljaven popravek za {raw['id']}: {attribute}={value!r}")
        ratings[attribute] = value

    return ChampionData(
        id=int(raw["key"]),
        slug=raw["id"],
        name=raw["name"],
        damage_profile=_damage_profile(raw["info"]),
        ratings=ratings,
        classes=list(raw.get("tags", [])),
        stats={k: float(v) for k, v in (raw.get("stats") or {}).items() if k in CHAMPION_STATS},
        spells=[
            _parse_spell(key, spell)
            for key, spell in zip(SPELL_KEYS, raw.get("spells") or [], strict=False)
        ],
    )


def _parse_spell(key: str, raw: dict[str, Any]) -> dict[str, Any]:
    """Sposobnost s tipko; opis brez HTML oznak (<br> postane presledek)."""
    text = HTML_TAG.sub(" ", str(raw.get("description", "")))
    return {
        "key": key,
        "name": str(raw["name"]),
        "description": " ".join(text.split())[:MAX_SPELL_DESCRIPTION],
        "cooldown": [float(c) if c % 1 else int(c) for c in raw.get("cooldown") or []],
    }


def _damage_profile(info: dict[str, int]) -> DamageProfile:
    difference = info["attack"] - info["magic"]
    if difference >= DAMAGE_PROFILE_MARGIN:
        return DamageProfile.PHYSICAL
    if difference <= -DAMAGE_PROFILE_MARGIN:
        return DamageProfile.MAGIC
    return DamageProfile.MIXED


def parse_items(data: dict[str, dict[str, Any]]) -> list[ItemData]:
    """data je slovar "data" iz item.json (ključ = ID); vrne predmete za Summoner's Rift."""
    return [
        ItemData(
            id=int(item_id),
            name=raw["name"],
            cost=raw["gold"]["total"],
            tags=_item_tags(raw),
            completed=_is_completed(raw),
        )
        for item_id, raw in data.items()
        if _is_summoners_rift_item(int(item_id), raw)
    ]


def _is_completed(raw: dict[str, Any]) -> bool:
    """Dokončan je legendarni predmet: sestavljen iz drugih, se ne gradi naprej, ni čevelj."""
    return (
        bool(raw.get("from"))
        and raw["gold"]["total"] >= LEGENDARY_MIN_COST
        and not raw.get("into")
        and not NOT_COMPLETED_TAGS.intersection(raw.get("tags", []))
    )


def _is_summoners_rift_item(item_id: int, raw: dict[str, Any]) -> bool:
    return (
        item_id < MAX_ITEM_ID
        and raw.get("maps", {}).get(SUMMONERS_RIFT, False)
        and raw.get("gold", {}).get("purchasable", False)
        and raw.get("inStore", True)
        and not raw.get("hideFromAll", False)
        and not raw.get("requiredChampion")
        and not raw.get("requiredAlly")
    )


def _item_tags(raw: dict[str, Any]) -> list[str]:
    tags = {ITEM_TAG_ALIASES.get(tag) or _snake_case(tag) for tag in raw.get("tags", [])}
    if ANTI_HEAL_PATTERN.search(raw.get("description", "")):
        tags.add("anti_heal")
    return sorted(tags)


def _snake_case(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()


@dataclass(frozen=True)
class RuneData:
    id: int
    name: str
    tree_id: int | None = None
    slot: int | None = None


def parse_runes(trees: list[dict[str, Any]]) -> list[RuneData]:
    """trees je runesReforged.json: drevesa z vrsticami run (vrstica 0 = ključne rune)."""
    result: list[RuneData] = []
    for tree in trees:
        result.append(RuneData(id=int(tree["id"]), name=tree["name"]))
        for slot, row in enumerate(tree.get("slots", [])):
            result.extend(
                RuneData(id=int(rune["id"]), name=rune["name"], tree_id=int(tree["id"]), slot=slot)
                for rune in row.get("runes", [])
            )
    return result
