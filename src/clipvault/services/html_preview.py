"""Static Qt rich-text HTML preview. No browser engine, scripts or resource reads."""

import html
import re
from html.parser import HTMLParser


class StaticHTML(HTMLParser):
    ALLOWED = {
        "html",
        "head",
        "body",
        "title",
        "style",
        "p",
        "div",
        "span",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "b",
        "strong",
        "i",
        "em",
        "u",
        "s",
        "br",
        "hr",
        "pre",
        "code",
        "blockquote",
        "ul",
        "ol",
        "li",
        "table",
        "thead",
        "tbody",
        "tr",
        "td",
        "th",
        "dl",
        "dt",
        "dd",
        "small",
        "sub",
        "sup",
        "center",
    }
    BLOCKED = {"script", "iframe", "object", "embed", "template", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []
        self.blocked = []
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCKED or self.blocked:
            self.blocked.append(tag)
            return
        if tag == "img":
            alt = dict(attrs).get("alt", "")
            if alt:
                self.output.append("<span>" + html.escape(alt) + "</span>")
            return
        if tag == "a":
            tag = "span"
        if tag not in self.ALLOWED:
            return
        self.in_style = tag == "style"
        safe = []
        for key, value in attrs:
            if (
                key
                in {
                    "style",
                    "width",
                    "height",
                    "colspan",
                    "rowspan",
                    "align",
                    "color",
                    "size",
                    "face",
                }
                and value is not None
            ):
                if key == "style":
                    value = re.sub(
                        r"(?is)url\([^)]*\)|@import[^;]*;|expression\([^)]*\)", "", value
                    )
                safe.append(f'{key}="{html.escape(value, quote=True)}"')
        self.output.append("<" + tag + (" " + " ".join(safe) if safe else "") + ">")

    def handle_endtag(self, tag):
        if self.blocked:
            if tag in self.blocked:
                self.blocked = self.blocked[: self.blocked.index(tag)]
            return
        if tag == "a":
            tag = "span"
        if tag in self.ALLOWED:
            self.output.append("</" + tag + ">")
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if not self.blocked:
            if self.in_style:
                data = re.sub(r"(?is)url\([^)]*\)|@import[^;]*;|expression\([^)]*\)", "", data)
                self.output.append(data)
            else:
                self.output.append(html.escape(data))


def static_html(text: str) -> str:
    parser = StaticHTML()
    parser.feed(text)
    parser.close()
    return "".join(parser.output)
