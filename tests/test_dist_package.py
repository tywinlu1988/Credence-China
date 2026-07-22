"""Dist 可安装包完整性测试（v0.8.0-release，T12.1–T12.7）。

`scripts/build_dist.py` 把 dev/ 源组装为 `dist/credence/` 可安装 agent 包。这些测试把
构建产物构建到 ``tmp_path``（不碰工作树），逐条断言布局契约：无绝对路径、无 `dev/` 残留、
链接可解析、技能为 spec 严格子集、引擎文档齐全、src 在 dist 布局可定位、剔除物不出现、
无父级逃逸、溯源指针已清且正文存活、生成文件齐全、构建可复现。构建器自带的 ``validate``
覆盖 (a)(b)(c)(d)(e) 与布局/剔除，本文件补充其外的 (f)–(l)。
"""

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

from src.path_sheet import (
    Depth,
    Mode,
    Object,
    engine_dir,
    load_registry_paths,
    templates_dir,
    validate_path_sheet,
)

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIST = ROOT / "scripts" / "build_dist.py"

SKILL_NAMES = [
    "credit-analysis-router",
    "fixed-income-credit-analysis",
    "credit-report-builder",
    "credit-qa-verifier",
]
GENERATED_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "INSTALL.md",
    "README.md",
    ".claude-plugin/plugin.json",
    "adapters/codex.md",
]
ABS_PATH_RE = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]")
DEV_TOKEN_RE = re.compile(r"(?<![\w/.-])dev[/\\]")


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_dist", BUILD_DIST)
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_dist"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def builder():
    return _load_builder()


def test_validate_flags_crlf_in_dist(builder, tmp_path):
    """P0: dist 产物混入 CRLF 时 validate 必须响亮报错（防 _write_text 回归）。"""
    out = tmp_path / "credence"
    builder.build(out_dir=out)
    target = out / "engine" / "engine-overview.md"
    target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n"))
    errors = builder.validate(out_dir=out)
    assert any("CRLF:" in e and "engine-overview.md" in e for e in errors)


@pytest.fixture(scope="module")
def dist(builder, tmp_path_factory):
    out = tmp_path_factory.mktemp("dist") / "credence"
    builder.build(out)
    return out


def _texts(base):
    for f in sorted(base.rglob("*")):
        if f.is_file() and f.suffix in (".md", ".py", ".html", ".css", ".yaml", ".json"):
            yield f, f.read_text(encoding="utf-8")


# T12.1 — 构建器自带校验全绿（覆盖 a 零绝对路径 / b 零 dev token / c 链接可解析 /
#          d 4 skill+严格 frontmatter / e 28 CORE_DOCS / 布局 / 剔除物缺席）
def test_t12_1_builder_validate_passes(builder, dist):
    assert builder.validate(dist) == []


# T12.2 — (f) src 在 dist 布局可定位：engine_dir/templates_dir 命中平铺目录，
#          且对 dist 根 validate_path_sheet 全 active 路径通过（模板真实落盘）。
def test_t12_2_src_resolves_in_dist(dist):
    assert engine_dir(dist) == dist / "engine"
    assert templates_dir(dist) == dist / "templates"

    reg = load_registry_paths(dist / "engine" / "work-path-registry.md")
    active = sorted(pid for pid, p in reg.items() if str(p.get("status")) == "active")
    assert active, "no active paths parsed from dist registry"
    for pid in active:
        role = str(reg[pid].get("role", "meta"))
        sheet = {
            "role": role,
            "object": Object.SINGLE_ISSUER.value,
            "depth": Depth.L1.value,
            "mode": Mode.A.value,
            "path_id": pid,
            "engine_reading_order": ["e"],
            "quality_gates": ["g"],
        }
        assert validate_path_sheet(sheet, reg, root=dist) == [], pid


# T12.3 — (h) 无父级逃逸：dist 内任何 .md 不含 `](../../`（engine/ 平铺后两级链接即逃逸包根）。
def test_t12_3_no_parent_escape(dist):
    for f, text in _texts(dist):
        assert "](../../" not in text, f"{f.relative_to(dist)} contains a ../../ escape link"


# T12.4 — (g)+(i) 剔除物缺席且无 audits//validation/ 引用。
def test_t12_4_excluded_and_pointer_tokens_absent(dist):
    for f in sorted(dist.rglob("*")):
        if f.is_dir():
            continue
        rel = f.relative_to(dist)
        assert "__pycache__" not in f.parts and f.suffix != ".pyc", rel
        assert f.name != "settings.local.json", rel
        assert "audits" not in f.parts, rel
    for f, text in _texts(dist / "engine"):
        assert "audits/" not in text, f"{f.name} still references audits/"
        assert "validation/" not in text, f"{f.name} still references validation/"


