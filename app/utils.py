import bleach
import markdown

ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'blockquote',
    'code', 'pre', 'h1', 'h2', 'h3', 'h4', 'a'
]
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
}


def sanitize_markdown_text(text):
    return bleach.clean(text or '', tags=[], strip=True).strip()


def markdown_to_html(text):
    html = markdown.markdown(text or '', extensions=['extra'])
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
