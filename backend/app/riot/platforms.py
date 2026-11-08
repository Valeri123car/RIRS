"""Platforme (strežniki igre) in pripadajoče regionalne usmeritve Riot API.

Summoner in Spectator se kličeta na platformi (npr. eun1), Account in Match pa na regiji
(npr. europe). MVP podpira spodnje platforme; ostale (npr. SEA) so v načrtu za kasneje.
"""

from app.riot.errors import InvalidPlatformError

PLATFORM_TO_REGION: dict[str, str] = {
    "eun1": "europe",
    "euw1": "europe",
    "tr1": "europe",
    "ru": "europe",
    "na1": "americas",
    "br1": "americas",
    "la1": "americas",
    "la2": "americas",
    "kr": "asia",
    "jp1": "asia",
}


def region_for(platform: str) -> str:
    """Vrne regionalno usmeritev za platformo ali sproži InvalidPlatformError."""
    try:
        return PLATFORM_TO_REGION[platform]
    except KeyError:
        raise InvalidPlatformError(f"Nepodprta platforma: {platform!r}") from None
