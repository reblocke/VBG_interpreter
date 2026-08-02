# Security and privacy

## Supported version

Security fixes target the current `main` branch and latest tagged research preview. This is static
research/educational software, not a production clinical service.

## Reporting a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/reblocke/VBG_interpreter/security/advisories/new)
for suspected security or privacy vulnerabilities. Include the affected release/commit, impact,
and reproduction steps using synthetic values only. Do not place exploit details, credentials,
PHI, patient values, or restricted research data in a public issue.

Use the public research-software issue form only for non-sensitive software, documentation, or
scientific-contract reports.

## Runtime boundary

- The browser has no calculation backend, telemetry, application cookies, browser storage,
  URL-state serialization, or entered-value export.
- Entered values are processed by Python running locally in the browser worker.
- The static app uses a restrictive same-origin content-security policy.
- Pyodide is self-hosted under `web/vendor/` and verified by
  `scripts/verify_pyodide_vendor.py`.
- The worker accepts same-origin package/runtime requests and exposes one typed interpretation
  route.
- Dependencies are pinned in `uv.lock`; the upstream `stewartlight` commit is pinned in both the
  package metadata and lockfile.
- The published Pages bundle includes a machine-readable manifest binding it to the exact source
  commit.

Loading the public site makes ordinary HTTPS requests to GitHub Pages. GitHub infrastructure may
retain standard request, abuse-prevention, and security logs. Application code does not include
entered form values in those requests. Do not enter PHI, real patient values, credentials,
restricted data, or secrets into the app, tests, screenshots, issues, or repository artifacts.

This repository does not accept protected datasets or production service credentials.
