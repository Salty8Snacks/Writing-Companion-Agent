"""Offline tests for the writing-companion agent.

Scripted-model tests need no API key: they verify agent configuration,
session plumbing with the bundled skill, and that the skill's grounding
claims match the actual reference files.
"""

import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from mistralai import agents

from main import INSTRUCTIONS, agent

SKILL_DIR = Path(__file__).resolve().parent.parent / "skills" / "writing-coach-references"
EXAMPLES = SKILL_DIR / "01_reference_examples_by_category.txt"
GUIDE = SKILL_DIR / "02_writing_coach_reference_guide.txt"


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """A test that forgets override() fails instead of calling the model."""
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_CLIENT_API_KEY", raising=False)


@pytest.fixture
def scripted_model() -> Iterator[agents.testing.ScriptedModel]:
    model = agents.testing.ScriptedModel(
        [agents.testing.reply("Coached answer, in the student's own voice.")]
    )
    yield model
    model.assert_consumed()


def test_agent_identity() -> None:
    assert agent.name == "writing-companion"


def test_instructions_cover_required_behaviors() -> None:
    normalized = " ".join(INSTRUCTIONS.split())
    for required in (
        "academic integrity",
        "never invent references",
        "cannot be verified",
        "student ownership",
        "coach instead",
    ):
        assert required.lower() in normalized.lower()


def test_skill_files_present() -> None:
    for path in (SKILL_DIR / "SKILL.md", EXAMPLES, GUIDE):
        assert path.is_file()


def test_skill_grounding_claims_match_files() -> None:
    """SKILL.md promises §1-§9 and 74 examples; the files must agree."""
    sections = {
        int(match) for match in re.findall(r"^## §(\d+)", GUIDE.read_text(), re.M)
    }
    assert sections == set(range(1, 10))

    example_ids = set(re.findall(r"^### Example (SWA-\d+)", EXAMPLES.read_text(), re.M))
    assert len(example_ids) == 74
    assert example_ids == set(re.findall(r"(SWA-\d+)", EXAMPLES.read_text()))


async def test_plain_reply_run(scripted_model: agents.testing.ScriptedModel) -> None:
    state = await agent.override(model=scripted_model).run("Explain 'analyze' vs 'summarize'.")
    assert isinstance(state, agents.Completed), state
    assert state.text == "Coached answer, in the student's own voice."


async def test_session_opens_with_bundled_skill(
    scripted_model: agents.testing.ScriptedModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WRITING_COMPANION_SANDBOX", "bashkit")
    local_agent = agents.Agent(
        model="mistral-large-4",
        name="writing-companion",
        environment=agents.BashkitSandbox(),
        skills=[agents.LocalSkillBundle.from_directory(SKILL_DIR)],
        instructions=INSTRUCTIONS,
    )

    session = await local_agent.override(model=scripted_model).start_session()
    try:
        state = await session.run("Help me narrow a topic.")
        assert isinstance(state, agents.Completed), state
    finally:
        await session.cancel()


def _build_with(be, completion, model: str) -> agents.Agent:
    return agents.Agent(
        model=model,
        name="writing-companion-test",
        completion=completion,
        environment=agents.BashkitSandbox(),
        skills=[agents.LocalSkillBundle.from_directory(SKILL_DIR)],
        instructions=INSTRUCTIONS,
    )


def test_default_provider_is_mistral(monkeypatch: pytest.MonkeyPatch) -> None:
    import main

    monkeypatch.delenv("WRITING_COMPANION_PROVIDER", raising=False)
    assert main._completion() is None
    assert main.agent.model == "mistral-large-4"


def test_ollama_provider_needs_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    import main

    monkeypatch.setenv("WRITING_COMPANION_PROVIDER", "ollama")
    config = main._completion()
    assert config.model == "mistral-small3.2"
    assert _build_with(main, config, config.model).model == "mistral-small3.2"


def test_gateway_provider_reads_named_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import main

    monkeypatch.setenv("WRITING_COMPANION_PROVIDER", "gateway")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key-for-construction-only")
    monkeypatch.setenv("WRITING_COMPANION_GATEWAY_MODEL", "gemini-3.8-flash")
    config = main._completion()
    assert config.model == "gemini-3.8-flash"
    assert _build_with(main, config, config.model).model == "gemini-3.8-flash"
