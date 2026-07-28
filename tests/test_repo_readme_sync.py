"""Drift-detector: README factual claims vs repo truth.

Fails when README commit count, module count, module names, LICENSE
status, or stale-OWID claim diverge from the real repo state.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

README = Path(__file__).resolve().parent.parent / "README.md"
REPO = README.parent


def _git(*args: str) -> str:
    return subprocess.run(
        ("git",) + args,
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO,
    ).stdout.strip()


def _pipeline_modules() -> list[str]:
    out = _git("ls-files", "ellectric/pipeline/*.py")
    return sorted(
        p for p in out.splitlines() if not p.endswith("__init__.py")
    )


def _readme_text() -> str:
    return README.read_text(encoding="utf-8")


class TestReadmeCommitCount:
    def test_readme_commit_count_matches_repo(self):
        txt = _readme_text()
        readme_match = re.search(r"\*\*(\d+)\+?\s*次提交\*\*", txt)
        assert readme_match, "Could not find '次提交' line in README"
        readme_count = int(readme_match.group(1))
        actual = int(_git("rev-list", "--count", "HEAD"))
        assert actual >= readme_count, (
            f"README claims {readme_count}+ commits, repo has {actual}"
        )
        # Allow 10% slack so small commits don't break the test
        assert actual - readme_count < max(10, readme_count // 10), (
            f"README commit count ({readme_count}) too far behind repo ({actual})"
        )


class TestReadmeModuleCount:
    def _readme_module_claims(self, txt: str) -> list[int]:
        """Return all integer module counts found in README."""
        # Stats section: "16 个模块" or "16 modules"
        counts = []
        for m in re.finditer(r"(\d+)\s*[个]*(?:模块|modules)", txt):
            counts.append(int(m.group(1)))
        # Structure tree header
        for m in re.finditer(r"\((\d+)\s*模块", txt):
            counts.append(int(m.group(1)))
        return counts

    def test_module_count_agrees_with_tree(self):
        modules = _pipeline_modules()
        actual = len(modules)
        txt = _readme_text()
        counts = self._readme_module_claims(txt)
        assert actual in counts, (
            f"Pipeline has {actual} modules, "
            f"but README claims {counts} (from {len(counts)} mentions)"
        )

    def test_stats_and_structure_agree(self):
        """Stats section and structure section must not contradict each other."""
        txt = _readme_text()
        counts = self._readme_module_claims(txt)
        if len(counts) >= 2:
            assert len(set(counts)) == 1, (
                f"README has inconsistent module counts: {counts}"
            )


class TestReadmeModuleNames:
    def test_all_tracked_modules_in_structure_tree(self):
        txt = _readme_text()
        modules = _pipeline_modules()
        # Find the structure tree section: pipeline/ ... ember_loader.py
        tree_start = txt.find("├── pipeline/")
        assert tree_start != -1, "Could not find pipeline structure tree"
        tree_section = txt[tree_start:]
        for path in modules:
            stem = Path(path).stem
            assert stem in tree_section, (
                f"Pipeline module '{stem}' not found in README structure tree"
            )


class TestReadmeDataNote:
    def test_no_stale_owid_claim(self):
        txt = _readme_text()
        note_section = txt[txt.find("## ⚠️ 注意事项"):]
        # The stale phrase combo must not appear
        assert "OWID" not in note_section or (
            "年度级" not in note_section
            and "折算为日均值" not in note_section
        ), (
            "README data note still contains stale OWID claim: "
            "'OWID 公开数据为年度级，需折算为日均值'"
        )
        # Positively assert Shandong 15min is mentioned in notes
        assert "山东" in note_section and "15min" in note_section, (
            "README data note should mention '山东' and '15min'"
        )
        assert "出清数据" in note_section, (
            "README data note should mention '出清数据'"
        )


class TestLicense:
    def test_license_tracked(self):
        result = _git("ls-files", "LICENSE")
        assert result, "LICENSE is not tracked in git"