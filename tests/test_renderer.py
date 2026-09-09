from mkdocs_flow_player.renderer import render_player


def test_renderer_embeds_json_and_escapes_html():
    html = render_player("flowchart LR\nA[A]", {"id": "demo", "title": "A < B", "steps": [{"node": "A"}]})
    assert 'data-flow-id="demo"' in html
    assert "A &lt; B" in html
    assert '"steps": [{"node": "A"}]' in html

