# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes (alpha) |

This project is **alpha**. Expect breaking changes before 1.0.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security problems.

- Prefer email to the maintainers listed in the GitHub org/repo settings, or
- Use GitHub **Private vulnerability reporting** if enabled on this repository.

Include:

1. Description of the issue and impact  
2. Steps to reproduce (PoC if possible)  
3. Affected version / commit  

We aim to acknowledge reports within a few business days.

## Operator responsibilities

neo-harness can invoke external model CLIs and (when enabled) run tools against
a workspace directory. You are responsible for:

- Keeping Neo4j credentials and API keys out of git  
- Reviewing diffs before applying host or repo changes  
- Using `NEO_ACT_ALLOW_TOOLS=0` when you only want plan/reflect behavior  
- Not pointing harness memory at shared production graphs without isolation  

See [docs/security-and-publishing.md](docs/security-and-publishing.md).
