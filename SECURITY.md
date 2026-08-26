# Security Policy

## Supported versions

Security fixes apply to the current `main` branch and the latest GitHub
Release tag. Older tags are not patched separately.

## Reporting a vulnerability

Do not open a public issue for secrets, API keys, personal data, or a
working exploit.

Report privately with a
[GitHub security advisory](https://github.com/codingnanyong/busan-competition-2026/security/advisories/new).

Include:

- what is affected (collector, workflow, dashboard, or docs)
- how to reproduce, without a full exploit if possible
- whether keys or personal records were exposed

Maintainers will acknowledge the report and say whether a fix or disclosure
date is planned. Public discussion stays closed until keys are rotated and a
fix is on `main`.

## Secrets in this project

API keys and tokens belong only in local `.env` or GitHub Actions secrets.
Do not put them in issues, pull requests, Linear, Slack, notebooks, or
committed manifests.

See `.env.example` and [data access requirements](docs/data/DATA_ACCESS_REQUIREMENTS.md).
If a key was committed or pasted in chat, revoke it at the provider and
open a private advisory.
