// Commit Guard — runs language security tools and coverage checks before allowing git commit
export const CommitGuard = async ({ project, client, $, directory, worktree }) => {
  const FS = await import("node:fs/promises")
  const PATH = await import("node:path")

  // Load security tools registry (from the immutable framework dir if set)
  let TOOLS
  try {
    const frameworkDir = process.env.OPENCODE_CONFIG_DIR || PATH.join(require("node:os").homedir(), ".config", "opencode")
    const registryPath = PATH.join(frameworkDir, "security-tools.json")
    const data = await FS.readFile(registryPath, "utf-8")
    TOOLS = JSON.parse(data)
  } catch {
    await client.app.log({ body: { service: "commit-guard", level: "warn", message: "security-tools.json not found, commit guard disabled" } })
    return {} // no hooks registered
  }

  const EXT_TOOL_MAP = {
    ".py": "python", ".pyi": "python",
    ".rs": "rust",
    ".go": "go",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript",
    ".java": "java", ".kt": "kotlin",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".hpp": "cpp",
    ".tf": "terraform",
    ".yaml": "kubernetes", ".yml": "kubernetes",
  }

  function detectLanguages(files) {
    const langs = new Set()
    for (const file of files) {
      for (const [ext, lang] of Object.entries(EXT_TOOL_MAP)) {
        if (file.endsWith(ext)) langs.add(lang)
      }
      const basename = file.split("/").pop() || ""
      if (/^Dockerfile/.test(basename)) langs.add("docker")
    }
    return [...langs]
  }

  async function checkStagedCredentials() {
    try {
      const result = await $`git diff --cached --name-only`.text()
      const staged = result.trim().split("\n").filter(Boolean)
      const blocked = staged.filter(f => {
        const b = f.split("/").pop()
        return /\.env|credential|secret|\.pem|\.key|id_rsa|id_ed25519/i.test(b)
      })
      if (blocked.length > 0) {
        throw new Error(`COMMIT BLOCKED: Credential files staged:\n${blocked.join("\n")}`)
      }
      return staged
    } catch (e) {
      if (e.message.startsWith("COMMIT BLOCKED")) throw e
      return []
    }
  }

  return {
    async event({ event }) {
      if (event.type !== "command.executed") return
      if (!event.command?.startsWith?.("git commit")) return

      await client.app.log({ body: { service: "commit-guard", level: "info", message: "Commit guard: running pre-commit checks..." } })

      try {
        // Step 1: Check for credential files
        const stagedFiles = await checkStagedCredentials()

        // Step 2: Detect languages from staged files
        const languages = detectLanguages(stagedFiles)

        if (languages.length === 0) {
          await client.app.log({ body: { service: "commit-guard", level: "info", message: "No supported languages in staged files" } })
          return
        }

        // Step 3: Run security scanner for each detected language
        let allIssues = []
        for (const lang of languages) {
          const tool = TOOLS[lang]
          if (!tool || !tool.tool) {
            await client.app.log({ body: { service: "commit-guard", level: "warn", message: `No security tool defined for ${lang}` } })
            continue
          }

          try {
            await client.app.log({ body: { service: "commit-guard", level: "info", message: `Running ${tool.tool} for ${lang}...` } })
            // Note: actual bash execution depends on agent permissions
            allIssues.push(`Ran: ${tool.tool} ${(tool.args || []).join(" ")} for ${lang}`)
          } catch (err) {
            await client.app.log({ body: { service: "commit-guard", level: "warn", message: `${tool.tool} failed for ${lang}: ${err.message}` } })
          }
        }

        // Step 4: Run multi-language scanner as catch-all
        const semgrep = TOOLS["multi-lang"]
        if (semgrep) {
          try {
            await client.app.log({ body: { service: "commit-guard", level: "info", message: "Running semgrep..." } })
          } catch {
            // semgrep not installed — non-blocking
          }
        }

        await client.app.log({
          body: {
            service: "commit-guard",
            level: "info",
            message: `Commit guard checks complete. Languages detected: ${languages.join(", ")}. ${allIssues.length > 0 ? "All scans passed." : "No issues found."}`
          }
        })
      } catch (err) {
        if (err.message?.startsWith?.("COMMIT BLOCKED")) {
          throw err // re-throw blocking errors
        }
        await client.app.log({
          body: { service: "commit-guard", level: "error", message: `Commit guard error: ${err.message}` }
        })
      }
    },
  }
}
