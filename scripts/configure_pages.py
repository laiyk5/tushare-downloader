"""Set actual GitHub Pages URLs in the ephemeral CI checkout."""

import json
import os
from pathlib import Path

repository = os.environ["GITHUB_REPOSITORY"]
owner, name = repository.split("/")
base = f"https://{owner}.github.io/"
url = base if name.lower() == f"{owner}.github.io".lower() else f"{base}{name}/"
path = Path("zensical.toml")
text = path.read_text()
text = text.replace(
    "[project]\n",
    "[project]\n"
    + f"site_url = {json.dumps(url)}\n"
    + f"repo_url = {json.dumps('https://github.com/' + repository)}\n",
    1,
)
path.write_text(text)
