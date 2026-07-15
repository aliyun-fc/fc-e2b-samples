# Errors

Command failures and integration errors.

---

## [ERR-20260714-002] uv_lock

**Logged**: 2026-07-14T00:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: config

### Summary
Renaming a Python project to the exact name of one of its dependencies made dependency resolution self-referential.

### Error
```
Because your project depends on itself at an incompatible version
(e2b-code-interpreter==2.7.0), we can conclude that your project's
requirements are unsatisfiable.
```

### Context
- Operation: `uv lock --offline` in the renamed Code Interpreter demo.
- Cause: project name was set to `e2b-code-interpreter`, matching the third-party SDK dependency.

### Suggested Fix
Keep the directory name capability-oriented, but give the local Python package a distinct name such as `e2b-code-interpreter-demo`.

### Metadata
- Reproducible: yes
- Related Files: e2b-code-interpreter/pyproject.toml

### Resolution
- **Resolved**: 2026-07-14T00:00:00+08:00
- **Notes**: Renamed the local project metadata before rebuilding the lockfile.

---

## [ERR-20260714-003] validation_workdir

**Logged**: 2026-07-14T00:00:00+08:00
**Priority**: low
**Status**: resolved
**Area**: tests

### Summary
Cross-demo validation used repository-relative paths while its working directory was a child demo.

### Error
```
rg: e2b-browser-cdp: No such file or directory
```

### Context
- Operation: post-rename validation after rebuilding the Code Interpreter lockfile.
- Cause: the command ran from `e2b-code-interpreter/`, while validation paths assumed the repository root.

### Suggested Fix
Run cross-project checks from the workspace root, or use absolute paths.

### Metadata
- Reproducible: yes
- Related Files: none

### Resolution
- **Resolved**: 2026-07-14T00:00:00+08:00
- **Notes**: Re-ran the validation from the repository root.

---

## [ERR-20260714-004] playwright_process_group

**Logged**: 2026-07-14T00:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: tests

### Summary
Playwright CDP teardown could terminate the caller's shared terminal process group before cleanup output was emitted.

### Error
```
The demo consistently stopped after "--- Playwright CDP case ---" without an
exit status or final sandbox cleanup line.
```

### Context
- E2B template build, sandbox creation, browsertool health probe, and internal WebSocket handshake had already succeeded.
- A detached Playwright child process successfully connected with `X-Access-Token`, opened example.com, and read the title.

### Suggested Fix
Run Playwright verification in a child process with `start_new_session=True`, capture its output, and keep sandbox cleanup in the parent process.

### Metadata
- Reproducible: yes
- Related Files: e2b-browser-cdp/browser_sandbox_demo.py

### Resolution
- **Resolved**: 2026-07-14T00:00:00+08:00
- **Notes**: Implemented isolated Playwright verification and confirmed the CDP flow succeeds.

---

## [ERR-20260714-005] validation_python_path

**Logged**: 2026-07-14T00:00:00+08:00
**Priority**: low
**Status**: resolved
**Area**: tests

### Summary
The final syntax check referenced a demo-local virtualenv from the repository root.

### Error
```
zsh: no such file or directory: .venv/bin/python
```

### Context
- Operation: compile check for `e2b-browser-cdp/browser_sandbox_demo.py`.
- Cause: `.venv` is located inside the demo directory, not at the repository root.

### Suggested Fix
Use the demo-local absolute/relative Python path when running cross-project validation from the root.

### Metadata
- Reproducible: yes
- Related Files: e2b-browser-cdp/.venv/bin/python

### Resolution
- **Resolved**: 2026-07-14T00:00:00+08:00
- **Notes**: Re-ran the check using the correct demo-local interpreter path.

---

## [ERR-20260714-006] disk_usage_alias

**Logged**: 2026-07-14T00:00:00+08:00
**Priority**: low
**Status**: resolved
**Area**: config

### Summary
The `du` command resolved to a wrapper that attempted to invoke an unavailable `rtk` command.

