"""Build and exercise the actual public package under a repository-style URL.

Needs requirements-dev.txt and an installed Playwright browser. Starts a temporary
local server, checks the package, and shuts the server down when finished.
"""

import argparse
import functools
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *arguments):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", help="Installed browser channel, such as chrome.")
    args = parser.parse_args()
    subprocess.run([sys.executable, "scripts/build_site.py"], cwd=ROOT, check=True)
    with ZipFile(ROOT / "outputs/deployment/site.zip") as archive:
        archived = set(archive.namelist())
        built = {path.relative_to(ROOT / "dist").as_posix() for path in (ROOT / "dist").rglob("*") if path.is_file()}
        assert archived == built
        assert "index.html" in archived
        assert not any(path.startswith(("src/", "datasets/", ".env", ".git/")) or path.endswith((".csv", ".pdf", ".py")) for path in archived)
        for relative in archived:
            assert archive.read(relative) == (ROOT / "dist" / relative).read_bytes()
    with tempfile.TemporaryDirectory(prefix="class-exhibit-") as directory:
        shutil.copytree(ROOT / "dist", Path(directory) / "ai-explanation-audit")
        handler = functools.partial(QuietHandler, directory=directory)
        with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_port}/ai-explanation-audit"
            try:
                with urlopen(f"{url}/") as response:
                    assert response.status == 200
                for private_path in (".env", "README.md", "src/api_client.py", "data/poster.pdf"):
                    try:
                        urlopen(f"{url}/{private_path}")
                    except HTTPError as error:
                        assert error.code == 404
                    else:
                        raise AssertionError(f"Unexpected file in public package: {private_path}")
                command = [sys.executable, "scripts/check_ui.py", "--url", url]
                if args.channel:
                    command.extend(["--channel", args.channel])
                subprocess.run(command, cwd=ROOT, check=True)
            finally:
                server.shutdown()
                thread.join()
    print("Deployment package passed: archive contents, isolated hosting and full UI under a repository subpath.")


if __name__ == "__main__":
    main()
