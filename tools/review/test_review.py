import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = Path(__file__).with_name("review.py")
SPEC = importlib.util.spec_from_file_location("review_runner", MODULE_PATH)
review = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = review
SPEC.loader.exec_module(review)


def environment() -> dict[str, str]:
    return {
        "REVIEW_MODEL_PROVIDER": "ollama",
        "REVIEW_MODEL_BASE_URL": "http://localhost:11434",
        "REVIEW_MODEL_ID": "model",
        "REVIEW_GITHUB_TOKEN": "token",
        "REVIEW_GITHUB_REPOSITORY": "owner/repository",
        "REVIEW_GITHUB_REVIEWER_LOGIN": "reviewer[bot]",
    }


def test_settings_load_env_and_process_override(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "REVIEW_MODEL_PROVIDER=openai\n"
        "REVIEW_MODEL_BASE_URL=https://model.example/v1\n"
        "REVIEW_MODEL_API_KEY=file-key\n"
        "REVIEW_MODEL_ID=file-model\n"
        "REVIEW_GITHUB_TOKEN=file-token\n"
        "REVIEW_GITHUB_REPOSITORY=owner/repository\n"
        "REVIEW_GITHUB_REVIEWER_LOGIN=reviewer[bot]\n",
        encoding="utf-8",
    )
    process = environment()
    process["REVIEW_MODEL_ID"] = "process-model"

    settings = review.Settings.load(env_file, environ=process)

    assert settings.model_provider == "ollama"
    assert settings.model_id == "process-model"
    assert settings.model_base_url == "http://localhost:11434"
    assert "github_token=" not in repr(settings)
    assert "model_api_key=" not in repr(settings)


def test_openai_provider_requires_api_key(tmp_path: Path) -> None:
    values = environment()
    values.update(
        {
            "REVIEW_MODEL_PROVIDER": "openai",
            "REVIEW_MODEL_BASE_URL": "https://model.example/v1",
            "REVIEW_MODEL_API_KEY": "",
        }
    )

    try:
        review.Settings.load(tmp_path / "missing", environ=values)
    except review.ReviewError as error:
        assert "REVIEW_MODEL_API_KEY" in str(error)
    else:
        raise AssertionError("openai без API key не должен проходить")


def test_checks_require_all_successful() -> None:
    runs = [
        {"name": "policy", "status": "completed", "conclusion": "success"},
        {"name": "lint", "status": "completed", "conclusion": "success"},
        {"name": "tests", "status": "completed", "conclusion": "success"},
    ]

    assert review.checks_passed(runs, ("policy", "lint", "tests"))
    runs[-1]["conclusion"] = "failure"
    assert not review.checks_passed(runs, ("policy", "lint", "tests"))


def test_only_current_final_review_suppresses_run() -> None:
    reviews = [
        {
            "commit_id": "a" * 40,
            "state": "APPROVED",
            "user": {"login": "reviewer[bot]"},
        }
    ]

    assert review.already_reviewed(reviews, "reviewer[bot]", "a" * 40)
    assert not review.already_reviewed(reviews, "reviewer[bot]", "b" * 40)


def test_render_review_contains_evidence() -> None:
    decision = SimpleNamespace(
        summary="Найден дефект.",
        findings=[
            SimpleNamespace(
                severity="high",
                file="src/app.py",
                line=42,
                problem="Проверка отсутствует",
                evidence="Тест принимает запрещённое значение",
                reproduction="pytest tests/test_app.py",
            )
        ],
    )

    rendered = review.render_review(decision)

    assert "`src/app.py:42`" in rendered
    assert "Свидетельство: Тест принимает запрещённое значение" in rendered


def test_file_reader_decodes_github_base64_with_line_breaks() -> None:
    settings = review.Settings.load(Path("missing"), environ=environment())

    class Client(review.GitHubClient):
        def request(self, method, path, **kwargs):
            return {"type": "file", "content": "cHJpbnQo\nJ29rJyk="}

    assert Client(settings).file("src/app.py", "a" * 40) == "print('ok')"


def test_diff_size_is_limited() -> None:
    values = environment()
    values["REVIEW_MAX_DIFF_BYTES"] = "3"
    settings = review.Settings.load(Path("missing"), environ=values)

    class Client(review.GitHubClient):
        def request(self, method, path, **kwargs):
            return "large"

    try:
        Client(settings).diff(1)
    except review.ReviewError as error:
        assert "REVIEW_MAX_DIFF_BYTES" in str(error)
    else:
        raise AssertionError("слишком большой diff не должен проходить")
