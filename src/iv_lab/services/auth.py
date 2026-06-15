"""User authentication (legacy ``users.txt`` behavior).

Migrated from the legacy ``system`` class in ``IVLab/IVlab.py``:
``scramble_string`` / ``unscramble_string``, the scrambled-JSON user
table loading in ``system.__init__``, and the login rules of
``system.user_login``.

The scramble is the legacy obfuscation, preserved exactly: a random
first byte followed by a cumulative additive byte chain mod 256,
hex-encoded. The output is therefore non-deterministic, but
``unscramble_string`` recovers the input regardless of the seed byte.
It is obfuscation, not cryptography — exactly as in the legacy code.

Login rules preserved from ``system.user_login``:

- usernames are matched lowercase (the table keys are lowercased on
  load),
- a blank username logs in as the generic ``user`` account when that
  account exists with password ``123456``,
- failures raise :class:`AuthenticationError` with the legacy messages
  ("Username not valid" / "Sciper not valid for user ..."),
- calibration is permitted only for the legacy hardcoded usernames and
  for the generic ``user``/``123456`` login. Note the legacy quirk that
  the generic check compares the *original-case* username, so logging
  in as ``User``/``123456`` does not grant calibration.

Standard library only; no GUI dependencies.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Union

#: Machine-specific live users file (gitignored; takes priority if it exists).
USERS_FILENAME = "config/users.txt"

#: Committed generic template used on new systems before a users.txt is created.
USERS_GENERIC_FILENAME = "config/users_generic.txt"

#: Legacy hardcoded usernames allowed to run the calibration.
CALIBRATION_USERS = ("felix", "legeyt")

#: Legacy generic account: blank username logs in as this user.
GENERIC_USERNAME = "user"
GENERIC_PASSWORD = "123456"

#: Legacy error message when users.txt is missing or corrupted.
USER_TABLE_ERROR_MESSAGE = (
    "ERROR: User table corrupted or absent.  Please contact an administrator."
)


class UserTableError(Exception):
    """The users file is missing or cannot be decoded (legacy error)."""


class AuthenticationError(Exception):
    """Login failed (legacy 'Username not valid' / 'Sciper not valid')."""


@dataclass(frozen=True)
class AuthenticatedUser:
    """A successfully logged-in user."""

    #: Lowercase username (legacy ``system.username``).
    username: str
    #: Whether the calibration panel is enabled for this user.
    can_calibrate: bool


def scramble_string(text: str) -> str:
    """Obfuscate a string (legacy ``system.scramble_string``)."""
    bytename = bytearray(text.encode())
    # use a single random byte to scramble the numeric string
    random.seed()
    randbyte = random.getrandbits(8)
    hashed_bytes = [randbyte]
    for i, b in enumerate(bytename):
        hashed_bytes.append((hashed_bytes[i] + b) % 256)

    return "".join("{:02x}".format(b) for b in hashed_bytes)


def unscramble_string(text: str) -> str:
    """Recover a string scrambled by :func:`scramble_string` (legacy
    ``system.unscramble_string``)."""
    extracted = []
    for i in range(int(len(text) / 2)):
        extracted.append(int(text[i * 2 : (i + 1) * 2], 16))

    # undo the convolution from the end, working back; the first byte is
    # the random seed and is thrown away
    length = len(extracted)
    unhashed_reversed = []
    for i in range(length - 1):
        unhashed_reversed.append(
            (extracted[length - 1 - i] - extracted[length - 1 - (i + 1)]) % 256
        )

    return bytearray(reversed(unhashed_reversed)).decode()


def load_users(path: Union[str, Path]) -> dict[str, str]:
    """Load the scrambled JSON user table (legacy ``system.__init__``).

    Returns a username -> password mapping with lowercase usernames.
    Raises :class:`UserTableError` with the legacy message when the file
    is missing or cannot be decoded.
    """
    try:
        scrambled = Path(path).read_text()
        users_raw = json.loads(unscramble_string(scrambled))
        # force all usernames to be lowercase (legacy)
        return {key.lower(): value for key, value in users_raw.items()}
    except Exception as exc:
        raise UserTableError(USER_TABLE_ERROR_MESSAGE) from exc


def write_users(path: Union[str, Path], users: dict[str, str]) -> None:
    """Write a user table in the legacy scrambled-JSON format.

    The legacy application never writes ``users.txt`` (it is prepared by
    an administrator); this helper exists for tests and admin tooling.
    """
    Path(path).write_text(scramble_string(json.dumps(users)))


class Authenticator:
    """Validates logins against a loaded user table
    (legacy ``system.user_login``)."""

    def __init__(self, users: dict[str, str]) -> None:
        #: username -> password, lowercase usernames (as from :func:`load_users`).
        self.users = users

    def login(self, username: str, password: str) -> AuthenticatedUser:
        """Authenticate; returns the user or raises
        :class:`AuthenticationError` with the legacy message."""
        # legacy: a blank username logs in as the generic user when the
        # 'user' account exists with the generic password
        if (
            username.lower() == ""
            and GENERIC_USERNAME in self.users
            and self.users[GENERIC_USERNAME] == GENERIC_PASSWORD
        ):
            username = GENERIC_USERNAME
            password = GENERIC_PASSWORD

        key = username.lower()
        if key not in self.users:
            raise AuthenticationError("Username not valid")
        if self.users[key] != password:
            raise AuthenticationError("Sciper not valid for user " + username)

        # legacy calibration permission, including the original-case
        # comparison of the generic username
        can_calibrate = key in CALIBRATION_USERS or (
            username == GENERIC_USERNAME and password == GENERIC_PASSWORD
        )

        return AuthenticatedUser(username=key, can_calibrate=can_calibrate)
