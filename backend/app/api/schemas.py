"""Skupne vhodne sheme API."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Riot: ime 3–16 znakov, oznaka 3–5 znakov.
GAME_NAME_LENGTH = (3, 16)
TAG_LINE_LENGTH = (3, 5)

Platform = Literal["eun1", "euw1", "tr1", "ru", "na1", "br1", "la1", "la2", "kr", "jp1"]


class RiotIdInput(BaseModel):
    """Riot ID ("ime#oznaka") in platforma, kot ju vpiše uporabnik."""

    riot_id: str = Field(max_length=32, examples=["Luka#EUNE"])
    platform: Platform

    @field_validator("riot_id")
    @classmethod
    def validate_riot_id(cls, value: str) -> str:
        game_name, separator, tag_line = value.strip().rpartition("#")
        game_name, tag_line = game_name.strip(), tag_line.strip()
        if not separator:
            raise ValueError("Riot ID mora biti v obliki ime#oznaka.")
        if not GAME_NAME_LENGTH[0] <= len(game_name) <= GAME_NAME_LENGTH[1]:
            raise ValueError("Ime mora imeti 3–16 znakov.")
        if not (TAG_LINE_LENGTH[0] <= len(tag_line) <= TAG_LINE_LENGTH[1] and tag_line.isalnum()):
            raise ValueError("Oznaka mora imeti 3–5 črk ali številk.")
        return f"{game_name}#{tag_line}"

    @property
    def game_name(self) -> str:
        return self.riot_id.rsplit("#", 1)[0]

    @property
    def tag_line(self) -> str:
        return self.riot_id.rsplit("#", 1)[1]
