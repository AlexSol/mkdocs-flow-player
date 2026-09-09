from __future__ import annotations

import logging
import html
from importlib.resources import files
from pathlib import Path
import posixpath
import shutil
from urllib.parse import urlsplit

from mkdocs.config import config_options
from mkdocs.exceptions import PluginError
from mkdocs.plugins import BasePlugin

from .parser import FlowError, load_topology, load_yaml, parse_directive, replace_directives
from .renderer import render_player
from .validator import validate_metadata, validate_scenario


log = logging.getLogger("mkdocs.plugins.flow-player")


class FlowPlayerPlugin(BasePlugin):
    config_scheme = (
        ("validation", config_options.Choice(("strict", "warning"), default="strict")),
        (
            "mermaid_url",
            config_options.Type(
                str,
                default="https://cdn.jsdelivr.net/npm/mermaid@11.17.2/dist/mermaid.min.js",
            ),
        ),
    )

    def on_config(self, config):
        # Reset per build; the plugin instance is reused across `mkdocs serve` rebuilds.
        self._flow_sources = {}
        # An empty mermaid_url skips injection so docs can vendor their own copy
        # (drop it in docs/ and add it via extra_javascript, or point mermaid_url
        # at a docs-relative path for an offline build).
        if self.config["mermaid_url"]:
            config.extra_javascript.append(self.config["mermaid_url"])
        config.extra_javascript.append("assets/javascripts/flow-player.js")
        config.extra_css.append("assets/stylesheets/flow-player.css")
        return config

    def on_page_markdown(self, markdown, page, config, files):
        docs_dir = Path(config.docs_dir)

        def replace(body):
            try:
                directive = parse_directive(body)
                diagram_path = self._safe_path(docs_dir, directive.diagram)
                topology = load_topology(diagram_path)
                metadata = {}
                if directive.metadata:
                    metadata_path = self._safe_path(docs_dir, directive.metadata)
                    metadata = load_yaml(metadata_path)
                    validate_metadata(metadata, topology)
                    self._resolve_metadata_docs(metadata, docs_dir, page.file.src_path)
                scenarios = []
                for scenario_ref in directive.scenarios:
                    scenario_path = self._safe_path(docs_dir, scenario_ref)
                    scenario = load_yaml(scenario_path)
                    validate_scenario(scenario, topology)
                    self._claim_flow_id(scenario["id"], page.file.src_path)
                    scenarios.append(scenario)
                return render_player(topology.source, scenarios, directive.title, metadata)
            except FlowError as exc:
                message = f"{page.file.src_path}: {exc}"
                if self.config["validation"] == "strict":
                    raise PluginError(f"flow-player: {message}") from exc
                log.warning(message)
                return f'<div class="flow-player--invalid" role="alert">{html.escape(message)}</div>'

        return replace_directives(markdown, replace)

    def on_post_build(self, config):
        assets = files("mkdocs_flow_player").joinpath("assets")
        targets = {
            "flow-player.js": Path(config.site_dir) / "assets/javascripts/flow-player.js",
            "flow-player.css": Path(config.site_dir) / "assets/stylesheets/flow-player.css",
        }
        for source_name, target in targets.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            with assets.joinpath(source_name).open("rb") as source:
                with target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)

    def _claim_flow_id(self, flow_id: str, src_path: str) -> None:
        # Lazily created so direct unit calls that skip on_config still work.
        sources = self.__dict__.setdefault("_flow_sources", {})
        previous = sources.get(flow_id)
        if previous is not None:
            where = "the same page" if previous == src_path else previous
            raise FlowError(f"duplicate flow id '{flow_id}'; already defined in {where}")
        sources[flow_id] = src_path

    @staticmethod
    def _safe_path(docs_dir: Path, relative: str) -> Path:
        candidate = (docs_dir / relative).resolve()
        root = docs_dir.resolve()
        if candidate != root and root not in candidate.parents:
            raise FlowError(f"Path escapes docs_dir: {relative}")
        return candidate

    @staticmethod
    def _resolve_metadata_docs(metadata: dict, docs_dir: Path, page_src_path: str) -> None:
        for node in metadata.get("nodes", {}).values():
            doc = node.get("doc")
            if not doc:
                continue
            parts = urlsplit(doc)
            if parts.scheme:
                if parts.scheme not in {"http", "https"} or parts.netloc == "":
                    raise FlowError(f"Unsupported metadata doc URL: {doc}")
                node["doc_href"] = doc
                node["doc_external"] = True
                continue
            if doc.startswith("#") or doc.startswith("/"):
                node["doc_href"] = doc
                node["doc_external"] = False
                continue
            target = FlowPlayerPlugin._safe_path(docs_dir, parts.path)
            if not target.exists():
                raise FlowError(f"Metadata doc target does not exist: {doc}")
            target_rel = target.relative_to(docs_dir.resolve()).as_posix()
            if target.suffix.lower() == ".md":
                target_rel = target_rel[:-3] + ".html"
            page_dir = posixpath.dirname(page_src_path)
            href = posixpath.relpath(target_rel, page_dir) if page_dir else target_rel
            if parts.query:
                href += f"?{parts.query}"
            if parts.fragment:
                href += f"#{parts.fragment}"
            node["doc_href"] = href
            node["doc_external"] = False
