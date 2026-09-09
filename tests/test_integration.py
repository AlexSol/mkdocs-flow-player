from pathlib import Path

from mkdocs.commands.build import build
from mkdocs.config import load_config


def test_example_builds(tmp_path: Path):
    root = Path(__file__).parents[1]
    config = load_config(config_file=str(root / "example/mkdocs.yml"), site_dir=str(tmp_path / "site"))
    build(config)
    output = (tmp_path / "site/index.html").read_text(encoding="utf-8")
    assert output.count('class="flow-player"') == 2
    assert (tmp_path / "site/assets/javascripts/flow-player.js").exists()
    assert (tmp_path / "site/assets/stylesheets/flow-player.css").exists()

