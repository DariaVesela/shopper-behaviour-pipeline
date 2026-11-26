"""The event ID: the stable identity of an event, the same however it enters the pipeline.

Recipe (fixed; changing it would give every stored event a different ID):

    the first 32 hex characters of SHA-256 of the UTF-8 string "<base name>:<record number>"

- <base name> is the source file's name without its directory, e.g. "2019-Oct.csv". Paths
  are split on "/" only, as POSIX paths; a Windows path with backslashes is not supported.
  Both ingest paths must read each file under its original name: a renamed or compressed
  copy (e.g. "2019-Oct.csv.gz") gives every event a different ID.
- <record number> is the 1-based CSV record number in that file, not counting the header
  (records as csv.reader yields them, not physical lines, which differ when a quoted field
  holds a newline), written in decimal with no padding.

Example: event_id("2019-Oct.csv", 1) == "8bb5b68b26122aacc4bc89501df780b3".
"""

import hashlib
import os
from pathlib import PurePosixPath


def event_id(source_file: str | os.PathLike[str], record_number: int) -> str:
    """Return the event ID of CSV record `record_number` (1-based, no header) of `source_file`.

    Raises TypeError unless `record_number` is an int (bools excluded), and ValueError if it
    is below 1 or `source_file` has no file name.
    """
    # 1.0 or True would format differently from 1 and give the same event another ID.
    if isinstance(record_number, bool) or not isinstance(record_number, int):
        raise TypeError(f"record_number must be an int, got {record_number!r}")
    if record_number < 1:
        raise ValueError(f"record_number must be 1 or more, got {record_number}")
    base_name = PurePosixPath(source_file).name
    if base_name in ("", ".."):
        raise ValueError(f"source_file has no file name: {source_file!r}")
    key = f"{base_name}:{record_number}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
