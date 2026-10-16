"""Package the public exhibit for static hosting, without model API calls.

Run from any directory with Python 3.9 or later. Only the explicit public file
list is copied into dist/ and outputs/deployment/site.zip.
"""

import json
import re
import shutil
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site"
DESTINATION = ROOT / "dist"
ARCHIVE = ROOT / "outputs/deployment/site.zip"
DATA_FILES = (
    "study.json",
    "demographics_forced.json",
    "demographics.json",
    "explanation_analysis.json",
    "demographics_social.json",
    "demographics_moral.json",
    "demographics_edges.json",
    "challenges.json",
)
PUBLIC_FILES = (
    "index.html",
    "app.js",
    "styles.css",
    "assets/trolley.svg",
    *(f"data/{filename}" for filename in DATA_FILES),
)


class LocalReferences(HTMLParser):
    """Find local assets and anchors that must survive subdirectory hosting."""

    def __init__(self):
        super().__init__()
        self.references = []
        self.ids = set()

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if "id" in attributes:
            self.ids.add(attributes["id"])
        for key in ("src", "href"):
            value = attributes.get(key)
            if value and not urlsplit(value).scheme and not value.startswith("//"):
                self.references.append(value)


def validate_source():
    """Reject missing assets, invalid data, and paths tied to the local server."""
    for relative in PUBLIC_FILES:
        path = SOURCE / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Missing public file or unsupported symlink: {relative}")
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
    app = (SOURCE / "app.js").read_text(encoding="utf-8")
    requested = set(re.findall(r"readData\('([^']+)'\)", app))
    if requested != set(DATA_FILES):
        raise ValueError("The deployment data list differs from the site's requested datasets.")
    page = LocalReferences()
    page.feed((SOURCE / "index.html").read_text(encoding="utf-8"))
    for reference in page.references:
        path = urlsplit(reference)
        if path.path.startswith("/") or ".." in Path(path.path).parts:
            raise ValueError(f"Public links must work under a repository subpath: {reference}")
        if path.path and path.path not in PUBLIC_FILES:
            raise ValueError(f"Local reference is not in the public package: {reference}")
        if not path.path and path.fragment and path.fragment not in page.ids:
            raise ValueError(f"Missing page section: {reference}")
    for filename in ("index.html", "app.js", "styles.css"):
        content = (SOURCE / filename).read_text(encoding="utf-8")
        if re.search(r"(?:localhost|127\.0\.0\.1)(?::\d+)?", content):
            raise ValueError(f"Local-server address in public source: {filename}")


def build_site():
    """Create an isolated hosting directory and a zip with index.html at its root."""
    validate_source()
    if DESTINATION.is_symlink():
        raise ValueError("The generated dist directory must not be a symlink.")
    with tempfile.TemporaryDirectory(prefix=".site-build-", dir=ROOT) as directory:
        staging = Path(directory)
        for relative in PUBLIC_FILES:
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / relative, target)
        (staging / ".nojekyll").write_text("", encoding="utf-8")
        if DESTINATION.exists():
            shutil.rmtree(DESTINATION)
        shutil.copytree(staging, DESTINATION)
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(ARCHIVE, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(DESTINATION.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(DESTINATION).as_posix())
    print(f"Built {len(PUBLIC_FILES)} public files plus .nojekyll in dist/.")
    print("Upload bundle: outputs/deployment/site.zip")
    print("Preview: python3 -m http.server 8767 --bind 127.0.0.1 --directory dist")
    return DESTINATION


if __name__ == "__main__":
    build_site()
