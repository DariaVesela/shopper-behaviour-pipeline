"""make keys: create a key file in secrets/ for each component's service account."""

import json
import os
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SECRETS_DIR = REPO_ROOT / "secrets"


def create_missing_keys(
    emails: Mapping[str, str],
    secrets_dir: Path,
    create_key: Callable[[str, Path], None],
) -> list[Path]:
    """Create secrets/<component>.json for each component that has none; return the new files.

    An existing file is kept: each key made is another live credential, and GCP allows
    only 10 per service account. Delete a file to have its key made again.
    """
    created = []
    # Files and the directory are created owner-only from the start, never loosened later.
    previous_umask = os.umask(0o077)
    try:
        secrets_dir.mkdir(mode=0o700, exist_ok=True)
        for component, email in emails.items():
            key_file = secrets_dir / f"{component}.json"
            if key_file.exists():
                continue
            # Written beside the final name, then renamed: a failed run leaves no file that
            # a later run would mistake for a finished key.
            partial_file = secrets_dir / f".{component}.json.partial"
            try:
                create_key(email, partial_file)
                partial_file.replace(key_file)
            finally:
                partial_file.unlink(missing_ok=True)
            created.append(key_file)
    finally:
        os.umask(previous_umask)
    return created


def terraform_service_account_emails() -> dict[str, str]:
    """Read each component's service account email from the Terraform output."""
    result = subprocess.run(
        ["terraform", f"-chdir={REPO_ROOT / 'infra' / 'terraform'}", "output", "-json",
         "service_account_emails"],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    return json.loads(result.stdout)


def gcloud_create_key(email: str, key_file: Path) -> None:
    """Have GCP make a new key for the service account `email` and write it to `key_file`."""
    subprocess.run(
        ["gcloud", "iam", "service-accounts", "keys", "create", str(key_file),
         f"--iam-account={email}"],
        check=True,
    )  # fmt: skip


def main() -> None:
    """Create the missing key files and say which were made."""
    created = create_missing_keys(
        terraform_service_account_emails(), SECRETS_DIR, gcloud_create_key
    )
    for key_file in created:
        print(f"created {key_file.relative_to(REPO_ROOT)}")
    if not created:
        print("every service account already has a key file in secrets/")


if __name__ == "__main__":
    main()
