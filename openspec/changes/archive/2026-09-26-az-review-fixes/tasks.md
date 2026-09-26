## 1. Lock az deps

- [x] 1.1 `update_pins.py`: write `pins/az-requirements.txt` with `pins/az.env`; commit every staged file
- [x] 1.2 Dockerfile: `--require-hashes -r pins/az-requirements.txt`, fail when it doesn't pin `AZ_VERSION`
- [x] 1.3 `tests/test_az_lock.py`

## 2. No ~/.azure mounts

- [x] 2.1 `run.sh`: drop the `azureProfile.json` / `clouds.config` mounts; help text
- [x] 2.2 Smoke: PAT carries the sentinel

## 3. Telemetry and docs

- [x] 3.1 Wrapper sets `AZURE_CORE_COLLECT_TELEMETRY=no`; dockle accept-key
- [x] 3.2 `.trivyignore` scope note; README; design doc `op run` pointer
