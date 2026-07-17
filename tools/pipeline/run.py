"""Исполнитель воспроизводимых стадий продуктового конвейера."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


POLICY_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = Path(".pipeline/product.zip")
MANIFEST = Path(".pipeline/artifact.json")
DIGEST = Path(".pipeline/product.zip.sha256")
PLACEHOLDER = "<"


class PipelineError(RuntimeError):
    """Ошибка конфигурации или выполнения продуктового конвейера."""


def load_config(root: Path) -> dict[str, object]:
    path = root / ".pipeline.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        schema = json.loads((POLICY_ROOT / "schemas/pipeline.schema.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PipelineError(f"не удалось прочитать конфигурацию: {error}") from error
    sys.path.insert(0, str(POLICY_ROOT / "tools" / "verify"))
    from verify import validate_json  # noqa: PLC0415

    errors = validate_json(document, schema)
    if errors:
        raise PipelineError("невалидная .pipeline.json: " + "; ".join(errors))
    if not isinstance(document, dict):
        raise PipelineError("корень .pipeline.json должен быть объектом")
    return document


def substitute(value: str, variables: dict[str, str]) -> str:
    if PLACEHOLDER in value and ">" in value:
        raise PipelineError(f"не заменён маркер первичной настройки: {value}")
    try:
        return value.format_map(variables)
    except KeyError as error:
        raise PipelineError(f"неизвестная переменная {{{error.args[0]}}}") from error


def run_commands(commands: object, root: Path, variables: dict[str, str]) -> None:
    if not isinstance(commands, list):
        raise PipelineError("список команд отсутствует")
    for raw in commands:
        if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
            raise PipelineError("каждая команда должна быть массивом строк")
        command = [substitute(item, variables) for item in raw]
        print("+ " + " ".join(command), flush=True)
        try:
            completed = subprocess.run(command, cwd=root, check=False)
        except OSError as error:
            raise PipelineError(f"команда недоступна: {command[0]}: {error}") from error
        if completed.returncode:
            raise PipelineError(f"команда завершилась с кодом {completed.returncode}: {command[0]}")


def output_files(root: Path, patterns: object) -> list[Path]:
    if not isinstance(patterns, list):
        raise PipelineError("build.outputs должен быть массивом")
    files: set[Path] = set()
    for pattern in patterns:
        if not isinstance(pattern, str):
            raise PipelineError("build.outputs содержит не строку")
        pattern = substitute(pattern, {})
        matches = [Path(item) for item in glob.glob(str(root / pattern), recursive=True)]
        if not matches:
            raise PipelineError(f"выход сборки не найден: {pattern}")
        for match in matches:
            if match.is_symlink():
                raise PipelineError(f"символьная ссылка запрещена в артефакте: {match}")
            resolved = match.resolve()
            if root.resolve() not in (resolved, *resolved.parents):
                raise PipelineError(f"выход сборки находится вне репозитория: {pattern}")
            if resolved.is_file():
                files.add(resolved)
            elif resolved.is_dir():
                for child in resolved.rglob("*"):
                    relative_parts = child.relative_to(root).parts
                    if ".git" in relative_parts or ".pipeline" in relative_parts:
                        continue
                    if child.is_symlink():
                        raise PipelineError(f"символьная ссылка запрещена в артефакте: {child}")
                    if child.is_file():
                        files.add(child.resolve())
    if not files:
        raise PipelineError("сборка не создала файлов для артефакта")
    return sorted(files)


def create_archive(root: Path, patterns: object) -> Path:
    archive = root / ARCHIVE
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        for source in output_files(root, patterns):
            relative = source.relative_to(root).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (source.stat().st_mode & 0xFFFF) << 16
            target.writestr(info, source.read_bytes(), compresslevel=9)
    return archive


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record_artifact(root: Path, commit: str) -> str:
    archive = root / ARCHIVE
    if not archive.is_file():
        raise PipelineError(f"артефакт сборки отсутствует: {ARCHIVE}")
    digest = sha256(archive)
    (root / DIGEST).write_text(f"{digest}  product.zip\n", encoding="utf-8")
    (root / MANIFEST).write_text(
        json.dumps(
            {"schema_version": 1, "commit": commit, "artifact": f"sha256:{digest}"},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"sha256:{digest}")
    return digest


def verify_review(
    path: Path,
    reviewer: str,
    author: str,
    head: str,
    labels_path: Path | None = None,
    human_reviewer: str = "",
) -> None:
    labels: set[str] = set()
    if labels_path is not None:
        try:
            label_document = json.loads(labels_path.read_text(encoding="utf-8"))
            labels = {
                item["name"]
                for item in label_document.get("labels", [])
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            }
        except (OSError, json.JSONDecodeError, AttributeError) as error:
            raise PipelineError(f"не удалось прочитать метки PR: {error}") from error
    if not reviewer or reviewer == author:
        raise PipelineError("AGENT_REVIEWER_LOGIN должен указывать отдельную учётную запись")
    try:
        reviews = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PipelineError(f"не удалось прочитать GitHub Reviews: {error}") from error
    approved = any(
        isinstance(review, dict)
        and review.get("state") == "APPROVED"
        and review.get("commit_id") == head
        and isinstance(review.get("user"), dict)
        and review["user"].get("login") == reviewer
        for review in reviews if isinstance(reviews, list)
    )
    if not approved:
        raise PipelineError(f"нет актуального APPROVED review от {reviewer} для {head}")
    if "risk:critical" in labels:
        if not human_reviewer or human_reviewer in {author, reviewer}:
            raise PipelineError("для risk:critical требуется отдельный HUMAN_REVIEWER_LOGIN")
        human_approved = any(
            isinstance(review, dict)
            and review.get("state") == "APPROVED"
            and review.get("commit_id") == head
            and isinstance(review.get("user"), dict)
            and review["user"].get("login") == human_reviewer
            for review in reviews
        )
        if not human_approved:
            raise PipelineError(f"risk:critical не имеет APPROVED review от {human_reviewer}")

def deploy(config: dict[str, object], root: Path, commit: str, artifact: Path) -> None:
    if not artifact.is_file():
        raise PipelineError(f"артефакт не найден: {artifact}")
    expected_path = artifact.with_name(artifact.name + ".sha256")
    if expected_path.is_file():
        expected = expected_path.read_text(encoding="utf-8").split()[0]
        if sha256(artifact) != expected:
            raise PipelineError("хеш загруженного артефакта не совпадает")
    destination = root / ".pipeline/deploy"
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    with zipfile.ZipFile(artifact) as source:
        for member in source.infolist():
            target = (destination / member.filename).resolve()
            if destination.resolve() not in (target, *target.parents):
                raise PipelineError(f"опасный путь в артефакте: {member.filename}")
        source.extractall(destination)
    variables = {
        "commit": commit,
        "artifact": str(artifact.resolve()),
        "artifact_dir": str(destination.resolve()),
    }
    run_commands(config["deploy"], root, variables)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("lint", "tests", "build", "artifact", "review", "deploy"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--commit", default="")
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--reviews", type=Path)
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--human-reviewer", default="")
    parser.add_argument("--author", default="")
    parser.add_argument("--labels", type=Path)
    try:
        args = parser.parse_args()
        root = args.root.resolve()
        if args.stage == "review":
            if args.reviews is None:
                raise PipelineError("для review требуется --reviews")
            verify_review(
                args.reviews,
                args.reviewer,
                args.author,
                args.commit,
                args.labels,
                args.human_reviewer,
            )
            return 0
        config = load_config(root)
        variables = {"commit": args.commit}
        if args.stage in {"lint", "tests"}:
            run_commands(config[args.stage], root, variables)
        elif args.stage == "build":
            build = config["build"]
            if not isinstance(build, dict):
                raise PipelineError("build должен быть объектом")
            run_commands(build["commands"], root, variables)
            create_archive(root, build["outputs"])
        elif args.stage == "artifact":
            record_artifact(root, args.commit)
        elif args.stage == "deploy":
            if args.artifact is None:
                raise PipelineError("для deploy требуется --artifact")
            deploy(config, root, args.commit, args.artifact.resolve())
    except PipelineError as error:
        print(f"Ошибка конвейера: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
