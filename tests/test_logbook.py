"""Legacy logbook (ivlablog.txt) behavior tests, all in tmp_path."""

import datetime
from pathlib import Path

from iv_lab.services import Logbook

FIXED_TIME = datetime.datetime(2026, 6, 12, 14, 30, 5)
FIXED_PREFIX = "12.06.2026 14:30:05: "


def make_logbook(sd_path) -> Logbook:
    return Logbook(sd_path, clock=lambda: FIXED_TIME)


def read_log(sd_path: Path) -> list[str]:
    return (sd_path / "ivlablog.txt").read_text().splitlines()


def test_login_entry_matches_legacy_format(tmp_path: Path) -> None:
    logbook = make_logbook(tmp_path)

    logbook.log_login("felix")

    assert read_log(tmp_path) == [FIXED_PREFIX + "user felix logged on"]


def test_logout_with_comment_writes_two_legacy_lines(tmp_path: Path) -> None:
    logbook = make_logbook(tmp_path)

    logbook.log_logout("felix", "cells looked unstable today")

    assert read_log(tmp_path) == [
        FIXED_PREFIX + "user comment: cells looked unstable today",
        FIXED_PREFIX + "user felix logged off",
    ]


def test_logout_without_comment_writes_single_line(tmp_path: Path) -> None:
    logbook = make_logbook(tmp_path)

    logbook.log_logout("felix", "")

    assert read_log(tmp_path) == [FIXED_PREFIX + "user felix logged off"]


def test_entries_are_appended(tmp_path: Path) -> None:
    logbook = make_logbook(tmp_path)

    logbook.log_login("felix")
    logbook.log_logout("felix")
    logbook.log_login("alice")

    assert read_log(tmp_path) == [
        FIXED_PREFIX + "user felix logged on",
        FIXED_PREFIX + "user felix logged off",
        FIXED_PREFIX + "user alice logged on",
    ]


def test_empty_sd_path_disables_logging(tmp_path: Path) -> None:
    # legacy: sdPath == '' means no sd copy and no log file
    logbook = Logbook("", clock=lambda: FIXED_TIME)

    logbook.log_login("felix")
    logbook.log_logout("felix", "comment")

    assert not logbook.enabled
    assert logbook.log_file_path is None
    assert list(tmp_path.iterdir()) == []


def test_log_directory_is_created_on_demand(tmp_path: Path) -> None:
    sd_path = tmp_path / "sd" / "nested"
    logbook = make_logbook(sd_path)

    logbook.log_login("felix")

    assert read_log(sd_path) == [FIXED_PREFIX + "user felix logged on"]


def test_real_timestamp_format_is_legacy_compatible(tmp_path: Path) -> None:
    logbook = Logbook(tmp_path)  # real clock

    logbook.log_login("felix")

    line = read_log(tmp_path)[0]
    # dd.mm.YYYY HH:MM:SS: user felix logged on
    prefix, _, message = line.partition(": user ")
    datetime.datetime.strptime(prefix, "%d.%m.%Y %H:%M:%S")
    assert message == "felix logged on"
