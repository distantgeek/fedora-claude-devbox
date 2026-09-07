// Security Sniffer — intercepts write/edit operations and scans for security violations
export const SecuritySniffer = async ({ project, client, $, directory, worktree }) => {
  const SEVERITY = { CRITICAL: "CRITICAL", HIGH: "HIGH", MEDIUM: "MEDIUM", LOW: "LOW" }

  const PATTERNS = [
    // Secrets & Credentials
    { pattern: /(?:api[_-]?key|apikey|secret|password|passwd|token|credential)\s*[=:]\s*['"][^'"]{8,}['"]/gi, severity: SEVERITY.CRITICAL, category: "Hardcoded secret" },
    { pattern: /-----BEGIN\s+(?:RSA|EC|DSA|OPENSSH)\s+PRIVATE KEY-----/gi, severity: SEVERITY.CRITICAL, category: "Private key in source" },
    { pattern: /AKIA[0-9A-Z]{16}/g, severity: SEVERITY.CRITICAL, category: "AWS access key" },

    // Injection
    { pattern: /os\.system\s*\(.*\)/, severity: SEVERITY.HIGH, category: "Unsafe OS command" },
    { pattern: /subprocess\.call\s*\(.*shell\s*=\s*True/, severity: SEVERITY.HIGH, category: "Shell injection risk" },
    { pattern: /eval\s*\(/, severity: SEVERITY.HIGH, category: "eval() usage" },
    { pattern: /exec\s*\(/, severity: SEVERITY.HIGH, category: "exec() usage" },
    { pattern: /innerHTML\s*=/, severity: SEVERITY.HIGH, category: "innerHTML assignment" },
    { pattern: /dangerouslySetInnerHTML/, severity: SEVERITY.HIGH, category: "dangerouslySetInnerHTML usage" },
    { pattern: /(\+\s*['"]|f['"].*\{.*user)/, severity: SEVERITY.MEDIUM, category: "Possible string-built SQL" },

    // Weak Cryptography
    { pattern: /(?:MD5|md5)\s*\(/, severity: SEVERITY.HIGH, category: "MD5 usage" },
    { pattern: /(?:SHA-?1|sha-?1)\s*\(/, severity: SEVERITY.HIGH, category: "SHA1 usage" },
    { pattern: /Cipher\.getInstance\s*\(\s*['"]DES/, severity: SEVERITY.HIGH, category: "DES cipher" },
    { pattern: /ECB/gi, severity: SEVERITY.HIGH, category: "ECB mode" },

    // Insecure Config
    { pattern: /DEBUG\s*=\s*True/i, severity: SEVERITY.MEDIUM, category: "Debug mode enabled" },
    { pattern: /CORS_ORIGIN.*['"]\*['"]/, severity: SEVERITY.MEDIUM, category: "CORS wildcard" },

    // Path Traversal
    { pattern: /os\.path\.join\s*\(.*request\./, severity: SEVERITY.MEDIUM, category: "Possible path traversal" },
  ]

  function scan(content, filePath) {
    const findings = []
    for (const { pattern, severity, category } of PATTERNS) {
      const matches = content.match(pattern)
      if (matches) {
        findings.push({ file: filePath, severity, category, count: matches.length })
      }
    }
    return findings
  }

  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool === "write" || input.tool === "edit") {
        // Extract the content being written
        const content = output.args?.content || output.args?.newString || ""
        const filePath = output.args?.filePath || output.args?.path || "unknown"

        if (!content) return // nothing to scan

        const findings = scan(content, filePath)

        if (findings.length === 0) return

        const critical = findings.filter(f => f.severity === SEVERITY.CRITICAL)
        const high = findings.filter(f => f.severity === SEVERITY.HIGH)
        const medium = findings.filter(f => f.severity === SEVERITY.MEDIUM)

        if (critical.length > 0) {
          const msg = critical.map(f => `  ${f.category} (${f.count}x) in ${f.file}`).join("\n")
          await client.app.log({ body: { service: "security-sniffer", level: "error", message: `BLOCKED: Critical security issues:\n${msg}` } })
          throw new Error(`SECURITY BLOCK: Critical issues found:\n${msg}\n\nFix these before writing.`)
        }

        if (high.length > 0) {
          const msg = high.map(f => `  ${f.category} (${f.count}x) in ${f.file}`).join("\n")
          await client.app.log({ body: { service: "security-sniffer", level: "warn", message: `WARNING: High severity issues:\n${msg}` } })
        }

        if (medium.length > 0) {
          const msg = medium.map(f => `  ${f.category} in ${f.file}`).join(", ")
          await client.app.log({ body: { service: "security-sniffer", level: "info", message: `Medium issues noted: ${msg}` } })
        }
      }
    },
  }
}
