import { tool } from "@opencode-ai/plugin"

export default tool({
  description:
    "Example agentictools tool. Echoes a message and reports the agentictools home. Replace with real behavior.",
  args: {
    message: tool.schema.string().describe("Message to echo back"),
  },
  async execute(args) {
    const home = process.env.AGENTICTOOLS_HOME ?? "(AGENTICTOOLS_HOME not set)"
    return `agentictools home: ${home}\nmessage: ${args.message}`
  },
})
