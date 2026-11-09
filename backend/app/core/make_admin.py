"""Povišanje obstoječega uporabnika v administratorja: python -m app.core.make_admin <e-pošta>.

Vloge administrator se ne da dobiti prek API-ja (registracija vedno ustvari igralca), zato
jo podeli lastnik sistema z ukazom na strežniku. Gesla ukaz ne potrebuje.
"""

import sys

from sqlalchemy import select

from app.db.session import get_session_factory
from app.models.user import User, UserRole


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Uporaba: python -m app.core.make_admin <e-pošta>", file=sys.stderr)
        return 2
    email = args[0].strip().lower()
    with get_session_factory()() as session:
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            print(f"Uporabnik {email} ne obstaja (najprej se registriraj).", file=sys.stderr)
            return 1
        user.role = UserRole.ADMIN
        session.commit()
    print(f"{email} je zdaj administrator.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
