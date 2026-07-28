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
        "| **0.8.0-release** | **2026-07-16** | 历史行不动 |\n"
        "\n## 六、版本历史\n\n"
        "| 版本 | 日期 | 变更内容 |\n|---|---|---|\n"
        "| **0.8.0-release** | **2026-07-16** | 历史行不动 |\n"
        "\n---\n\n## 七、版本管理策略\n",
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
    (tmp_path / "dev" / "engine" / "systemic-warning-framework.md").write_text(
        "**版本**: v0.8.0-release | **日期**: 2026-07-10 | **状态**: 已发布\n"
        "### 11.3 版本演进路线\n\n"
        "| 版本 | 计划内容 |\n|------|---------|\n"
        "| v0.7.0-alpha | 旧行 |\n"
        "| v0.8.0-release（当前） | 旧当前行（本框架与阈值无变更） |\n"
        "| v0.10.3（规划） | 未来行：SRI 时间序列 |\n",
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
        "**版本**: v0.8.0-release\n"
        "## 版本历史\n\n"
        "| 版本 | 日期 | 里程碑 |\n|---|---|---|\n"
        "| **v0.8.0-release** | **2026-07-16** | 历史行不动 |\n"
        "\n> **注**：尾注行。\n",
        encoding="utf-8",
    )
    (tmp_path / "AGENTS.md").write_text("**引擎版本**：v0.8.0-release\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "**版本 Version** `v0.8.0-release`\n发行包在 `version/v0.8.0-release/`。\n"
        "### 路线图\n\n"
        "- ~~**v0.8.0**~~（已发布）：旧版。\n"
        "- **v0.8.1（规划中）**：待发布功能。\n"
        "### Roadmap\n\n"
        "- **v0.8.1 (planned)**: upcoming feature.\n",
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
    changes = pm.apply_rules(tmp_path, OLD, NEW, apply=True, note="测试说明", tests=999)
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
    pm.apply_rules(tmp_path, OLD, NEW, apply=True, note="测试说明", tests=999)
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


def test_real_tree_dry_run_includes_history_sync_points():
    """植入-还原门：真树 dry-run 必含 4 同步点 + 占位形态 + 工作区不变。"""
    pm = _load_promote()
    old = pm.detect_old_version(ROOT)

    def _status():
        return subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout

    before = _status()
    hints = []
    changes = pm.apply_rules(ROOT, old, "v9.9.9-release", apply=False, hints=hints)
    rule_ids = {c.rule_id for c in changes}
    assert "dev-readme-history" in rule_ids, "真树 dry-run 缺同步点: dev-readme-history"
    assert "overview-history" in rule_ids, "真树 dry-run 缺同步点: overview-history"
    assert "systemic-history" in rule_ids, "真树 dry-run 缺同步点: systemic-history"
    # dry-run 占位形态（未传 note/tests）
    hist = [c for c in changes if c.rule_id == "dev-readme-history"]
    assert "〈note〉" in hist[0].new_line and "〈N〉" in hist[0].new_line
    # 真树无 v9.9.9（规划中）行 → roadmap-flip 无 changes 但 hints 非空
    assert "roadmap-flip" not in rule_ids
    assert any("v9.9.9" in h for h in hints), "无匹配规划行应有提示"

    # 真树路线图中首个（规划中）版本 → 双语翻转各一条（版本无关：目标随路线图滚动）
    import re as _re

    planned = _re.search(r"\*\*v(\d+\.\d+\.\d+)（规划中）\*\*", (ROOT / "README.md").read_text(encoding="utf-8"))
    assert planned, "真树 README 路线图无（规划中）行"
    target_semver = planned.group(1)
    changes2 = pm.apply_rules(ROOT, old, f"v{target_semver}-release", apply=False, hints=[])
    flip = [c for c in changes2 if c.rule_id == "roadmap-flip"]
    assert len(flip) == 2, f"双语翻转应各一条: {len(flip)}"
    assert any(f"~~**v{target_semver}**~~（已发布）" in c.new_line for c in flip)
    assert any(f"~~**v{target_semver}**~~ (released)" in c.new_line for c in flip)

    assert _status() == before, "dry-run 改变了工作区"


def test_sanitize_note_rejects_illegal_content():
    pm = _load_promote()
    for bad in ("含\n换行", "含\r回车", "引用 dev/README 路径", "自带（当前）标记", "含|竖线"):
        try:
            pm.sanitize_note(bad)
        except ValueError:
            continue
        raise AssertionError(f"未拒绝: {bad!r}")
    assert pm.sanitize_note("扫尾清单机制化：promote 自动补历史行") == "扫尾清单机制化：promote 自动补历史行"


def test_apply_requires_note_and_tests(tmp_path):
    pm = _load_promote()
    _fake_tree(tmp_path)
    for kwargs in (dict(note=None, tests=217), dict(note="说明", tests=None), dict(note="说明", tests=0)):
        try:
            pm.apply_rules(tmp_path, OLD, NEW, apply=True, **kwargs)
        except ValueError:
            continue
        raise AssertionError(f"缺参未拒绝: {kwargs}")


def test_apply_rules_sanitizes_note_internally(tmp_path):
    """直接调用 apply_rules 也拒绝非法 note（不依赖 main() 前置消毒）。"""
    pm = _load_promote()
    _fake_tree(tmp_path)
    try:
        pm.apply_rules(tmp_path, OLD, NEW, apply=True, note="含|竖线", tests=1)
    except ValueError:
        return
    raise AssertionError("apply_rules 未内部消毒 note")


def test_history_rows_dev_readme_and_overview(tmp_path):
    pm = _load_promote()
    _fake_tree(tmp_path)
    pm.apply_rules(tmp_path, OLD, NEW, apply=True, note="测试说明", tests=999)
    dev = _read(tmp_path / "dev" / "README.md")
    assert "| **v0.8.1-release** | **" in dev
    assert "| **v0.8.1-release** | **2" in dev and "测试说明。999 项测试通过。** |" in dev
    # 新行在旧行之后、尾注之前（定位带 "| **" 前缀以跳过文件头 **版本** 行）
    assert dev.index("历史行不动") < dev.index("| **v0.8.1-release**") < dev.index("尾注行")
    overview = _read(tmp_path / "dev" / "engine" / "engine-overview.md")
    assert "| **0.8.1-release** | **" in overview  # 无 v 前缀
    assert "测试说明（本框架与阈值无变更）。999 项测试通过** |" in overview
    assert overview.index("历史行不动") < overview.index("| **0.8.1-release**") < overview.index("## 七")


def test_history_rows_framework_changed_flag(tmp_path):
    pm = _load_promote()
    _fake_tree(tmp_path)
    pm.apply_rules(tmp_path, OLD, NEW, apply=True, note="测试说明", tests=999, framework_changed=True)
    overview = _read(tmp_path / "dev" / "engine" / "engine-overview.md")
    section = overview.split("## 六、版本历史")[1].split("## 七")[0]
    new_row = next(l for l in section.splitlines() if "0.8.1-release" in l)
    assert "测试说明。999 项测试通过** |" in new_row
    assert "本框架与阈值无变更" not in new_row


def test_systemic_history_row_and_marker_migration(tmp_path):
    pm = _load_promote()
    _fake_tree(tmp_path)
    pm.apply_rules(tmp_path, OLD, NEW, apply=True, note="测试说明", tests=999)
    text = _read(tmp_path / "dev" / "engine" / "systemic-warning-framework.md")
    assert "| v0.8.0-release | 旧当前行（本框架与阈值无变更） |" in text, "旧行未摘（当前）"
    assert "| v0.8.1-release（当前） | 测试说明（本框架与阈值无变更） |" in text
    # 顺序：旧当前行 < 新当前行 < 未来行
    assert text.index("旧当前行") < text.index("v0.8.1-release（当前）") < text.index("v0.10.3（规划）")
    assert text.count("（当前）") == 1, "（当前）标记不唯一"


def test_systemic_history_framework_changed(tmp_path):
    pm = _load_promote()
    _fake_tree(tmp_path)
    pm.apply_rules(tmp_path, OLD, NEW, apply=True, note="测试说明", tests=999, framework_changed=True)
    text = _read(tmp_path / "dev" / "engine" / "systemic-warning-framework.md")
    assert "| v0.8.1-release（当前） | 测试说明 |" in text


def test_same_version_rerun_does_not_duplicate_history_rows(tmp_path):
    """同版本二次晋升（old == new，重做 apply）不得重复插入历史行，且追加器给出跳过提示。"""
    pm = _load_promote()
    _fake_tree(tmp_path)
    pm.apply_rules(tmp_path, OLD, NEW, apply=True, note="测试说明", tests=999)
    hints = []
    pm.apply_rules(tmp_path, NEW, NEW, apply=True, note="二次说明", tests=999, hints=hints)
    dev = _read(tmp_path / "dev" / "README.md")
    assert dev.count("| **v0.8.1-release** |") == 1, "dev/README 版本历史重复行"
    overview = _read(tmp_path / "dev" / "engine" / "engine-overview.md")
    assert overview.count("| **0.8.1-release** |") == 1, "overview §六 重复行"
    systemic = _read(tmp_path / "dev" / "engine" / "systemic-warning-framework.md")
    v81_lines = [l for l in systemic.splitlines() if "v0.8.1-release" in l]
    assert len(v81_lines) == 2, f"§11.3 应只有 文件头+唯一当前行: {v81_lines}"
    assert systemic.count("（当前）") == 1, "（当前）标记不唯一"
    assert hints, "二次晋升应给出防重复提示"


def test_roadmap_flip_bilingual(tmp_path):
    pm = _load_promote()
    _fake_tree(tmp_path)
    hints = []
    pm.apply_rules(tmp_path, OLD, NEW, apply=True, note="测试说明", tests=999, hints=hints)
    readme = _read(tmp_path / "README.md")
    assert "- ~~**v0.8.1**~~（已发布）：待发布功能。" in readme
    assert "- ~~**v0.8.1**~~ (released): upcoming feature." in readme
    assert "（规划中）" not in readme and "(planned)" not in readme
    assert hints == [], "有匹配行时不应提示"


def test_roadmap_flip_no_match_hints(tmp_path):
    pm = _load_promote()
    _fake_tree(tmp_path)
    hints = []
    pm.apply_rules(tmp_path, OLD, "v0.9.9-release", apply=False, hints=hints)
    assert hints and "v0.9.9" in hints[0], "无匹配行应给出提示"
