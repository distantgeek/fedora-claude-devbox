import { spawn } from "node:child_process"

export const ScrubDaddyBridge = async ({ project, client, $, directory }) => {
  function scrub(text) {
    if (!text || typeof text !== "string" || text.length < 4) return Promise.resolve(text)

    return new Promise((resolve) => {
      const child = spawn("scrub-daddy-llm", [], { stdio: ["pipe", "pipe", "ignore"] })
      let stdout = ""

      child.stdout.on("data", (chunk) => { stdout += chunk })
      child.on("close", () => { resolve(stdout.trim() || text) })
      child.on("error", () => { resolve(text) })

      child.stdin.write(text)
      child.stdin.end()

      setTimeout(() => {
        child.kill()
        resolve(text)
      }, 5000)
    })
  }

  return {
    "tool.execute.after": async (input, result) => {
      if (!result || typeof result !== "object") return

      if (typeof result.content === "string") {
        result.content = await scrub(result.content)
      }

      if (Array.isArray(result.content)) {
        for (const item of result.content) {
          if (item && item.type === "text" && typeof item.text === "string") {
            item.text = await scrub(item.text)
          }
        }
      }

      if (result.stdout && typeof result.stdout === "string") {
        result.stdout = await scrub(result.stdout)
      }
      if (result.stderr && typeof result.stderr === "string") {
        result.stderr = await scrub(result.stderr)
      }
    },
  }
}
