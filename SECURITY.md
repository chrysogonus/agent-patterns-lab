# Security policy

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub:
**Security > Report a vulnerability** on this repository
([private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)).
Do not open a public issue.

Include what is affected, how to reproduce it, and the impact you expect.

## Supported versions

Only the latest commit on `main` is supported. There are no maintained releases.

## Response

This is a personal research project maintained on a best-effort basis. You can expect an
acknowledgement within 7 days and an assessment within 30 days.

## Scope

The lab runs locally: the viewer (`apl serve`) binds to `127.0.0.1` only, and model provider keys
live in an untracked `.env`. Reports about exposing the viewer beyond loopback or about leaking
provider keys are in scope.