# T12.5 — (j) 溯源指针已清除，且邻接正文存活。
def test_t12_5_pointers_scrubbed_neighbors_intact(dist):
    eo = (dist / "engine" / "engine-overview.md").read_text(encoding="utf-8")
    # 审计表行已除，非审计导航行存活。
    assert "financial-analysis-audit" not in eo
    assert "rating-agency-benchmark-audit" not in eo
    assert "work-path-registry.md" in eo and "pipeline-contract.md" in eo
    # 深度链接已修为 ../src（不逃逸）。
    assert "../src/pipeline.py" in eo and "../../src/pipeline.py" not in eo

    es = (dist / "engine" / "external-support-framework.md").read_text(encoding="utf-8")
    # 行内括号片段已剥，句子保留。
    assert "在评级机构对标审计中，外部支持被列为G3/G4严重缺口" in es
    assert "rating-agency-benchmark-audit" not in es

    nc = (dist / "engine" / "non-credit-risk-overlay.md").read_text(encoding="utf-8")
    assert "risk-management-standards-audit" not in nc

    dt = (dist / "engine" / "dual-track-methodology.md").read_text(encoding="utf-8")
    assert "风险缓释建议" in dt  # 相邻正文存活


# T12.6 — (k) 生成的入口/安装文件齐全且含版本戳。
def test_t12_6_generated_files_present(dist):
    for rel in GENERATED_FILES:
        assert (dist / rel).exists(), f"missing generated file {rel}"
    agents = (dist / "AGENTS.md").read_text(encoding="utf-8")
    assert "引擎版本" in agents and ".claude/skills/" in agents
    for name in SKILL_NAMES:
        assert f"skills/{name}/SKILL.md" in agents, f"AGENTS.md does not index {name}"


# T12.7 — (l) 构建可复现：两次构建字节一致。
def test_t12_7_deterministic_rebuild(builder, tmp_path):
    a = tmp_path / "a" / "credence"
    b = tmp_path / "b" / "credence"
    builder.build(a)
    builder.build(b)
    files_a = {f.relative_to(a): f.read_bytes() for f in sorted(a.rglob("*")) if f.is_file()}
    files_b = {f.relative_to(b): f.read_bytes() for f in sorted(b.rglob("*")) if f.is_file()}
    assert files_a.keys() == files_b.keys()
    diff = [str(k) for k in files_a if files_a[k] != files_b[k]]
    assert not diff, f"non-deterministic outputs: {diff[:5]}"


# T12.8 — (m) dist 布局下编排器可导入：src.pipeline 顶层链式导入全部 5 引擎，
#          不依赖包外的 scripts/（回归锁：composite_scorer 曾 sys.path 注入 ../scripts
#          import consistency_check，导致发行包内 pipeline 整体 ModuleNotFoundError）。
def test_t12_8_pipeline_importable_in_dist(dist):
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]);"
        "import src.pipeline as p;"
        "assert len(p.EXECUTABLE_ENGINES) == 5;"
        "print('PIPELINE_OK')"
    )
    r = subprocess.run(
        [sys.executable, "-c", code, str(dist)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert r.returncode == 0 and "PIPELINE_OK" in r.stdout, r.stderr


# T12.9 — (n) 生成的 AGENTS.md 保真：含防漂移铁律与 5 引擎清单，路径计数/模板数与
#          注册表真值一致（回归锁：生成器模板曾自带 Type 1–15、2 引擎、8/6/2 过期声明，
#          根 AGENTS.md 修正从未触达发行包用户）。
def test_t12_9_generated_agents_md_fidelity(dist):
    agents = (dist / "AGENTS.md").read_text(encoding="utf-8")
    assert "防漂移铁律" in agents, "generated AGENTS.md missing 防漂移铁律"
    assert "Type 1–18" in agents and "Type 1–15" not in agents
    for pid in ("WP-M0-01", "WP-M4-01", "WP-M4-02", "WP-M4-03", "WP-X-05"):
        assert pid in agents, f"generated AGENTS.md missing wired engine {pid}"
    reg = load_registry_paths(dist / "engine" / "work-path-registry.md")
    counts = {"active": 0, "partial": 0, "planned": 0}
    for p in reg.values():
        s = str(p.get("status"))
        if s in counts:
            counts[s] += 1
    claim = (
        f"{counts['active']} 条 active / {counts['partial']} 条 partial / "
        f"{counts['planned']} 条 planned"
    )
    assert claim in agents, f"generated AGENTS.md path counts stale, expect {claim!r}"
