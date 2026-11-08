import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Champion, RiotAccount, User, UserRole


def _user(email: str) -> User:
    return User(email=email, password_hash="argon2-zgostitev")


def test_nov_uporabnik_dobi_privzeto_vlogo_player(db: Session) -> None:
    user = _user("luka@example.com")
    db.add(user)
    db.flush()
    db.refresh(user)

    assert user.role == UserRole.PLAYER


def test_email_mora_biti_edinstven(db: Session) -> None:
    db.add(_user("luka@example.com"))
    db.flush()

    db.add(_user("luka@example.com"))
    with pytest.raises(IntegrityError):
        db.flush()


@pytest.mark.parametrize("value", [-1, 4])
def test_ocena_sampiona_izven_0_do_3_je_zavrnjena(db: Session, value: int) -> None:
    db.add(Champion(id=266, slug="Aatrox", name="Aatrox", healing=value))

    with pytest.raises(IntegrityError):
        db.flush()


def test_riot_racun_ima_najvec_enega_lastnika(db: Session) -> None:
    owner, other = _user("a@example.com"), _user("b@example.com")
    db.add_all([owner, other])
    db.flush()

    db.add(
        RiotAccount(
            puuid="p-1", game_name="Luka", tag_line="EUNE", platform="eun1", user_id=owner.id
        )
    )
    db.flush()

    db.add(
        RiotAccount(
            puuid="p-1", game_name="Luka", tag_line="EUNE", platform="eun1", user_id=other.id
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_brisanje_uporabnika_ohrani_riot_racun(db: Session) -> None:
    user = _user("luka@example.com")
    db.add(user)
    db.flush()
    account = RiotAccount(
        puuid="p-2", game_name="Luka", tag_line="EUNE", platform="eun1", user_id=user.id
    )
    db.add(account)
    db.flush()

    db.delete(user)
    db.flush()
    db.expire_all()

    assert db.get(RiotAccount, "p-2").user_id is None
