// Language Guard — detects unguarded languages and halts development until security framework is scaffolded
export const LanguageGuard = async ({ project, client, $, directory, worktree }) => {
  // File extension → language mapping
  const EXT_MAP = {
    ".py": "python", ".pyi": "python",
    ".rs": "rust",
    ".go": "go",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript", ".cts": "typescript",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hxx": "cpp",
    ".tf": "terraform", ".tfvars": "terraform",
    ".yaml": "kubernetes", ".yml": "kubernetes",
  }

  // Languages that have defined security frameworks
  const KNOWN_LANGUAGES = ["python", "rust", "go", "javascript", "typescript", "java", "kotlin", "c", "cpp", "docker", "kubernetes", "terraform", "bash", "sh", "ruby", "powershell", "perl", "php"]

  function detectLanguage(filePath) {
    for (const [ext, lang] of Object.entries(EXT_MAP)) {
      if (filePath.endsWith(ext)) return lang
    }
    const basename = filePath.split("/").pop() || ""
    if (/^Dockerfile/.test(basename)) return "docker"
    return null
  }

  function detectLanguageFromShebang(content) {
    const shebang = content.split("\n")[0] || ""
    if (shebang.includes("python")) return "python"
    if (shebang.includes("node")) return "javascript"
    if (shebang.includes("ruby")) return "ruby"
    if (shebang.includes("bash") || shebang.includes("sh")) return "bash"
    if (shebang.includes("pwsh") || shebang.includes("powershell")) return "powershell"
    if (shebang.includes("perl")) return "perl"
    if (shebang.includes("php")) return "php"
    return null
  }

  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool !== "write" && input.tool !== "edit") return

      const filePath = output.args?.filePath || output.args?.path || ""
      const content = output.args?.content || output.args?.newString || ""
      let language = detectLanguage(filePath)

      if (!language && content) {
        language = detectLanguageFromShebang(content)
      }

      if (!language) return // Can't determine language, allow

      if (!KNOWN_LANGUAGES.includes(language)) {
        await client.app.log({
          body: {
            service: "language-guard",
            level: "warn",
            message: `Unguarded language detected: ${language} (file: ${filePath}). Scaffold security framework before proceeding.`
          }
        })
        throw new Error(
          `UNGUARDED LANGUAGE: ${language}\n\n` +
          `No security framework exists for ${language}. Before writing code:\n` +
          `1. Run: @security-auditor "Research OWASP guidelines for ${language}"\n` +
          `2. Identify: equivalent of bandit/gosec/cargo-audit for ${language}\n` +
          `3. Create: skill file in ~/.config/opencode/skills/security-${language}/SKILL.md\n` +
          `4. Add entry to ~/.config/opencode/security-tools.json\n` +
          `5. Re-run this write – it will be allowed once the language framework exists.\n\n` +
          `Suggested research sources for ${language}:\n` +
          `- OWASP cheat sheets\n` +
          `- NIST National Vulnerability Database\n` +
          `- Language-specific security linters\n` +
          `- Package ecosystem CVE databases`
        )
      }
    },
  }
}
