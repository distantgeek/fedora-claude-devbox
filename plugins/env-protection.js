// Env Protection — blocks reading .env files, credential files, keys, and certs
export const EnvProtection = async ({ project, client, $, directory, worktree }) => {
  const BLOCKED_PATTERNS = [
    /\.env$/i, /\.env\.\w+$/i,             // .env, .env.local, .env.production
    /credentials/i,                         // credentials.json, aws-credentials, etc
    /\.pem$/i,                              // PEM certificate files
    /\.key$/i,                              // Private key files
    /\.pfx$/i, /\.p12$/i,                   // PKCS12 certificate stores
    /secret/i,                              // secret files
    /id_rsa/i, /id_ed25519/i, /id_ecdsa/i,  // SSH private keys
    /\.htpasswd$/i,                         // htpasswd files
  ]

  function isBlocked(filePath) {
    const basename = filePath.split("/").pop() || filePath
    return BLOCKED_PATTERNS.some(p => p.test(basename))
  }

  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool === "read") {
        const filePath = output.args?.filePath || ""
        if (isBlocked(filePath)) {
          await client.app.log({
            body: { service: "env-protection", level: "warn", message: `Blocked read of sensitive file: ${filePath}` }
          })
          throw new Error(`SECURITY: Cannot read sensitive file: ${filePath}. This file may contain credentials or secrets.`)
        }
      }
    },
  }
}
