"""Work around mistralai-agents 1.1.2/1.1.3 local-skill failures on Windows.

The SDK validates skill paths as absolute with PurePath, whose Windows flavor
requires a drive letter: "/SKILL.md" and "/skills/<name>/SKILL.md" (the paths
the SDK builds itself) are rejected on Windows, raising
"Invalid skill metadata" and pydantic ValidationErrors during session startup.
Upstream has no fixed release yet (1.1.3 is current). This script patches the
installed copies to also accept POSIX-absolute paths, which every OS accepts.
Re-run after `uv sync` until the SDK ships the fix, then delete the script.
"""

import inspect

from pathlib import Path

from mistralai.vibe.harness.core import protocol as protocol_module
from mistralai.vibe.harness.runtime.capabilities import skills as skills_module
from mistralai.vibe.harness.app_server.session.models import (
    configuration as configuration_module,
)

CALLER_PATCH = (
    'path=f"/{_SKILL_ENTRY_FILE}"',
    'path="C:/" + _SKILL_ENTRY_FILE',
)
VALIDATOR_OLD = (
    "if not(PurePath(value).is_absolute()or PureWindowsPath(value).is_absolute())"
    ":raise ValueError('skill path must be absolute')"
)
VALIDATOR_NEW = (
    "if not(PurePath(value).is_absolute()or PureWindowsPath(value).is_absolute()"
    "or value.startswith('/')):raise ValueError('skill path must be absolute')"
)

files = [
    Path(inspect.getfile(skills_module)),
    Path(inspect.getfile(protocol_module)),
    Path(inspect.getfile(configuration_module)),
]

for path in files:
    source = path.read_text(encoding="utf-8")
    patched = source.replace(VALIDATOR_OLD, VALIDATOR_NEW)
    patched = patched.replace(CALLER_PATCH[0], CALLER_PATCH[1])
    if patched == source:
        already = VALIDATOR_NEW in source or CALLER_PATCH[1] in source
        print(f"{path.name}: {'already patched' if already else 'nothing to patch'}")
    else:
        compile(patched, str(path), "exec")
        path.write_text(patched, encoding="utf-8")
        print(f"patched {path.name}")
