import html

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

PREVIEW_LIMIT = 20_000


def render_preview(text: str, content_type: str, theme: str, font_size: int) -> str:
    sample = text[:PREVIEW_LIMIT]
    dark = theme == "dark"
    foreground, background = ("#dce4f4", "#161c29") if dark else ("#293246", "#ffffff")
    if content_type in {"python", "javascript", "json", "shell", "sql"}:
        lexer = get_lexer_by_name("bash" if content_type == "shell" else content_type)
        formatter = HtmlFormatter(noclasses=True, style="native" if dark else "friendly")
        body = highlight(sample, lexer, formatter)
    else:
        body = "<pre>" + html.escape(sample) + "</pre>"
    if len(text) > PREVIEW_LIMIT:
        body += (
            f"<p>Preview: first {PREVIEW_LIMIT:,} characters. Use Details for the full text.</p>"
        )
    return (
        "<html><head><style>"
        f"body {{ color:{foreground}; background:{background}; }}"
        f"pre {{ white-space:pre-wrap; font-family:Consolas,monospace; font-size:{font_size}px; }}"
        f"p {{ color:{foreground}; font-size:10pt; }}"
        "</style></head><body>" + body + "</body></html>"
    )
