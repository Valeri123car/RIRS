"""Napake Riot prehoda. Sporočila nikoli ne vsebujejo API ključa."""


class RiotApiError(Exception):
    """Splošna napaka pri klicu Riot API."""


class RiotNotFoundError(RiotApiError):
    """Iskani vir (račun, tekma ...) ne obstaja."""


class RiotAuthError(RiotApiError):
    """API ključ manjka, je neveljaven ali je potekel (razvojni ključ velja 24 ur)."""


class RiotUnavailableError(RiotApiError):
    """Riot API po več poskusih ni odgovoril (napaka strežnika, omrežja ali omejitve)."""


class InvalidPlatformError(RiotApiError, ValueError):
    """Neznana ali nepodprta platforma (regija strežnika)."""


class RiotConfigError(RiotApiError):
    """Napačna nastavitev Riot prehoda (npr. način live brez ključa)."""
