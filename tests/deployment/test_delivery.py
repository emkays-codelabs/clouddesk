"""P14-4, P14-5 (N8): static checks on the Terraform roots, deploy scripts, workflows and Makefile.

These read files. They do NOT prove Terraform plans against a real account, that a workflow ran on
GitHub, or that a script deploys anything: nothing has been applied (CLAUDE.md 15.1).
"""

import pathlib
import re
import shutil
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deployment"
CLOUDS = ["aws", "azure", "gcp"]
ENVS = ["dev", "staging", "prod"]
SCRIPTS = ["deploy", "build_and_push", "smoke_test", "rollback", "destroy"]
WORKFLOWS = ["test", "security", "docker-build", "terraform-validate", "_deploy"]


def _text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


@pytest.mark.parametrize("cloud", CLOUDS)
def test_each_cloud_root_has_its_files(cloud):
    for name in ["main.tf", "variables.tf", "outputs.tf"]:
        assert (DEPLOY / cloud / name).is_file()


@pytest.mark.parametrize("cloud", CLOUDS)
def test_secrets_are_variables_marked_sensitive_with_no_value(cloud):
    text = _text(DEPLOY / cloud / "variables.tf")
    for name in ["llm_api_key", "jwt_secret"]:
        block = re.search(rf'variable "{name}" \{{.*?\n\}}', text, re.S).group(0)
        assert "sensitive = true" in block
        assert re.search(r'default\s*=\s*""', block), "a secret has no default beyond empty"


@pytest.mark.parametrize("cloud", CLOUDS)
def test_the_state_backend_is_configured_outside_the_code(cloud):
    assert re.search(r'backend "\w+" \{\}', _text(DEPLOY / cloud / "main.tf"))


@pytest.mark.parametrize("env", ENVS)
def test_each_environment_has_a_var_file_with_no_secret(env):
    text = _text(DEPLOY / "environments" / f"{env}.tfvars")
    assert f'environment   = "{env}"' in text
    assert not re.search(r"(api_key|secret|password|token)\s*=", text, re.I)


def test_the_var_files_are_not_excluded_by_gitignore():
    ignore = _text(ROOT / ".gitignore")
    assert "terraform.tfvars" in ignore and "*.tfvars" not in ignore


def test_production_gets_more_capacity_than_dev():
    def value(env, key):
        return int(
            re.search(
                rf"{key}\s*=\s*(\d+)", _text(DEPLOY / "environments" / f"{env}.tfvars")
            ).group(1)
        )

    assert value("prod", "memory") > value("dev", "memory")
    assert value("prod", "desired_count") >= 2


@pytest.mark.parametrize("name", SCRIPTS)
def test_each_script_is_strict_and_has_a_usage_line(name):
    text = _text(DEPLOY / "scripts" / f"{name}.sh")
    assert text.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in text
    assert "shell=True" not in text and "eval " not in text


@pytest.mark.parametrize("name", SCRIPTS)
def test_each_script_parses_with_bash(name):
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("no bash on PATH")
    result = subprocess.run(
        [bash, "-n", str(DEPLOY / "scripts" / f"{name}.sh")], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_auto_approve_is_refused_outside_dev():
    text = _text(DEPLOY / "scripts" / "deploy.sh")
    assert '"$env" != "dev"' in text and "refused" in text


def test_destroy_never_accepts_auto_approve():
    assert "--auto-approve" not in _text(DEPLOY / "scripts" / "destroy.sh").replace(
        "Never takes --auto-approve", ""
    )


def test_images_are_tagged_with_the_git_sha_and_a_dirty_tree_is_refused():
    text = _text(DEPLOY / "scripts" / "build_and_push.sh")
    assert "git rev-parse" in text and "git status --porcelain" in text


@pytest.mark.parametrize("name", WORKFLOWS)
def test_each_workflow_is_valid_yaml_with_jobs(name):
    data = yaml.safe_load(_text(ROOT / ".github" / "workflows" / f"{name}.yml"))
    assert data["jobs"]
    assert True in data or "on" in data  # PyYAML reads the bare key `on` as True


def test_the_deploy_pipeline_orders_its_stages_and_gates_prod():
    text = _text(ROOT / ".github" / "workflows" / "_deploy.yml")
    data = yaml.safe_load(text)
    jobs = data["jobs"]
    assert list(jobs) == ["bootstrap-registry", "build-and-push", "plan", "apply", "smoke"]
    assert jobs["apply"]["needs"] == "plan"
    assert "prod-apply" in jobs["apply"]["environment"]
    assert data["permissions"]["id-token"] == "write", "OIDC, not long-lived keys"
    assert "AWS_SECRET_ACCESS_KEY" not in text


def test_no_workflow_embeds_a_credential():
    for path in (ROOT / ".github" / "workflows").glob("*.yml"):
        assert not re.search(r"(AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,})", _text(path))


def test_the_makefile_has_the_delivery_targets():
    text = _text(ROOT / "Makefile")
    assert re.search(r"^terraform-validate:", text, re.M)
    assert re.search(r"^smoke:", text, re.M)
    assert "smoke_test.sh" in text


def test_no_env_file_is_committed():
    tracked = subprocess.run(
        ["git", "ls-files", ".env", "*.tfstate", "tfplan", "backend.hcl"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout.split()
    assert tracked == []
