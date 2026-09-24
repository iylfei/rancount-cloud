"""Publish one Android APK to the public update feed atomically."""

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Android versionName, e.g. 1.2.3")
    parser.add_argument("--apk", required=True, type=Path, help="signed universal APK")
    parser.add_argument("--directory", type=Path, default=Path(os.getenv("APP_UPDATE_DIR", "/data/app-updates")))
    parser.add_argument("--notes", default="", help="release notes")
    args = parser.parse_args()

    if not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        parser.error("version must be major.minor.patch")
    if not args.apk.is_file():
        parser.error("APK must be a readable ZIP/APK file")
    with args.apk.open("rb") as source:
        header = source.read(4)
    if header != b"PK\x03\x04":
        parser.error("APK must be a readable ZIP/APK file")

    args.directory.mkdir(parents=True, exist_ok=True)
    name = f"rancount-{args.version}-universal.apk"
    destination = args.directory / name
    digest = hashlib.sha256()
    with tempfile.NamedTemporaryFile(dir=args.directory, suffix=".apk", delete=False) as staged:
        staged_path = Path(staged.name)
        with args.apk.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                staged.write(chunk)
                digest.update(chunk)
    try:
        os.replace(staged_path, destination)
    finally:
        staged_path.unlink(missing_ok=True)

    manifest = {
        "version": args.version,
        "release_notes": args.notes,
        "assets": [{"name": name, "sha256": digest.hexdigest()}],
    }
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=args.directory, suffix=".json", delete=False
    ) as staged:
        manifest_path = Path(staged.name)
        json.dump(manifest, staged, ensure_ascii=False)
    try:
        os.replace(manifest_path, args.directory / "latest.json")
    finally:
        manifest_path.unlink(missing_ok=True)
    print(f"Published {name} ({digest.hexdigest()})")


if __name__ == "__main__":
    main()
