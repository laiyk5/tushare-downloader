from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Frames(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []

    def handle_starttag(self, tag, attrs):
        if tag == "iframe":
            self.sources.append(dict(attrs).get("src", ""))


site = Path("site").resolve()
page = site / "design/cli-demo/index.html"
parser = Frames()
parser.feed(page.read_text(encoding="utf-8"))
assert len(parser.sources) == 1, "Expected one demo iframe"
url = urlsplit(parser.sources[0])
assert not url.scheme and not url.netloc and not url.path.startswith("/")
target = (page.parent / unquote(url.path)).resolve()
assert target == site / "design/assets/cli-modes-demo.html", target
assert target.is_file()
content = target.read_text(encoding="utf-8")
assert "<iframe" not in content and "<script src=" not in content
assert 'id="cm-format"' in content and 'id="cm-level"' in content
print("Built iframe resolves to the standalone demo; no nested frame or external scripts.")
