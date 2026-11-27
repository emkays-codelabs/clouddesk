"""P14-2: static checks on the Dockerfiles (N8).

These read the files as text. They do NOT prove an image builds or reports healthy: that needs a
running Docker daemon and is checked separately.
"""

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8").replace("\r\n", "\n")


def _instructions(text: str) -> list[str]:
    """Dockerfile instructions with line continuations joined and comments dropped."""
    joined = re.sub(r"\\\n", " ", text)
    return [
        ln.strip() for ln in joined.splitlines() if ln.strip() and not ln.strip().startswith("#")
    ]


DOCKERFILES = {"backend": "backend/Dockerfile", "frontend": "frontend/Dockerfile"}
HEALTH_PATH = {"backend": "/health/live", "frontend": "/api/health"}
BASE = {"backend": "python:3.12-slim", "frontend": "node:22-alpine"}


@pytest.fixture(params=sorted(DOCKERFILES))
def image(request):
    name = request.param
    text = _read(DOCKERFILES[name])
    return name, text, _instructions(text)


def test_is_multi_stage(image):
    _, _, ins = image
    assert sum(1 for i in ins if i.upper().startswith("FROM ")) >= 2


def test_every_stage_uses_the_pinned_base_image(image):
    name, _, ins = image
    froms = [i.split()[1] for i in ins if i.upper().startswith("FROM ")]
    assert froms and all(f == BASE[name] for f in froms)


def test_final_stage_runs_as_a_non_root_user(image):
    _, _, ins = image
    users = [i.split(None, 1)[1] for i in ins if i.upper().startswith("USER ")]
    assert users and users[-1] == "app"
    last_from = max(n for n, i in enumerate(ins) if i.upper().startswith("FROM "))
    assert any(i.upper().startswith("USER ") for i in ins[last_from:])


def test_healthcheck_targets_the_right_path(image):
    name, _, ins = image
    health = [i for i in ins if i.upper().startswith("HEALTHCHECK ")]
    assert len(health) == 1
    assert HEALTH_PATH[name] in health[0]
    assert "curl" not in health[0]


def test_base_images_carry_the_pin_by_digest_reminder(image):
    _, text, ins = image
    n_from = sum(1 for i in ins if i.upper().startswith("FROM "))
    assert text.lower().count("pin by digest before production") >= n_from


def test_no_secrets_and_no_env_files_are_baked_in(image):
    _, text, ins = image
    for i in ins:
        if i.upper().startswith("COPY") or i.upper().startswith("ADD"):
            assert ".env" not in i
        if i.upper().startswith(("ENV ", "ARG ")):
            assert not re.search(r"KEY|SECRET|TOKEN|PASSWORD", i, re.I), i
    assert not re.search(r"sk-[A-Za-z0-9]{10,}|BEGIN [A-Z ]*PRIVATE KEY", text)


def test_backend_installs_from_the_lock_and_starts_uvicorn():
    ins = _instructions(_read("backend/Dockerfile"))
    assert any("uv sync" in i and "--frozen" in i and "--no-dev" in i for i in ins)
    cmd = [i for i in ins if i.upper().startswith("CMD ")]
    assert len(cmd) == 1 and "uvicorn" in cmd[0] and "app.main:app" in cmd[0] and "8000" in cmd[0]
    env = " ".join(i for i in ins if i.upper().startswith("ENV "))
    assert "/app/backend" in env and "PYTHONPATH" in env


def test_backend_copies_only_paths_that_exist_and_makes_data_writable():
    ins = _instructions(_read("backend/Dockerfile"))
    copied = [
        i.split()[-2].rstrip("/")
        for i in ins
        if i.upper().startswith("COPY ")
        and "--from" not in i
        and not i.split()[-2].endswith(".lock")
    ]
    for src in copied:
        if src.startswith("--") or src in {"pyproject.toml", "uv.lock"}:
            continue
        assert (ROOT / src).exists(), f"COPY source {src} does not exist"
    assert any("mkdir -p /app/data" in i and "chown app:app" in i and "/app/data" in i for i in ins)


def test_frontend_takes_the_api_url_as_a_build_arg_and_copies_standalone():
    ins = _instructions(_read("frontend/Dockerfile"))
    assert any(i.startswith("ARG NEXT_PUBLIC_API_URL") for i in ins)
    assert any(".next/standalone" in i for i in ins)
    assert any(i.startswith("CMD") and "server.js" in i for i in ins)
    assert 'output: "standalone"' in _read("frontend/next.config.mjs")


def test_root_dockerignore_excludes_secrets_and_local_data():
    lines = {ln.strip() for ln in _read(".dockerignore").splitlines()}
    assert {".env", ".env.*", "data/", ".git", ".venv", "node_modules"} <= lines
    assert "!.env.example" in lines


def test_frontend_dockerignore_excludes_env_and_build_output():
    lines = {ln.strip() for ln in _read("frontend/.dockerignore").splitlines()}
    assert {".env", ".env.*", "node_modules", ".next"} <= lines


def test_backend_image_copies_the_agents_and_memory_packages():
    copies = [
        i for i in _instructions(_read("backend/Dockerfile")) if i.upper().startswith("COPY ")
    ]
    for pkg in ("agents", "memory"):
        assert any(f"{pkg}/" in c and f"./{pkg}/" in c for c in copies), pkg
        assert (ROOT / pkg).is_dir()


def test_backend_image_copies_the_integrations_package_the_tools_import():
    # backend/app/tools imports `integrations`; without this COPY the image fails at import time.
    copies = [
        i for i in _instructions(_read("backend/Dockerfile")) if i.upper().startswith("COPY ")
    ]
    assert any("integrations/" in c and "./integrations/" in c for c in copies)
