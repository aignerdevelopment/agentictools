---
id: 30-security
tags: [security]
always: false
---

# Security

- Never print, log, commit or transmit secrets, tokens or private keys.
- Use environment variables or a secret manager for credentials.
- Validate and escape all external input.
- Apply least privilege to file, network and shell access.
- Ask before running destructive or irreversible commands.
- Keep dependencies patched; call out known vulnerabilities when you touch them.
