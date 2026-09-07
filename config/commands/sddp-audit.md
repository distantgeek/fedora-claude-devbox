@project-auditor

You are starting a project audit workflow. Your sole purpose is to fully audit an existing codebase for security vulnerabilities, structural issues, and hallucination risks.

## Input
`$ARGUMENTS` = The project path to audit (default: current directory).

## Instructions
1. Run: `project-auditor <path>`
2. Analyze findings: categorize by severity (P0/P1/P2)
3. Check imports against package registries (PyPI, npm)
4. Run structural analysis — large files, circular deps, test coverage
5. Generate a structured audit report with fix plan
6. Offer to seed the SDD pipeline

Report compactly. Do not modify any files.
