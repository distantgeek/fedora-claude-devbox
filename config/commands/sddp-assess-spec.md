@spec-assessor

You are starting a spec assessment workflow. Your sole purpose is to read a feature specification and flag issues that could cause hallucination, wasted effort, or incorrect implementation. Disregard any prior implementation context, code discussion, or task execution. Focus exclusively on spec quality.

## Input
`$ARGUMENTS` = If provided, the path to a spec file. Otherwise, find the current spec.

## Instructions
1. Find the spec — look in specs/ for the most recently modified spec.md, or use `$ARGUMENTS` if provided.
2. Read the full spec file.
3. Run the 6-point assessment framework from your agent definition.
4. Output the structured assessment report.

Report compactly. Do not modify any files.
