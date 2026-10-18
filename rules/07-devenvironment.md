---
id: 07-devenvironment
tags: [core, always, env]
always: true
---

# Environment configuration (`.devenvironment`)

Every project defines its environment-dependent values in
`.devenvironment/env.sh`: git URL and credentials, service URLs, MCP URLs and
credentials, and anything else that varies between environments.

## Always load the environment first

Before you compile, build, run tests, set up the environment for anything, or
invoke any configured or authenticated tool/MCP server, load it from the
repository root and use the resulting variables:

```sh
. ./.devenvironment/env.sh
```

Never hardcode URLs, hostnames, credentials or tokens in code, scripts, tool
definitions or MCP config; reference the exported environment variable instead.

If `.devenvironment/env.sh` does not exist, tell the developer to create it (or
copy it from `templates/project/.devenvironment/` in the central agentictools
repo) before proceeding.

## Secrets

`env.sh` is committed and must contain **no secrets** — only non-secret
defaults and placeholders. Real values go in the gitignored sibling
`.devenvironment/env.local.sh`, which `env.sh` sources automatically.

## Adding new things that need configuration or authentication

When you add a tool, MCP server, service integration or anything else that needs
configuration or authentication, add the corresponding key(s) to
`.devenvironment/env.sh` with the literal placeholder

```
<insert your .... here>
```

(keep the angle brackets and wording), and reference that variable from the
tool/MCP/service config. Also add the same key to
`templates/project/.devenvironment/env.sh` and register the new MCP/tool as usual.

If a variable you need is still a placeholder or empty, stop and tell the
developer exactly which key in `.devenvironment/env.sh` / `env.local.sh` to fill.
Do not invent or guess a value.

Run `devenv_check` (defined by `env.sh`) to list all unconfigured keys.
