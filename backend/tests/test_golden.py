"""Golden snapshot test: synthetic daily run has no banned phrases and no duplicate URLs."""
from unmet.newsletter_style import BANNED_PHRASES, get_intro
from unmet.run.render_sample import run_render_sample


def test_golden_no_banned_phrases():
    """Rendered sample must not contain any BANNED_PHRASES."""
    md = run_render_sample()
    lower = md.lower()
    for phrase in BANNED_PHRASES:
        assert phrase.lower() not in lower, f"Banned phrase found: {phrase!r}"


def test_golden_no_duplicate_urls():
    """Rendered output must not repeat the same URL in multiple sections."""
    md = run_render_sample()
    lines = md.split("\n")
    urls = []
    for line in lines:
        if line.strip().startswith("http") or "http" in line:
            # Simple extraction: any token that looks like URL
            for word in line.split():
                if word.startswith("http"):
                    urls.append(word.rstrip(".,)"))
    seen = set()
    for u in urls:
        assert u not in seen, f"Duplicate URL in output: {u!r}"
        seen.add(u)


def test_golden_intro_evidence_mention():
    """Intro must mention evidence-based / no hallucination."""
    intro = get_intro()
    assert "evidence" in intro.lower() or "claim" in intro.lower()
