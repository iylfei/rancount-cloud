# Android updates

BeeCount Cloud exposes `GET /api/v1/app-updates/latest` and the APK URL returned
in its `assets` list. Both routes are public so an app can check before login.
Without a published release, `latest` returns HTTP 204.

The Android app reads the BeeCount Cloud address already saved in Cloud Services.
It compares `version` with its installed `versionName`, downloads the universal
APK from the same server, verifies the SHA-256 value, then opens Android's
installer. The APK must have a higher `versionCode` and be signed with the same
certificate as the installed app.

To publish a release, copy a signed universal APK to the server and run:

```sh
python3 scripts/publish_app_update.py \
  --version 1.2.3 \
  --apk /path/to/signed-universal.apk \
  --directory /path/to/persistent/app-updates \
  --notes 'Changes in this release'
```

The directory must match `APP_UPDATE_DIR` in the server container. On Docker,
the default is `/data/app-updates`, inside the persistent `/data` volume. The
script writes the APK first and replaces `latest.json` last, so clients only
see complete releases. Do not publish unsigned or differently signed builds.
