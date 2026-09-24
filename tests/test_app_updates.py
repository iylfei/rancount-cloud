import hashlib
import json

from fastapi.testclient import TestClient

from src.main import app
from src.routers import app_updates


def test_app_updates_are_available_only_from_a_valid_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(app_updates, "_release_dir", lambda: tmp_path)
    client = TestClient(app)
    latest = "/api/v1/app-updates/latest"

    assert client.get(latest).status_code == 204

    apk = b"PK\x03\x04test apk"
    (tmp_path / "rancount-0.0.2-universal.apk").write_bytes(apk)
    (tmp_path / "latest.json").write_text(
        json.dumps(
            {
                "version": "0.0.2",
                "release_notes": "Fix screenshot billing",
                "assets": [
                    {
                        "name": "rancount-0.0.2-universal.apk",
                        "sha256": hashlib.sha256(apk).hexdigest(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    response = client.get(latest)
    assert response.status_code == 200
    asset = response.json()["assets"][0]
    assert asset["url"] == "/api/v1/app-updates/files/rancount-0.0.2-universal.apk"
    assert client.get(asset["url"]).content == apk
    assert client.get("/api/v1/app-updates/files/other.apk").status_code == 404

    manifest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    manifest["assets"][0]["name"] = "../secret.apk"
    (tmp_path / "latest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert client.get(latest).status_code == 503
