import pytest

from core.language import SUPPORTED_LANGUAGES
from services.ai import prompts

FORMAT_FIELDS = [
    '"status"', '"severity"', '"title"', '"file_path"',
    '"description"', '"code_hint"', '"issues"',
]


def _all_prompts(language: str) -> dict[str, str]:
    return {
        "secrets": prompts.secrets_detection("CONTEXTE", language),
        "gitignore": prompts.gitignore_check("CONTEXTE", language),
        "quality": prompts.quality_check("CONTEXTE", language),
        "readme": prompts.readme_check("README", "CODE", language),
    }


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_every_prompt_carries_its_output_language_rule(language):
    expected = "en francais" if language == "fr" else "in English"

    for name, prompt in _all_prompts(language).items():
        assert expected in prompt, f"{name} ne fixe pas la langue de sortie"


def test_context_is_injected():
    for name, prompt in _all_prompts("fr").items():
        if name == "readme":
            assert "README" in prompt and "CODE" in prompt
        else:
            assert "CONTEXTE" in prompt, f"{name} n'injecte pas le contexte"


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_format_block_is_complete(language):
    for name, prompt in _all_prompts(language).items():
        assert "FORMAT :" in prompt
        for field in FORMAT_FIELDS:
            if name == "quality" and field == '"status"':
                continue
            assert field in prompt, f"{name} : champ {field} absent du FORMAT"


def test_recommendations_requested_where_expected():
    generated = _all_prompts("fr")

    assert '"recommendations"' in generated["secrets"]
    assert '"recommendations"' in generated["gitignore"]
    assert '"recommendations"' in generated["readme"]
    assert '"recommendations"' not in generated["quality"]


def test_strict_rules_survive():
    secrets = prompts.secrets_detection("CONTEXTE", "fr")

    assert "NE SIGNALE PAS les placeholders" in secrets
    assert "Si tu n'es pas certain a 90%+, NE SIGNALE PAS" in secrets
    assert "toute valeur litterale non placeholder EST un secret reel" in secrets


def test_quality_prompt_defers_to_linters():
    quality = prompts.quality_check("CONTEXTE", "fr")

    assert "c'est deja couvert par les linters" in quality
    assert "Maximum 3 issues" in quality
