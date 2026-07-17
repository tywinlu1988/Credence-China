"""promote.py 晋升脚本测试（建议4：版本声明单源化）。"""

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMOTE = ROOT / "scripts" / "promote.py"


def _load_promote():
    spec = importlib.util.spec_from_file_location("promote", PROMOTE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["promote"] = module
    spec.loader.exec_module(module)
    return module


OLD = "v0.8.0-release"
NEW = "v0.8.1-release"


def _fake_tree(tmp_path: Path) -> None:
    """覆盖每条规则的代表性假树：声明点 + 必须免疫的历史引用。"""
    (tmp_path / "dev" / "engine").mkdir(parents=True)
    (tmp_path / "dev" / "engine" / "engine-overview.md").write_text(
        "# 总览\n\n**版本**: v0.8.0-release | **日期**: 2026-07-10\n"
        "| **引擎版本** | 核心方法论文档 | v0.8.0-release | 说明 |\n"
        '| 独立体系，在文件头标注"对应引擎版本: v0.8.0-release" |\n'
        "| engine-overview.md | v0.8.0-release | 引擎架构总览 |\n"
        "| **0.8.0-release** | **2026-07-16** | 历史行不动 |\n",
        encoding="utf-8",
    )
    (tmp_path / "dev" / "engine" / "industry-framework.md").write_text(
        "**版本**: v0.8.0-release | **范式版本**: v1.0.0 | **日期**: 2026-07-10\n"
        "自 v0.8.0-release 起的叙述不动\n"
        "根据《传染理论基础》(v0.8.0-release)定义的范式映射\n"
        "confidence 在当前 v0.8.0-release 的计算中未被量化消费\n"
        "| v0.8.0-release（当前） | 自带历史表行不动 |\n",
        encoding="utf-8",
    )
    skills = tmp_path / "dev" / ".claude" / "skills"
    (skills / "fixed-income-credit-analysis" / "references").mkdir(parents=True)
    (skills / "fixed-income-credit-analysis" / "SKILL.md").write_text(
        "# Fixed Income Credit Analysis Engine v0.8.0-release\n", encoding="utf-8"
    )
    (skills / "fixed-income-credit-analysis" / "references" / "ref.md").write_text(
        "**版本**: v0.8.0-release\n", encoding="utf-8"
    )
    (skills / "credit-qa-verifier").mkdir(parents=True)
    (skills / "credit-qa-verifier" / "SKILL.md").write_text(
        "**对应引擎版本**: v0.8.0-release\n", encoding="utf-8"
    )
    (tmp_path / "dev").mkdir(exist_ok=True)
    (tmp_path / "dev" / "README.md").write_text(
        "**版本**: v0.8.0-release\n| **v0.8.0-release** | **2026-07-16** | 历史行不动 |\n",
        encoding="utf-8",
    )
    (tmp_path / "AGENTS.md").write_text("**引擎版本**：v0.8.0-release\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "**版本 Version** `v0.8.0-release`\n发行包在 `version/v0.8.0-release/`。\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text('version = "0.8.0"\n', encoding="utf-8")
    (tmp_path / "package.json").write_text('{"version": "0.8.0"}\n', encoding="utf-8")
    (tmp_path / "scripts").mkdir(exist_ok=True)
    (tmp_path / "scripts" / "consistency_check.py").write_text(
        'EXPECTED_VERSION = "v0.8.0-release"\n', encoding="utf-8"
    )
    (tmp_path / "scripts" / "build_dist.py").write_text(
        '    return m.group(1) if m else "v0.8.0-release"\n', encoding="utf-8"
    )
    (tmp_path / ".gitignore").write_text(
        "# 仅当前可安装包 version/v0.8.0-release/ 入库\nversion/*\n!version/v0.8.0-release/\n",
        encoding="utf-8",
    )
    (tmp_path / "dev" / "templates").mkdir(exist_ok=True)
    (tmp_path / "dev" / "templates" / "template-type13.html").write_text(
        "<!-- @engine-version: v0.8.0-release -->\n"
        "<span>报告版本：v0.8.0-release · Type 13 传染分析</span>\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "adapters").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "adapters" / "codex.md").write_text(
        "**引擎版本**：v0.8.0-release · **入口**：仓库根级 `AGENTS.md`\n",
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs" / "VERSION-MANAGEMENT.md").write_text(
        "**对应引擎版本**: v0.8.0-release\n"
        "（现为 `version/v0.8.0-release/`）\n"
        "（现为 `v0.8.0-release`）\n"
        "自 **v0.8.0-release** 起的叙述不动\n",
        encoding="utf-8",
    )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_apply_rules_rewrites_all_declaration_points(tmp_path):
    pm = _load_promote()
    _fake_tree(tmp_path)
    changes = pm.apply_rules(tmp_path, OLD, NEW, apply=True)
    assert changes, "no changes reported"
    overview = _read(tmp_path / "dev" / "engine" / "engine-overview.md")
    assert "**版本**: v0.8.1-release" in overview
    assert "| engine-overview.md | v0.8.1-release |" in overview
    assert "**引擎版本** | 核心方法论文档 | v0.8.1-release" in overview
    industry = _read(tmp_path / "dev" / "engine" / "industry-framework.md")
    assert industry.startswith("**版本**: v0.8.1-release")
    assert "《传染理论基础》(v0.8.1-release)定义" in industry, "跨文档引用未改写"
    assert "在当前 v0.8.1-release 的计算中" in industry, "当前版本叙述未改写"
    assert "# Fixed Income Credit Analysis Engine v0.8.1-release" in _read(
        tmp_path / "dev" / ".claude" / "skills" / "fixed-income-credit-analysis" / "SKILL.md"
    )
    assert "**版本**: v0.8.1-release" in _read(
        tmp_path / "dev" / ".claude" / "skills" / "fixed-income-credit-analysis" / "references" / "ref.md"
    )
    assert "**对应引擎版本**: v0.8.1-release" in _read(
        tmp_path / "dev" / ".claude" / "skills" / "credit-qa-verifier" / "SKILL.md"
    )
    assert _read(tmp_path / "dev" / "README.md").startswith("**版本**: v0.8.1-release")
    assert "**引擎版本**：v0.8.1-release" in _read(tmp_path / "AGENTS.md")
    readme = _read(tmp_path / "README.md")
    assert "`v0.8.1-release`" in readme and "version/v0.8.1-release/" in readme
    assert 'version = "0.8.1"' in _read(tmp_path / "pyproject.toml")
    assert '{"version": "0.8.1"}' in _read(tmp_path / "package.json")
    assert 'EXPECTED_VERSION = "v0.8.1-release"' in _read(
        tmp_path / "scripts" / "consistency_check.py"
    )
    assert 'else "v0.8.1-release"' in _read(tmp_path / "scripts" / "build_dist.py")
    assert "!version/v0.8.1-release/" in _read(tmp_path / ".gitignore")
    assert "仅当前可安装包 version/v0.8.1-release/ 入库" in _read(tmp_path / ".gitignore")
    templates = _read(tmp_path / "dev" / "templates" / "template-type13.html")
    assert "@engine-version: v0.8.1-release" in templates
    assert "报告版本：v0.8.1-release" in templates
    assert "**引擎版本**：v0.8.1-release" in _read(tmp_path / "docs" / "adapters" / "codex.md")
    vm = _read(tmp_path / "docs" / "VERSION-MANAGEMENT.md")
    assert "**对应引擎版本**: v0.8.1-release" in vm
    assert "`version/v0.8.1-release/`" in vm
    assert "（现为 `v0.8.1-release`）" in vm


def test_apply_rules_preserves_historical_references(tmp_path):
    pm = _load_promote()
    _fake_tree(tmp_path)
    pm.apply_rules(tmp_path, OLD, NEW, apply=True)
    overview = _read(tmp_path / "dev" / "engine" / "engine-overview.md")
    assert "| **0.8.0-release** |" in overview, "历史表行被误伤"
    assert "对应引擎版本: v0.8.0-release" in overview, "audits 约定示例被误伤"
    industry = _read(tmp_path / "dev" / "engine" / "industry-framework.md")
    assert "**范式版本**: v1.0.0" in industry, "范式版本被误伤"
    assert "自 v0.8.0-release 起的叙述不动" in industry, "叙述行被误伤"
    assert "| v0.8.0-release（当前） |" in industry, "自带历史表行被误伤"
    dev_readme = _read(tmp_path / "dev" / "README.md")
    assert "| **v0.8.0-release** | **2026-07-16** |" in dev_readme, "dev 历史表行被误伤"
    vm = _read(tmp_path / "docs" / "VERSION-MANAGEMENT.md")
    assert "自 **v0.8.0-release** 起的叙述不动" in vm, "加粗历史叙述被误伤"


def test_dry_run_reports_but_writes_nothing(tmp_path):
    pm = _load_promote()
    _fake_tree(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    changes = pm.apply_rules(tmp_path, OLD, NEW, apply=False)
    assert changes, "dry-run 也应报告改动"
    after = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after, "dry-run 落盘了"


def test_semver_derivation_and_validation():
    pm = _load_promote()
    assert pm.derive_semver("v0.8.1-release") == "0.8.1"
    assert pm.derive_semver("v1.0.0-alpha") == "1.0.0"
    for bad in ("0.8.1", "v0.8", "v0.8.1", "v0.8.1-RELEASE", ""):
        assert pm.derive_semver(bad) is None, bad


def test_detect_old_version_from_checker(tmp_path):
    pm = _load_promote()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "consistency_check.py").write_text(
        'EXPECTED_VERSION = "v0.7.3-beta"\n', encoding="utf-8"
    )
    assert pm.detect_old_version(tmp_path) == "v0.7.3-beta"


def test_real_tree_dry_run_reports_changes_and_stays_clean():
    pm = _load_promote()
    old = pm.detect_old_version(ROOT)

    def _status():
        return subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout

    before = _status()
    changes = pm.apply_rules(ROOT, old, "v9.9.9-release", apply=False)
    assert len(changes) > 30, f"真树改动数异常: {len(changes)}"
    assert _status() == before, "dry-run 改变了工作区"
