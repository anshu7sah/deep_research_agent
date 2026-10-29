import markdown
from logging_config import get_logger

logger = get_logger("pdf_service")

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<style>
body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; max-width: 800px;
       margin: 0 auto; padding: 2rem; line-height: 1.7; color: #1a1a1a; }}
h1 {{ font-size: 1.8rem; border-bottom: 2px solid #209dd7; padding-bottom: 0.4rem;
      color: #209dd7; }}
h2 {{ font-size: 1.3rem; color: #753991; margin-top: 1.5rem; }}
h3 {{ font-size: 1.1rem; margin-top: 1.2rem; }}
a {{ color: #209dd7; }}
blockquote {{ border-left: 3px solid #753991; padding: 0.5rem 1rem; margin: 1rem 0;
              background: #f5f5f5; }}
code {{ background: #f0f0f0; padding: 0.1rem 0.3rem; font-size: 0.9em; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
th {{ background: #f5f5f5; color: #209dd7; font-weight: 700; }}
</style>
</head>
<body>{content}</body>
</html>"""


def generate_pdf(markdown_text: str) -> bytes:
    html_content = markdown.markdown(
        markdown_text,
        extensions=["tables", "fenced_code"],
    )
    full_html = HTML_TEMPLATE.format(content=html_content)

    try:
        from weasyprint import HTML
        return HTML(string=full_html).write_pdf()
    except ImportError:
        logger.warning("weasyprint_not_installed_returning_html")
        return full_html.encode("utf-8")
    except Exception as e:
        logger.error("pdf_generation_failed", error=str(e))
        return full_html.encode("utf-8")
