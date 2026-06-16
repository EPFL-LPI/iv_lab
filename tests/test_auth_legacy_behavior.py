"""Legacy authentication behavior tests.

All user files are created in tmp_path with the test's own scrambled
content; the only repository file touched is the committed generic
template ``config/users_generic.txt`` (read-only).
"""

from pathlib import Path

import pytest

from iv_lab.services import (
    AuthenticatedUser,
    AuthenticationError,
    Authenticator,
    UserTableError,
    load_users,
    scramble_string,
    unscramble_string,
    write_users,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

TEST_USERS = {
    "felix": "111111",
    "legeyt": "222222",
    "alice": "333333",
    "user": "123456",
}


def make_users_file(tmp_path: Path, users=None) -> Path:
    path = tmp_path / "users.txt"
    write_users(path, users if users is not None else TEST_USERS)
    return path


# --- scramble/unscramble ---


@pytest.mark.parametrize(
    "text",
    [
        "felix_20220608_123456",
        '{"username":"Sciper", "legeyt":"180578"}',
        "user",
        "",
        "äöü unicode",
    ],
)
def test_scramble_string_round_trips(text: str) -> None:
    assert unscramble_string(scramble_string(text)) == text


def test_scramble_output_is_hex_with_random_seed_byte() -> None:
    scrambled = scramble_string("abc")

    # one seed byte plus one byte per input byte, two hex digits each
    assert len(scrambled) == (1 + 3) * 2
    int(scrambled, 16)  # all hex


def test_committed_generic_users_file_decodes() -> None:
    # the committed legacy template must load with the migrated code
    users = load_users(REPO_ROOT / "config" / "users_generic.txt")

    assert isinstance(users, dict)
    assert users  # non-empty
    assert all(key == key.lower() for key in users)
    assert "user" in users


# --- user table loading ---


def test_load_users_round_trip(tmp_path: Path) -> None:
    path = make_users_file(tmp_path)

    assert load_users(path) == TEST_USERS


def test_load_users_lowercases_usernames(tmp_path: Path) -> None:
    path = make_users_file(tmp_path, {"Felix": "111111", "LEGEYT": "222222"})

    users = load_users(path)

    assert users == {"felix": "111111", "legeyt": "222222"}


def test_missing_users_file_raises_legacy_error(tmp_path: Path) -> None:
    with pytest.raises(UserTableError, match="User table corrupted or absent"):
        load_users(tmp_path / "users.txt")


def test_corrupted_users_file_raises_legacy_error(tmp_path: Path) -> None:
    path = tmp_path / "users.txt"
    path.write_text("this is not a scrambled user table")

    with pytest.raises(UserTableError, match="User table corrupted or absent"):
        load_users(path)


# --- login ---


def test_valid_login_returns_lowercase_user(tmp_path: Path) -> None:
    auth = Authenticator(load_users(make_users_file(tmp_path)))

    user = auth.login("alice", "333333")

    assert isinstance(user, AuthenticatedUser)
    assert user.username == "alice"


def test_login_is_case_insensitive_for_username(tmp_path: Path) -> None:
    auth = Authenticator(load_users(make_users_file(tmp_path)))

    assert auth.login("Alice", "333333").username == "alice"
    assert auth.login("ALICE", "333333").username == "alice"


def test_blank_username_logs_in_as_generic_user(tmp_path: Path) -> None:
    auth = Authenticator(load_users(make_users_file(tmp_path)))

    user = auth.login("", "anything")  # password is ignored (legacy)

    assert user.username == "user"
    assert user.can_calibrate


def test_blank_username_without_generic_account_fails(tmp_path: Path) -> None:
    users = {k: v for k, v in TEST_USERS.items() if k != "user"}
    auth = Authenticator(load_users(make_users_file(tmp_path, users)))

    with pytest.raises(AuthenticationError, match="Username not valid"):
        auth.login("", "123456")


def test_wrong_password_fails_with_legacy_message(tmp_path: Path) -> None:
    auth = Authenticator(load_users(make_users_file(tmp_path)))

    with pytest.raises(AuthenticationError, match="Sciper not valid for user alice"):
        auth.login("alice", "wrong")


def test_unknown_username_fails_with_legacy_message(tmp_path: Path) -> None:
    auth = Authenticator(load_users(make_users_file(tmp_path)))

    with pytest.raises(AuthenticationError, match="Username not valid"):
        auth.login("nobody", "123456")


# --- calibration permissions (legacy hardcoded rules) ---


def test_calibration_allowed_for_legacy_hardcoded_users(tmp_path: Path) -> None:
    auth = Authenticator(load_users(make_users_file(tmp_path)))

    assert auth.login("felix", "111111").can_calibrate
    assert auth.login("legeyt", "222222").can_calibrate


def test_calibration_denied_for_regular_users(tmp_path: Path) -> None:
    auth = Authenticator(load_users(make_users_file(tmp_path)))

    assert not auth.login("alice", "333333").can_calibrate


def test_calibration_allowed_for_explicit_generic_login(tmp_path: Path) -> None:
    auth = Authenticator(load_users(make_users_file(tmp_path)))

    assert auth.login("user", "123456").can_calibrate


def test_calibration_generic_check_is_case_sensitive_legacy_quirk(
    tmp_path: Path,
) -> None:
    # legacy compares the original-case username against 'user', so
    # 'User'/'123456' logs in fine but does not enable calibration
    auth = Authenticator(load_users(make_users_file(tmp_path)))

    user = auth.login("User", "123456")

    assert user.username == "user"
    assert not user.can_calibrate


def test_calibration_hardcoded_users_match_case_insensitively(tmp_path: Path) -> None:
    # the legacy check runs on self.username, which is lowercased
    auth = Authenticator(load_users(make_users_file(tmp_path)))

    assert auth.login("Felix", "111111").can_calibrate
