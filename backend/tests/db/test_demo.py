import pytest
from sqlalchemy.orm import Session

from app.demo import DemoError, seed_demo


def test_demo_za_neobstojecega_uporabnika_javi_napako(db: Session):
    with pytest.raises(DemoError, match="ne obstaja"):
        seed_demo(db, "ni-ga@example.com")
