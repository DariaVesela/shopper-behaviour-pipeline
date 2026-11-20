"""Checks that local-only files never show up in git status."""

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def is_ignored(path: str) -> bool:
    """Return True if git would ignore `path` (relative to the repo root).

    `git check-ignore` exits 0 for ignored, 1 for not ignored, and anything else on error;
    an error raises rather than reading as "not ignored".
    """
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--no-index", path],
        cwd=REPO_ROOT,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"git check-ignore failed with exit code {result.returncode}")
    return result.returncode == 0


@pytest.mark.parametrize(
    "path",
    [
        "data/raw/2019-Oct.csv",
        "secrets/kafka-connect.json",
        "infra/terraform/terraform.tfvars",
        "infra/terraform/.terraform/providers.lock",
        "infra/terraform/terraform.tfstate",
        "infra/terraform/terraform.tfstate.backup",
        "dbt/target/manifest.json",
        "dbt/logs/dbt.log",
        ".env",
        "replayer/__pycache__/reader.cpython-311.pyc",
        ".idea/workspace.xml",
        ".vscode/settings.json",
    ],
)
def test_local_only_files_are_ignored(path: str) -> None:
    assert is_ignored(path)


@pytest.mark.parametrize(
    "path",
    [
        "infra/terraform/terraform.tfvars.example",
        "infra/terraform/main.tf",
        "schemas/event.avsc",
        "tests/data/sample_events.csv",
        "beam/secrets_test.py",
    ],
)
def test_committed_files_are_not_ignored(path: str) -> None:
    assert not is_ignored(path)
