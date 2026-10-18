import type { Plugin } from "@opencode-ai/plugin"
import { fileURLToPath } from "node:url"
import { dirname, resolve } from "node:path"
import { realpathSync } from "node:fs"

function agentictoolsHome(): string {
  if (process.env.AGENTICTOOLS_HOME) return process.env.AGENTICTOOLS_HOME
  const here = realpathSync(dirname(fileURLToPath(import.meta.url)))
  return resolve(here, "..", "..")
}

const FORMATTER = `${agentictoolsHome()}/hooks/shared/format.sh`

export default (async ({ $ }) => {
  return {
    "tool.execute.after": async (input, output) => {
      if (!["edit", "write", "patch"].includes(input.tool)) return
      const file = (output.args?.filePath ?? output.args?.path ?? "") as string
      if (!file) return
      await $`sh ${FORMATTER} ${file}`.catch(() => {})
    },
  }
}) satisfies Plugin
