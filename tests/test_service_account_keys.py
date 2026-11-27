"""Tests for make keys: one key file per component service account, in secrets/."""

import os
import stat
from pathlib import Path

import pytest

from scripts.service_account_keys import create_missing_keys

EMAILS = {
    "kafka-connect": "kafka-connect-sa@test-project.iam.gserviceaccount.com",
    "beam": "beam-sa@test-project.iam.gserviceaccount.com",
}


class FakeGcloud:
    """Stands in for `gcloud iam service-accounts keys create`: writes a fake key file."""

    def __init__(self) -> None:
        self.requested_emails: list[str] = []

    def create_key(self, email: str, key_file: Path) -> None:
        self.requested_emails.append(email)
        key_file.write_text(f'{{"client_email": "{email}"}}')


def test_creates_a_key_file_per_component(tmp_path: Path) -> None:
    gcloud = FakeGcloud()

    created = create_missing_keys(EMAILS, tmp_path, gcloud.create_key)

    assert created == [tmp_path / "kafka-connect.json", tmp_path / "beam.json"]
    assert (tmp_path / "beam.json").read_text() == (
        '{"client_email": "beam-sa@test-project.iam.gserviceaccount.com"}'
    )


def test_an_existing_key_file_is_kept_and_no_new_key_is_made(tmp_path: Path) -> None:
    """Every key made is a live credential, and GCP allows only 10 per account."""
    (tmp_path / "beam.json").write_text("existing key")
    gcloud = FakeGcloud()

    created = create_missing_keys(EMAILS, tmp_path, gcloud.create_key)

    assert created == [tmp_path / "kafka-connect.json"]
    assert gcloud.requested_emails == [EMAILS["kafka-connect"]]
    assert (tmp_path / "beam.json").read_text() == "existing key"


def test_key_files_are_readable_only_by_their_owner(tmp_path: Path) -> None:
    secrets_dir = tmp_path / "secrets"
    previous_umask = os.umask(0o022)  # a typical umask, under which new files would be 644
    try:
        create_missing_keys(EMAILS, secrets_dir, FakeGcloud().create_key)
    finally:
        os.umask(previous_umask)

    assert stat.S_IMODE((secrets_dir / "beam.json").stat().st_mode) == 0o600
    assert stat.S_IMODE(secrets_dir.stat().st_mode) == 0o700


def test_a_failed_key_leaves_no_file_so_the_next_run_retries(tmp_path: Path) -> None:
    """A half-written file would otherwise count as present and never be replaced."""

    def fail_midway(email: str, key_file: Path) -> None:
        key_file.write_text('{"client_email": ')
        raise RuntimeError("gcloud failed")

    with pytest.raises(RuntimeError, match="gcloud failed"):
        create_missing_keys(EMAILS, tmp_path, fail_midway)

    assert list(tmp_path.iterdir()) == []
    assert create_missing_keys(EMAILS, tmp_path, FakeGcloud().create_key) == [
        tmp_path / "kafka-connect.json",
        tmp_path / "beam.json",
    ]
