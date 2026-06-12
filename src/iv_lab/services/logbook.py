"""Login/logout logbook (legacy ``ivlablog.txt`` behavior).

Migrated from ``system.writeToLogFile``, ``system.user_login``, and
``system.user_logout`` in ``IVLab/IVlab.py``:

- the log lives at ``<sdPath>/ivlablog.txt``; an empty ``sdPath``
  disables logging entirely (legacy),
- entries are appended as ``<dd.mm.YYYY HH:MM:SS: ><message>``,
- login writes ``user <name> logged on``,
- logout writes an optional ``user comment: <entry>`` line (only when
  the user typed one) followed by ``user <name> logged off``,
- the log directory is created on demand; a directory-creation failure
  is reported to the console and the entry is dropped (legacy).

Standard library only; no GUI or hardware dependencies. The clock is
injectable for tests.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Callable, Optional, Union

#: Legacy log file name inside ``sdPath``.
LOG_FILENAME = "ivlablog.txt"

#: Legacy timestamp prefix format.
TIMESTAMP_FORMAT = "%d.%m.%Y %H:%M:%S: "


class Logbook:
    """Appends legacy-format entries to ``ivlablog.txt``."""

    def __init__(
        self,
        sd_path: Union[str, Path, None],
        *,
        clock: Optional[Callable[[], datetime.datetime]] = None,
    ) -> None:
        #: Legacy ``computer.sdPath``; empty/None disables the logbook.
        self.sd_path = str(sd_path) if sd_path is not None else ""
        self._clock = clock or datetime.datetime.now

    @property
    def enabled(self) -> bool:
        """Whether logging is active (legacy ``sdPath != ''``)."""
        return self.sd_path != ""

    @property
    def log_file_path(self) -> Optional[Path]:
        """Full path of the log file, or None when disabled."""
        if not self.enabled:
            return None
        return Path(self.sd_path) / LOG_FILENAME

    def _timestamp(self) -> str:
        return self._clock().strftime(TIMESTAMP_FORMAT)

    def write(self, entry: str) -> None:
        """Append one raw entry (legacy ``writeToLogFile``)."""
        if not self.enabled:
            return

        log_file = self.log_file_path
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            print("ERROR: unable to create logfile directory")
            return

        # legacy opened with "w" for a new file and "a" otherwise; both
        # create the file, so append covers both cases
        with open(log_file, "a") as f:
            f.write(entry + "\n")

    def log_login(self, username: str) -> None:
        """Record a login (legacy ``user_login`` log line)."""
        self.write(self._timestamp() + "user " + username + " logged on")

    def log_logout(self, username: str, log_book_entry: str = "") -> None:
        """Record a logout with the optional user comment
        (legacy ``user_logout`` log lines)."""
        if len(log_book_entry) > 0:
            self.write(self._timestamp() + "user comment: " + log_book_entry)
        self.write(self._timestamp() + "user " + username + " logged off")
