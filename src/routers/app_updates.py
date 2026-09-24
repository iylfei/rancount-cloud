"""Public Android release manifest and APK downloads from operator-managed storage."""

import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from ..config import get_settings

router = APIRouter()
_APK_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\.apk\Z")
_SHA256 = re.compile(r"[a-fA-F0-9]{64}\Z")
_VERSION = re.compile(r"\d+\.\d+\.\d+\Z")


def _release_dir() -> Path:
    return Path(get_settings().app_update_dir)


def _manifest() -> dict | None:
    manifest_file = _release_dir() / "latest.json"
    if not manifest_file.is_file():
        return None
    try:
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not _VERSION.fullmatch(data["version"]):
            raise ValueError("invalid version")
        assets = data["assets"]
        if not isinstance(assets, list) or not assets:
            raise ValueError("empty assets")
        for asset in assets:
            if not isinstance(asset, dict):
                raise ValueError("invalid asset")
            name = asset["name"]
            if not isinstance(name, str) or not _APK_NAME.fullmatch(name):
                raise ValueError("invalid APK name")
            if not _SHA256.fullmatch(asset["sha256"]):
                raise ValueError("invalid checksum")
            if not (_release_dir() / name).is_file():
                raise ValueError("missing APK")
        return data
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="Update manifest unavailable") from exc


@router.get("/latest", response_model=None)
def latest_release() -> dict | Response:
    data = _manifest()
    if data is None:
        return Response(status_code=204)
    return {
        "version": data["version"],
        "release_notes": data.get("release_notes", ""),
        "assets": [
            {
                "name": asset["name"],
                "url": f"{get_settings().api_prefix}/app-updates/files/{asset['name']}",
                "sha256": asset["sha256"].lower(),
            }
            for asset in data["assets"]
        ],
    }


@router.get("/files/{filename}")
def download_release(filename: str) -> FileResponse:
    data = _manifest()
    if data is None or not any(asset["name"] == filename for asset in data["assets"]):
        raise HTTPException(status_code=404, detail="APK not found")
    return FileResponse(
        _release_dir() / filename,
        media_type="application/vnd.android.package-archive",
        filename=filename,
    )
