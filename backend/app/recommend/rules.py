"""Rezervna pravila za priporočilo builda (US-04, ADR-0006).

Uporabijo se, ko model nima dovolj podatkov za šampiona. Dokončani predmeti se točkujejo po
oznakah iz Data Dragon:
- škoda glede na razred igralčevega šampiona (strelec, mag, tank ...),
- obramba glede na delež fizične/magične škode nasprotne ekipe,
- protiukrepi za grožnje iz profila sestave (zdravljenje → anti-heal, tank → prebojnost ...).
Variante (standardna, varna, agresivna) se razlikujejo po razmerju teh treh delov. Razlog za
predmet je del točk, ki je prevladal; protiukrepi in obramba imajo prednost pred škodo, ker
igralcu pojasnijo, zakaj kupuje kaj drugega kot običajno.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.models.champion import Champion, DamageProfile
from app.models.item import Item
from app.recommend.base import RULES_LABEL, VARIANTS, RecommendationInput
from app.recommend.champion_stats import BuildStats

ITEMS_PER_VARIANT = 4
MIN_ITEMS = 3
MAX_NAMED_CHAMPIONS = 3

# Priporočilo iz pravih buildov šampiona (champion_stats): točke za pogostost in zmage.
POPULARITY_WEIGHT = 4.0
WIN_RATE_WEIGHT = 4.0
# Predmeti, ki jih ima manj kot ta delež igralcev šampiona, niso kandidati.
MIN_PICK_RATE = 0.05

SKILLS = ("Q", "W", "E")
R_LEVELS = (6, 11, 16)
MAX_LEVEL = 18
POINTS_PER_SKILL = 5

# Moč protiukrepa glede na stopnjo grožnje iz profila sestave.
LEVEL_MULTIPLIER = {"medium": 1.0, "high": 2.0, "very_high": 3.0}
DEFENSE_WEIGHT = 3.0
# Data Dragon podpornih predmetov ne označi; vsi stanejo največ 2300 zlata (Locket, Zeke's,
# Redemption ...), legendarni predmeti za ostale vloge pa vsaj 2400.
SUPPORT_ITEM_MAX_COST = 2300
RESIST_TAGS = frozenset({"spell_block", "magic_resist"})

# Predmeti iz iste skupine se med seboj izključujejo (enak edinstven pasiv).
EXCLUSIVE_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"Lord Dominik's Regards", "Mortal Reminder", "Serylda's Grudge"}),
    frozenset({"Ravenous Hydra", "Titanic Hydra", "Profane Hydra"}),
)


@dataclass(frozen=True)
class Mix:
    """Razmerje med škodo, obrambo in protiukrepi za eno varianto."""

    offense: float
    defense: float
    counters: float
    penetration: float = 0.0


MIXES = {
    "standard": Mix(offense=1.0, defense=0.5, counters=1.0),
    "safe": Mix(offense=0.6, defense=2.0, counters=1.0),
    "aggressive": Mix(offense=1.5, defense=0.0, counters=0.5, penetration=1.0),
}


def mix_for(key: str, state: str) -> Mix:
    """Razmerje variante, prilagojeno stanju igre: vodilni dodajo škodo, zaostajajoči obrambo."""
    base = MIXES[key]
    if state == "ahead":
        return Mix(
            offense=base.offense * 1.4,
            defense=base.defense * 0.4,
            counters=base.counters,
            penetration=base.penetration + 0.5,
        )
    if state == "behind":
        return Mix(
            offense=base.offense * 0.6,
            defense=base.defense * 1.8 + 0.3,
            counters=base.counters,
            penetration=base.penetration,
        )
    return base


@dataclass(frozen=True)
class Counter:
    tags: frozenset[str]
    weight: float
    reason: str


COUNTERS: dict[str, Counter] = {
    "healing": Counter(
        frozenset({"anti_heal"}), 2.0, "Zmanjša zdravljenje nasprotnikov ({champions})."
    ),
    "tank": Counter(
        frozenset(),  # prebojnost je odvisna od vrste škode (glej Profile.penetration)
        1.5,
        "Prebojnost zmanjša oklep in odpor tankovskih nasprotnikov ({champions}).",
    ),
    "cc": Counter(
        frozenset({"tenacity"}),
        1.5,
        "Odpornost skrajša nadzor, ki ga imajo nasprotniki ({champions}).",
    ),
    "poke": Counter(
        frozenset({"health_regen", "life_steal", "spell_vamp"}),
        0.5,
        "Obnova zdravja omili poke nasprotnikov ({champions}).",
    ),
    "burst": Counter(
        frozenset({"health"}), 0.5, "Dodatno zdravje te varuje pred burstom ({champions})."
    ),
}

DEFENSE_REASONS = {
    "physical": "Oklep proti {share} % fizične škode nasprotne ekipe.",
    "magic": "Magični odpor proti {share} % magične škode nasprotne ekipe.",
}

Runes = tuple[str, str, str]  # (primarno drevo, ključna runa, sekundarno drevo)


@dataclass(frozen=True)
class Profile:
    """Kaj gradi šampion določenega razreda."""

    role: str  # "damage", "tank" ali "support" – določa besedilo razloga za škodo
    offense: dict[str, float]
    requires: frozenset[str]  # predmet mora imeti vsaj eno od teh oznak
    forbids: frozenset[str]  # predmet ne sme imeti nobene od teh oznak
    magic: bool
    skill_priority: str
    runes: dict[str, Runes]

    @property
    def penetration(self) -> str:
        return "magic_pen" if self.magic else "armor_pen"


def _profile(
    role: str,
    offense: dict[str, float],
    requires: set[str],
    forbids: set[str],
    magic: bool,
    skill_priority: str,
    standard: Runes,
    safe: Runes,
    aggressive: Runes,
) -> Profile:
    return Profile(
        role=role,
        offense=offense,
        requires=frozenset(requires),
        forbids=frozenset(forbids),
        magic=magic,
        skill_priority=skill_priority,
        runes={"standard": standard, "safe": safe, "aggressive": aggressive},
    )


MARKSMAN = _profile(
    "damage",
    {"critical_strike": 3, "damage": 2, "attack_speed": 2, "armor_pen": 1, "life_steal": 0.5},
    {"damage", "critical_strike", "attack_speed"},
    {"spell_damage"},
    magic=False,
    skill_priority="QWE",
    standard=("Precision", "Lethal Tempo", "Inspiration"),
    safe=("Precision", "Fleet Footwork", "Resolve"),
    aggressive=("Precision", "Press the Attack", "Domination"),
)
MAGE = _profile(
    "damage",
    {"spell_damage": 3, "magic_pen": 1.5, "ability_haste": 1, "mana": 0.5},
    {"spell_damage"},
    {"damage", "critical_strike"},
    magic=True,
    skill_priority="QEW",
    standard=("Sorcery", "Arcane Comet", "Inspiration"),
    safe=("Sorcery", "Phase Rush", "Resolve"),
    aggressive=("Domination", "Electrocute", "Sorcery"),
)
ASSASSIN = _profile(
    "damage",
    {"damage": 3, "armor_pen": 2, "ability_haste": 1},
    {"damage"},
    {"spell_damage", "critical_strike"},
    magic=False,
    skill_priority="QEW",
    standard=("Domination", "Electrocute", "Precision"),
    safe=("Domination", "Electrocute", "Resolve"),
    aggressive=("Domination", "Dark Harvest", "Precision"),
)
MAGIC_ASSASSIN = _profile(
    "damage",
    {"spell_damage": 3, "magic_pen": 2, "ability_haste": 1},
    {"spell_damage"},
    {"damage", "critical_strike"},
    magic=True,
    skill_priority="QEW",
    standard=ASSASSIN.runes["standard"],
    safe=ASSASSIN.runes["safe"],
    aggressive=ASSASSIN.runes["aggressive"],
)
FIGHTER = _profile(
    "damage",
    {"damage": 2.5, "health": 2, "ability_haste": 1, "armor_pen": 0.5},
    {"damage", "health"},
    {"spell_damage", "critical_strike"},
    magic=False,
    skill_priority="QEW",
    standard=("Precision", "Conqueror", "Resolve"),
    safe=("Resolve", "Grasp of the Undying", "Precision"),
    aggressive=("Precision", "Conqueror", "Domination"),
)
MAGIC_FIGHTER = _profile(
    "damage",
    {"spell_damage": 2.5, "health": 2, "ability_haste": 1, "spell_vamp": 0.5},
    {"spell_damage", "health"},
    {"damage", "critical_strike"},
    magic=True,
    skill_priority="QEW",
    standard=FIGHTER.runes["standard"],
    safe=FIGHTER.runes["safe"],
    aggressive=FIGHTER.runes["aggressive"],
)
TANK = _profile(
    "tank",
    {"health": 3, "armor": 1, "spell_block": 1, "ability_haste": 1, "aura": 0.5},
    {"health", "armor", "spell_block", "magic_resist"},
    {"damage", "spell_damage", "critical_strike", "attack_speed"},
    magic=True,
    skill_priority="QWE",
    standard=("Resolve", "Aftershock", "Inspiration"),
    safe=("Resolve", "Grasp of the Undying", "Inspiration"),
    aggressive=("Resolve", "Aftershock", "Domination"),
)
SUPPORT = _profile(
    "support",
    {"mana_regen": 2.5, "ability_haste": 1.5, "aura": 1.5, "spell_damage": 1, "health": 0.5},
    {"mana_regen", "aura", "spell_damage"},
    {"damage", "critical_strike"},
    magic=True,
    skill_priority="EQW",
    standard=("Sorcery", "Summon Aery", "Resolve"),
    safe=("Resolve", "Guardian", "Inspiration"),
    aggressive=("Sorcery", "Arcane Comet", "Inspiration"),
)


def profile_for(champion: Champion) -> Profile:
    """Profil po glavnem Riotovem razredu; mešani razredi se ločijo po vrsti škode."""
    magic = champion.damage_profile == DamageProfile.MAGIC
    primary = next(iter(champion.classes or []), None)
    match primary:
        case "Marksman":
            return MARKSMAN
        case "Mage":
            return MAGE
        case "Assassin":
            return MAGIC_ASSASSIN if magic else ASSASSIN
        case "Fighter":
            return MAGIC_FIGHTER if magic else FIGHTER
        case "Tank":
            return TANK
        case "Support":
            return SUPPORT
    return MAGE if magic else FIGHTER


def skill_levels(priority: str) -> list[str]:
    """Vrstni red sposobnosti po levelih: R na 6/11/16, ostalo po prednosti (max 5 točk)."""
    order = [skill for skill in priority if skill in SKILLS]
    points = dict.fromkeys(order, 0)
    levels: list[str] = []
    for level in range(1, MAX_LEVEL + 1):
        if level in R_LEVELS:
            levels.append("R")
            continue
        # Prve tri levele dobi vsaka sposobnost po eno točko, nato po prednosti.
        skill = (
            order[level - 1]
            if level <= len(order)
            else next(s for s in order if points[s] < POINTS_PER_SKILL)
        )
        points[skill] += 1
        levels.append(skill)
    return levels


@dataclass
class _Pick:
    item: Item
    parts: dict[str, float]


@dataclass
class _Context:
    profile: Profile
    items: list[Item]
    threats: dict[str, dict[str, Any]]
    shares: dict[str, int]  # {"physical": 60, "magic": 40}
    counter_tags: dict[str, frozenset[str]] = field(default_factory=dict)
    build_stats: BuildStats | None = None
    game_state: str = "even"

    def __post_init__(self) -> None:
        for key, counter in COUNTERS.items():
            tags = counter.tags or frozenset({self.profile.penetration})
            self.counter_tags[key] = tags

    def score(self, item: Item, mix: Mix, consumed: set[str]) -> dict[str, float]:
        tags = set(item.tags)
        if self.build_stats is not None:
            # Jedro builda določajo pravi nakupi šampiona; oznake dodajo samo prilagoditev.
            stats = self.build_stats
            parts = {
                "popularity": POPULARITY_WEIGHT * stats.pick_rate(item.id)
                + WIN_RATE_WEIGHT * (stats.win_rate(item.id) - 0.5)
            }
        else:
            offense = sum(self.profile.offense.get(tag, 0) for tag in tags) * mix.offense
            if self.profile.penetration in tags:
                offense += mix.penetration
            parts = {"offense": offense}

        if "armor" in tags:
            parts["defense:physical"] = self._defense("physical", mix)
        if tags & RESIST_TAGS:
            parts["defense:magic"] = self._defense("magic", mix)

        for key, threat in self.threats.items():
            # Grožnje brez protiukrepa v predmetih (npr. engage) ne vplivajo na točke.
            if key in consumed or not tags & self.counter_tags.get(key, frozenset()):
                continue
            multiplier = LEVEL_MULTIPLIER.get(threat["level"], 1.0)
            parts[f"counter:{key}"] = COUNTERS[key].weight * multiplier * mix.counters
        return parts

    def _defense(self, kind: str, mix: Mix) -> float:
        return DEFENSE_WEIGHT * self.shares[kind] / 100 * mix.defense

    def countered(self, item: Item) -> set[str]:
        tags = set(item.tags)
        return {key for key, counter_tags in self.counter_tags.items() if tags & counter_tags}

    def reason(self, parts: dict[str, float], item: Item | None = None) -> str:
        situational = {k: v for k, v in parts.items() if k not in BASE_PARTS and v > 0}
        if situational:
            category = max(situational, key=lambda k: (situational[k], k))
            kind, _, key = category.partition(":")
            if kind == "counter":
                return COUNTERS[key].reason.format(champions=self._names(self.threats[key]))
            return DEFENSE_REASONS[key].format(share=self.shares[key])
        if self.build_stats is not None and item is not None:
            return self._popularity_reason(item)
        return self._offense_reason()

    def _popularity_reason(self, item: Item) -> str:
        stats = self.build_stats
        assert stats is not None
        pick = round(100 * stats.pick_rate(item.id))
        wins = round(100 * stats.win_rate(item.id))
        return f"Pogost predmet tega šampiona ({pick} % iger, {wins} % zmag z njim)."

    def _offense_reason(self) -> str:
        physical, magic = self.shares["physical"], self.shares["magic"]
        if self.profile.role == "tank":
            return (
                f"Zdravje in odpornosti za sprednjo linijo proti {physical} % fizične "
                f"in {magic} % magične škode nasprotnikov."
            )
        if "tank" in self.threats:
            names = self._names(self.threats["tank"])
            return f"Glavni vir škode, ki ga potrebuješ proti trdni sprednji liniji ({names})."
        if self.threats:
            top = next(iter(self.threats.values()))
            if self.profile.role == "support":
                return f"Okrepi zaveznike proti glavni grožnji nasprotnikov ({self._names(top)})."
            return f"Poveča škodo, da hitro odstraniš nevarne nasprotnike ({self._names(top)})."
        return (
            f"Poveča škodo, ker nasprotna ekipa nima izrazitih groženj "
            f"({physical} % fizične škode)."
        )

    @staticmethod
    def _names(threat: dict[str, Any]) -> str:
        return ", ".join(threat["champions"][:MAX_NAMED_CHAMPIONS])


class RuleBasedRecommender:
    """Rezervni Recommender (ADR-0006); vedno vrne vir "rules" brez model_id."""

    def recommend(self, data: RecommendationInput) -> dict[str, Any] | None:
        stats = _usable_stats(data)
        if stats is not None:
            profile = profile_from_builds(stats, data.items, data.champion)
            items = sorted(
                (i for i in data.items if i.completed and stats.pick_rate(i.id) >= MIN_PICK_RATE),
                key=lambda i: i.id,
            )
        else:
            profile = profile_for(data.champion)
            items = sorted(
                (i for i in data.items if i.completed and _allowed(profile, i)),
                key=lambda i: i.id,
            )
        if len(items) < MIN_ITEMS:
            return None

        context = _Context(
            profile=profile,
            items=items,
            # Grožnje so v profilu že razvrščene po moči; prva je najnevarnejša.
            threats={t["key"]: t for t in data.enemy_comp.get("threats", [])},
            shares=data.enemy_comp.get("damage", {"physical": 50, "magic": 50}),
            build_stats=stats,
            game_state=data.game_state,
        )
        variants = _variants(context)
        if not variants:
            return None
        return {
            "source": "rules",
            "label": RULES_LABEL,
            "model_id": None,
            "game_state": data.game_state,
            "champion": {"id": data.champion.id, "name": data.champion.name},
            "variants": variants,
        }


BASE_PARTS = frozenset({"offense", "popularity"})
ALL_PROFILES = (MARKSMAN, MAGE, ASSASSIN, MAGIC_ASSASSIN, FIGHTER, MAGIC_FIGHTER, TANK, SUPPORT)


def _usable_stats(data: RecommendationInput) -> BuildStats | None:
    stats = data.build_stats
    if stats is None:
        return None
    candidates = [i for i in data.items if i.completed and stats.pick_rate(i.id) >= MIN_PICK_RATE]
    return stats if len(candidates) >= MIN_ITEMS else None


def profile_from_builds(stats: BuildStats, items: Sequence[Item], champion: Champion) -> Profile:
    """Profil (rune, sposobnosti, razlogi), ki se najbolj ujema z dejanskim buildom šampiona.

    Razred šampiona ne zadošča (Pyke je »Support«, a gradi smrtonosnost); zato profil, katerega
    oznake pridobijo največ točk pri pogostih predmetih. Pri izenačenju velja razred.
    """
    fallback = profile_for(champion)

    def fit(profile: Profile) -> float:
        total = 0.0
        for item in items:
            rate = stats.pick_rate(item.id)
            tags = set(item.tags)
            if not item.completed or rate < MIN_PICK_RATE:
                continue
            if tags & profile.forbids or not tags & profile.requires:
                continue
            total += rate * sum(profile.offense.get(tag, 0) for tag in tags)
        return total

    best = max(ALL_PROFILES, key=fit)
    return best if fit(best) > fit(fallback) else fallback


def _allowed(profile: Profile, item: Item) -> bool:
    tags = set(item.tags)
    if profile.role != "support" and item.cost <= SUPPORT_ITEM_MAX_COST:
        return False
    return bool(tags & profile.requires) and not tags & profile.forbids


def _variants(context: _Context) -> list[dict[str, Any]]:
    """Variante z različnimi nabori predmetov (ADR-0007: razlika v vsaj enem predmetu)."""
    variants: list[dict[str, Any]] = []
    seen: list[frozenset[int]] = []
    for key, label in VARIANTS:
        excluded: set[int] = set()
        mix = mix_for(key, context.game_state)
        picks = _pick(context, mix, excluded)
        while len(picks) >= MIN_ITEMS and frozenset(p.item.id for p in picks) in seen:
            excluded.add(picks[-1].item.id)
            picks = _pick(context, mix, excluded)
        if len(picks) < MIN_ITEMS:
            continue
        seen.append(frozenset(p.item.id for p in picks))
        primary_tree, keystone, secondary_tree = context.profile.runes[key]
        variants.append(
            {
                "key": key,
                "label": label,
                "runes": {
                    "primary_tree": primary_tree,
                    "keystone": keystone,
                    "secondary_tree": secondary_tree,
                },
                "items": [
                    {
                        "id": p.item.id,
                        "name": p.item.name,
                        "reason": context.reason(p.parts, p.item),
                    }
                    for p in picks
                ],
                "skill_order": {
                    "priority": list(context.profile.skill_priority),
                    "levels": skill_levels(context.profile.skill_priority),
                },
            }
        )
    return variants


def _pick(context: _Context, mix: Mix, excluded: set[int]) -> list[_Pick]:
    """Požrešna izbira: vsakič najbolje ocenjen predmet; izpolnjen protiukrep se ne ponovi."""
    picks: list[_Pick] = []
    consumed: set[str] = set()
    blocked: set[int] = set(excluded)
    while len(picks) < ITEMS_PER_VARIANT:
        best: tuple[tuple[float, int, int], Item, dict[str, float]] | None = None
        for item in context.items:
            if item.id in blocked:
                continue
            parts = context.score(item, mix, consumed)
            rank = (sum(parts.values()), item.cost, -item.id)
            if best is None or rank > best[0]:
                best = (rank, item, parts)
        if best is None:
            break
        _, item, parts = best
        picks.append(_Pick(item, parts))
        consumed |= context.countered(item)
        blocked |= {item.id} | _group_ids(context.items, item)
    return picks


def _group_ids(items: Sequence[Item], item: Item) -> set[int]:
    for group in EXCLUSIVE_GROUPS:
        if item.name in group:
            return {i.id for i in items if i.name in group}
    return set()
