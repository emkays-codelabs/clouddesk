import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPOS = ROOT / "backend" / "app" / "repositories"
BANNED = (
    "agents", "rag", "memory", "langchain", "langgraph", "openai", "anthropic", "litellm",
    "app.core.llm", "app.api", "app.services", "fastapi",
)  # fmt: skip


def _modules():
    files = sorted(REPOS.glob("*.py"))
    assert files
    return files


def _imports(path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_repositories_import_no_model_client_agents_or_http():
    for path in _modules():
        for name in _imports(path):
            for ban in BANNED:
                assert name != ban and not name.startswith(ban + "."), f"{path.name}: {name}"


def test_repositories_never_bypass_the_tenant_filter():
    for path in _modules():
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            attr = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            assert attr != "text", f"{path.name}: raw text() SQL"
            assert not (attr == "get" and isinstance(fn, ast.Attribute)
                        and isinstance(fn.value, ast.Attribute) and fn.value.attr == "session"
                        ), f"{path.name}: session.get"  # fmt: skip
            if attr == "execute" and node.args:
                assert not (
                    isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
                ), f"{path.name}: string SQL"


def test_no_layer_outside_repositories_names_tenant_id():
    folders = [ROOT / "backend" / "app" / sub for sub in ("api", "services", "tools")] + [
        ROOT / d for d in ("agents", "memory", "rag", "integrations")
    ]
    for folder in folders:
        if not folder.exists():
            continue
        for path in folder.rglob("*.py"):
            assert "tenant_id" not in path.read_text(encoding="utf-8"), str(path)
