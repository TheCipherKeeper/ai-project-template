import importlib.util
import json
import sys
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).with_name("run.py")
SPEC = importlib.util.spec_from_file_location("pipeline_run", MODULE_PATH)
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = pipeline
SPEC.loader.exec_module(pipeline)


def config(root: Path) -> None:
    (root / ".pipeline.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "lint": [[sys.executable, "-c", "print('lint')"]],
                "tests": [[sys.executable, "-c", "print('tests')"]],
                "build": {
                    "commands": [
                        [sys.executable, "-c", "from pathlib import Path; Path('dist').mkdir(exist_ok=True); Path('dist/app.txt').write_text('product')"]
                    ],
                    "outputs": ["dist"],
                },
                "deploy": [[sys.executable, "-c", "from pathlib import Path; assert Path(r'{artifact_dir}/dist/app.txt').read_text() == 'product'"]],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_build_artifact_and_deploy(tmp_path: Path) -> None:
    config(tmp_path)
    document = pipeline.load_config(tmp_path)

    pipeline.run_commands(document["lint"], tmp_path, {"commit": "abc1234"})
    build = document["build"]
    pipeline.run_commands(build["commands"], tmp_path, {"commit": "abc1234"})
    archive = pipeline.create_archive(tmp_path, build["outputs"])
    first = pipeline.sha256(archive)
    pipeline.create_archive(tmp_path, build["outputs"])
    assert pipeline.sha256(archive) == first
    assert pipeline.record_artifact(tmp_path, "abc1234") == first

    pipeline.deploy(document, tmp_path, "def5678", archive)


def test_review_requires_current_head_approval(tmp_path: Path) -> None:
    reviews = tmp_path / "reviews.json"
    reviews.write_text(
        json.dumps([{"state": "APPROVED", "commit_id": "abc1234", "user": {"login": "review-agent"}}]),
        encoding="utf-8",
    )

    pipeline.verify_review(reviews, "review-agent", "author-agent", "abc1234")

    try:
        pipeline.verify_review(reviews, "review-agent", "author-agent", "def5678")
    except pipeline.PipelineError:
        pass
    else:
        raise AssertionError("устаревшее одобрение не должно проходить")


def test_review_allows_same_account_as_author(tmp_path: Path) -> None:
    reviews = tmp_path / "reviews.json"
    reviews.write_text(
        json.dumps([{"state": "APPROVED", "commit_id": "abc1234", "user": {"login": "same-agent"}}]),
        encoding="utf-8",
    )
    # Та же учётная запись для автора и ревьюера допускается: независимость
    # даёт отдельная сессия агента-ревьюера, а не отдельная учётка.
    pipeline.verify_review(reviews, "same-agent", "same-agent", "abc1234")


def test_critical_review_accepts_agent_approval(tmp_path: Path) -> None:
    reviews = tmp_path / "reviews.json"
    reviews.write_text(
        json.dumps(
            [
                {"state": "APPROVED", "commit_id": "abc1234", "user": {"login": "review-agent"}},
            ]
        ),
        encoding="utf-8",
    )
    pipeline.verify_review(reviews, "review-agent", "author-agent", "abc1234")


def test_review_requires_configured_reviewer(tmp_path: Path) -> None:
    reviews = tmp_path / "reviews.json"
    reviews.write_text("[]", encoding="utf-8")

    with pytest.raises(pipeline.PipelineError, match="учётную запись ревьюера"):
        pipeline.verify_review(reviews, "", "author-agent", "abc1234")

    reviews.write_text(
        json.dumps(
            [
                {
                    "state": "APPROVED",
                    "commit_id": "abc1234",
                    "user": {"login": "review-agent"},
                }
            ]
        ),
        encoding="utf-8",
    )
    pipeline.verify_review(reviews, "review-agent", "author-agent", "abc1234")
