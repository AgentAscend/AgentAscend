# Skill: read_only_repo_scan

Purpose
- Inspect repository state without mutating source files.

Allowed commands
- `git status --short`
- `git log --oneline -n <N>`
- `git diff -- <path>`
- `python3 -m py_compile <file>`
- `python3 -m json.tool <file>`

Procedure
1) Fail-fast checks
- Stop if repo path is unknown.
- Stop if command requires write/delete.

2) Scan sequence
- Run `git status --short`.
- Run `git log --oneline -n 10`.
- For any target file, run `git diff -- <path>`.

3) Verification output
- Report modified files, untracked files, and latest commits.
- Report parse/compile status if checks were requested.

Rollback
- None required (read-only).
- If accidental writes occur, immediately stop and restore with `git checkout -- <path>` after user approval.
