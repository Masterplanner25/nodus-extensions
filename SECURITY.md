# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | Yes |

## Sandbox tier warning

`SubprocessSandboxRunner` (`SandboxTier.INSECURE_DEV`) runs extension code as
a child process with the **same OS user permissions as the host**. Do not use
this tier for untrusted third-party extensions. Use `OciSandboxRunner`
(`SandboxTier.CONTAINER`) for production isolation.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report privately to: **shawnknight@the-master-plan.com**

Include a description, steps to reproduce, and potential impact.
You will receive a response within 72 hours.
