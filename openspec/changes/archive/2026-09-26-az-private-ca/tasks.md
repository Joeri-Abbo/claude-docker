## 1. Private CA under --az

- [x] 1.1 `run.sh`: fail early when `REQUESTS_CA_BUNDLE` is set but not a file; mount it as `claude-docker-az.crt` under `--az`
- [x] 1.2 `Dockerfile`: az wrapper defaults `REQUESTS_CA_BUNDLE` to `/etc/ssl/certs/ca-certificates.crt`
- [x] 1.3 `tests/test_az_ca.py`: missing file is refused
- [x] 1.4 `--help`, README `--az` row, private-CA section, threat-model line
