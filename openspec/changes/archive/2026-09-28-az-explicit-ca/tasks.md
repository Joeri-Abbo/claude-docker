## 1. Explicit --az CA variable

- [x] 1.1 `run.sh`: read `CLAUDE_DOCKER_AZ_CA` instead of `REQUESTS_CA_BUNDLE` for the check and the mount; list it in `--help`
- [x] 1.2 `tests/test_az_ca.py`: missing `CLAUDE_DOCKER_AZ_CA` file is refused
- [x] 1.3 README: `--az` row, private-CA section, threat-model line
