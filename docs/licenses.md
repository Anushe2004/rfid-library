# Dependency and licence inventory (NFR 04, starter)

Verify each licence against the package metadata before final submission, and generate a
CycloneDX SBOM in CI for the final tagged release.

| Package | Pinned | Role | Licence (check) |
|---------|--------|------|-----------------|
| openpyxl | 3.1.5 | read .xlsx | MIT |
| fastapi | 0.142.2 | service skeleton | MIT |
| pytest | 9.1.1 | tests (dev) | MIT |
| httpx | 0.28.1 | API tests (dev) | BSD-3-Clause |
| ruff | 0.16.10 | lint/format (dev) | MIT |

Offline install: download wheels once with `pip download -r requirements.txt -d wheels/`, carry
`wheels/` to the isolated site, install with `pip install --no-index --find-links wheels -r requirements.txt`.
