"""The event ID: the stable identity of an event, the same however it enters the pipeline.

Recipe (fixed; changing it would give every stored event a different ID):

    the first 32 hex characters of SHA-256 of the UTF-8 string "<base name>:<line number>"

- <base name> is the source file's name without its directory, e.g. "2019-Oct.csv". Paths
  are read as POSIX paths on every OS, so the ID cannot depend on where the code runs.
- <line number> is the 1-based data line number in that file, not counting the header,
  written in decimal with no padding.

Example: event_id("2019-Oct.csv", 1) == "8bb5b68b26122aacc4bc89501df780b3".
"""

import hashlib
import os
from pathlib import PurePosixPath


def event_id(source_file: str | os.PathLike[str], line_number: int) -> str:
    """Return the event ID of data line `line_number` (1-based, no header) of `source_file`."""
    key = f"{PurePosixPath(source_file).name}:{line_number}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
