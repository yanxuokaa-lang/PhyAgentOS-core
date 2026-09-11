from pathlib import Path

from PhyAgentOS.agent.context import ContextBuilder


class _Skills:
    def get_always_skills(self):
        return []

    def get_active_skills(self):
        return []

    def load_skills_for_context(self, _names):
        return ""

    def build_skills_summary(self):
        return "pick-place-workflow (available=true)"


def test_forge_context_requires_explicit_skill_activation_even_without_evolution(tmp_path: Path):
    builder = ContextBuilder(
        tmp_path,
        forge_context_provider=lambda: "Runtime ready",
        evolution_enabled=False,
    )
    builder.skills = _Skills()
    prompt = builder.build_system_prompt()
    assert "use activate_skill with the exact Skill name" in prompt
    assert "read its SKILL.md file using the read_file tool" not in prompt


def test_non_forge_context_keeps_read_only_skill_guidance(tmp_path: Path):
    builder = ContextBuilder(tmp_path, evolution_enabled=False)
    builder.skills = _Skills()
    prompt = builder.build_system_prompt()
    assert "read its SKILL.md file using the read_file tool" in prompt