### Error
```
zsh: command not found: rtk
```

### Context
- Operation: inspect untracked directory sizes before staging a commit.
- Environment: local zsh command aliases/wrappers.

### Suggested Fix
Use `/usr/bin/du` explicitly when checking directory size in this environment.

### Metadata
- Reproducible: yes
- Related Files: none

### Resolution
- **Resolved**: 2026-07-14T00:00:00+08:00
- **Notes**: Commit staging uses explicit paths and does not rely on the affected wrapper.

---

## [ERR-20260714-007] git_add_pathspec

**Logged**: 2026-07-14T00:00:00+08:00
**Priority**: low
**Status**: resolved
**Area**: config

### Summary
The initial staging command included renamed directories that had been untracked before the rename, so their old paths did not exist for Git.

### Error
```
fatal: pathspec 'browseruse-e2b-demo' did not match any files
```

### Context
- Operation: stage the rename and scaffold commit.
- Cause: only the originally tracked directories need their old paths staged as deletions; previously untracked directories do not.

### Suggested Fix
Stage tracked old paths and all new target directories explicitly, excluding nonexistent former untracked paths.

### Metadata
- Reproducible: yes
- Related Files: none

### Resolution
- **Resolved**: 2026-07-14T00:00:00+08:00
- **Notes**: Corrected the explicit staging list.

---

## [ERR-20260714-008] git_add_ignored_file

**Logged**: 2026-07-14T00:00:00+08:00
**Priority**: low
**Status**: resolved
**Area**: config

### Summary
Restoring a previously tracked `.python-version` file at its renamed path was blocked by an ignore rule.

### Error
```
The following paths are ignored by one of your .gitignore files:
e2b-code-interpreter/.python-version
```

### Context
- Operation: preserve the Code Interpreter demo's Python-version constraint during the directory rename.
- Cause: a root ignore rule matches `.python-version`, despite the file having been tracked at its old path.

### Suggested Fix
Use `git add -f` for this intentional tracked-file rename.

### Metadata
- Reproducible: yes
- Related Files: e2b-code-interpreter/.python-version

### Resolution
- **Resolved**: 2026-07-14T00:00:00+08:00
- **Notes**: Force-added the restored version file as part of the rename commit.

---

## [ERR-20260714-001] file_search

**Logged**: 2026-07-14T00:00:00+08:00
**Priority**: low
**Status**: resolved
**Area**: config

### Summary
The `rg` shell command resolved to a grep-compatible wrapper and rejected the `--files` option.

### Error
```
grep: option `--files' is ambiguous
```

### Context
- Command attempted: `rg --files ...`
- Environment: macOS zsh workspace
- Resolution: use the Codex-bundled ripgrep binary at its absolute path.

### Suggested Fix
Use the absolute ripgrep binary for repository file discovery in this environment.

### Metadata
- Reproducible: yes
- Related Files: none

### Resolution
- **Resolved**: 2026-07-14T00:00:00+08:00
- **Notes**: Subsequent repository searches used the bundled ripgrep binary.

---

## [ERR-20260714-002] file_search

**Logged**: 2026-07-14T10:35:00+08:00
**Priority**: low
**Status**: resolved
**Area**: config

### Summary
The shell `find` command resolved to an RTK wrapper that rejects compound predicates.

### Error
```
rtk find does not support compound predicates or actions (e.g. -not, -exec).
```

### Context
- Command attempted: `find .. -name AGENTS.md -o -name RTK.md`
- Environment: macOS zsh workspace
- Resolution: use `/usr/bin/find` when repository discovery needs standard find predicates.

### Suggested Fix
Use the system binary explicitly for compound file-discovery queries in this workspace.

### Metadata
- Reproducible: yes
- Related Files: none

### Resolution
- **Resolved**: 2026-07-14T10:35:00+08:00
- **Notes**: Migration checks used `/usr/bin/find`.

---
