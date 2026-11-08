"""Vpis šampionov in predmetov v bazo (upsert) s štetjem novih in spremenjenih zapisov.

Nov zapis dobi vse podatke, tudi izpeljane ocene in oznake. Pri obstoječem se posodobijo
samo podatki, ki jih določa Riot (ime, cena, razredi, dokončanost); ocene šampionov in oznake
predmetov ureja administrator (US-14), zato jih ponovni uvoz ne povozi.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ddragon.parse import ChampionData, ItemData
from app.models.champion import Champion
from app.models.item import Item


@dataclass
class Counts:
    created: int = 0
    updated: int = 0
    unchanged: int = 0


@dataclass
class ImportResult:
    champions: Counts = field(default_factory=Counts)
    items: Counts = field(default_factory=Counts)


def import_static_data(
    session: Session, champions: list[ChampionData], items: list[ItemData]
) -> ImportResult:
    """Uvozi podatke v sejo (flush, brez commit – o potrditvi odloči klicatelj)."""
    result = ImportResult()

    existing_champions = _by_id(session, Champion, [c.id for c in champions])
    for data in champions:
        champion = existing_champions.get(data.id)
        if champion is None:
            session.add(
                Champion(
                    id=data.id,
                    slug=data.slug,
                    name=data.name,
                    damage_profile=data.damage_profile,
                    classes=data.classes,
                    **data.ratings,
                )
            )
            result.champions.created += 1
        else:
            changed = _apply(champion, slug=data.slug, name=data.name, classes=data.classes)
            _count(result.champions, changed)

    existing_items = _by_id(session, Item, [i.id for i in items])
    for data in items:
        item = existing_items.get(data.id)
        if item is None:
            session.add(
                Item(
                    id=data.id,
                    name=data.name,
                    cost=data.cost,
                    tags=data.tags,
                    completed=data.completed,
                )
            )
            result.items.created += 1
        else:
            changed = _apply(item, name=data.name, cost=data.cost, completed=data.completed)
            _count(result.items, changed)

    session.flush()
    return result


def _by_id[T: (Champion, Item)](session: Session, model: type[T], ids: list[int]) -> dict[int, T]:
    if not ids:
        return {}
    return {row.id: row for row in session.scalars(select(model).where(model.id.in_(ids)))}


def _apply(row: Champion | Item, **values: object) -> bool:
    """Nastavi vrednosti, ki so drugačne; vrne True, če se je kaj spremenilo."""
    changed = False
    for name, value in values.items():
        if getattr(row, name) != value:
            setattr(row, name, value)
            changed = True
    return changed


def _count(counts: Counts, changed: bool) -> None:
    if changed:
        counts.updated += 1
    else:
        counts.unchanged += 1
