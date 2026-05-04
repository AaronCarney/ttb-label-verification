from pathlib import Path


def test_readme_preserves_hf_frontmatter():
    """T4's frontmatter must survive T9's body edit."""
    content = Path("README.md").read_text()
    assert content.startswith("---\n")
    for marker in ("sdk: docker", "app_port: 8000", "hardware: cpu-basic"):
        assert marker in content


def test_readme_has_reviewer_profiles():
    content = Path("README.md").read_text()
    assert "Profile A" in content and "Profile B" in content and "Profile C" in content
    assert "WSL2" in content


def test_readme_links_decisions_and_runbook():
    content = Path("README.md").read_text()
    for ref in ("docs/PRD.md", "docs/ARCHITECTURE.md", "docs/03-decisions.md", "DEMO-RUNBOOK.md"):
        assert ref in content, f"README missing link to {ref}"


def test_readme_has_live_demo():
    content = Path("README.md").read_text()
    # Recorded walkthrough is descoped; the live demo URL is the demo.
    assert "context31415-ttb-label.hf.space" in content
