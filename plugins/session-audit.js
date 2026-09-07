// Session Audit — nudges a session-start code + security review.
// Complements the standing instruction to run /audit before modifying code.
export const SessionAudit = async ({ project, client, directory, worktree }) => {
  return {
    async event({ event }) {
      if (event.type !== "session.created") return

      await client.app.log({
        body: {
          service: "session-audit",
          level: "info",
          message: "Session started. Standing policy: run /audit (spawns security-auditor + code-reviewer) before modifying code.",
        },
      })
    },
  }
}
