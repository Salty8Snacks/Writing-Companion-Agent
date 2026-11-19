"""Work around mistralai-agents 1.1.2/1.1.3 local-skill failure on Windows.

The SDK validates every local skill path with PurePath, which follows Windows
semantics on Windows: "/SKILL.md" is not absolute without a drive letter, so
any local skill raises "Invalid skill metadata". Upstream has no fixed release
yet (1.1.3 is current). This script patches the installed copy to embed a
drive-absolute path, which validates on every OS. Re-run after `uv sync` until
the SDK ships the fix, then delete the script.
"""

import inspect

from mistralai.vibe.harness.runtime.capabilities import skills as skills_module

from pathlib import Path

SKILLS_FILE = Path(inspect.getfile(skills_module))
PATCH = (
    'path=f"/{_SKILL_ENTRY_FILE}"',
    'path="C:/" + _SKILL_ENTRY_FILE',
)

source = SKILLS_FILE.read_text(encoding="utf-8")
if PATCH[0] in source:
    SKILLS_FILE.write_text(source.replace(PATCH[0], PATCH[1]), encoding="utf-8")
    print(f"patched {SKILLS_FILE}")
else:
    if PATCH[1] not in source:
        raise SystemExit(
            f"pattern not found in {SKILLS_FILE}; the SDK may have changed - "
            "check whether a fixed mistralai-agents release exists"
        )
    print("already patched")
