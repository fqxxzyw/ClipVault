"""Qt's local Markdown parser with all external resources denied."""

from PySide6.QtGui import QTextDocument

MARKDOWN_FEATURES = (
    QTextDocument.MarkdownFeature.MarkdownDialectGitHub
    | QTextDocument.MarkdownFeature.MarkdownNoHTML
)


class LocalDocument(QTextDocument):
    def loadResource(self, resource_type, name):
        # Deny HTTP, file, relative and data resources, including tracking images.
        return None


def markdown_plain_text(text: str) -> str:
    document = LocalDocument()
    document.setMarkdown(text, MARKDOWN_FEATURES)
    return document.toPlainText().replace("\ufffc", "")
