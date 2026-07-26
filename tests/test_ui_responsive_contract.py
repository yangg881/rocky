from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mobile_radar_filters_have_a_collapsed_sticky_entry_point() -> None:
    """Mobile users should not have to scroll past the full filter form before seeing jobs."""
    markup = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "app" / "static" / "styles.css").read_text(encoding="utf-8")

    assert 'id="radar-filter-toggle"' in markup
    assert 'aria-controls="radar-filter-form"' in markup
    assert "syncRadarFilterSummary" in script
    assert ".radar-mobile-filterbar" in styles
    assert ".radar-filters.is-open" in styles


def test_mobile_login_shell_prevents_horizontal_overflow_and_empty_scanner_space() -> None:
    """The sign-in screen must stay inside the viewport without a decorative blank tail."""
    styles = (ROOT / "src" / "auth.css").read_text(encoding="utf-8")

    assert "#auth-react-root {" in styles
    assert "overflow-x: clip" in styles
    assert ".ai-hero-system { display: none; }" in styles


def test_mobile_login_keeps_the_sign_in_flow_compact() -> None:
    """Decorative desktop-only content must not create a blank mobile scroll area."""
    styles = (ROOT / "src" / "auth.css").read_text(encoding="utf-8")

    assert 'grid-template-areas: "copy" "login";' in styles
    assert ".ai-hero-system { display: none; }" in styles
    assert ".site-footer.site-footer--embed {\n    position: static;" in styles


def test_web_download_fallback_uses_a_full_android_installer() -> None:
    """The unauthenticated web shell must not fall back to an ambiguous update path."""
    markup = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    card = (ROOT / "src" / "components" / "GlassLoginCard.jsx").read_text(encoding="utf-8")

    assert "download/android-full.apk" in markup
    assert 'link.href = "download/android-full.apk"' in script
    assert 'release?.download_url || "download/android-full.apk"' in card


def test_desktop_registration_card_uses_compact_controls_at_laptop_height() -> None:
    """A full registration form should fit a normal laptop viewport without feeling oversized."""
    styles = (ROOT / "src" / "auth.css").read_text(encoding="utf-8")

    assert ".ai-glass-login-inner { padding: 18px 20px 17px;" in styles
    assert ".ai-input-wrap { min-height: 43px;" in styles
    assert ".ai-submit { min-height: 46px;" in styles
