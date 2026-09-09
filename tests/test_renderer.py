from mkdocs_flow_player.renderer import render_player


def test_renderer_embeds_json_and_escapes_html():
    html = render_player(
        "flowchart LR\nA[A]",
        {"id": "demo", "title": "A < B", "steps": [{"node": "A"}]},
        metadata={"nodes": {"A": {"summary": "Node < A", "doc_href": "a.html"}}},
    )
    assert 'data-flow-id="demo"' in html
    assert "A &lt; B" in html
    assert '"steps": [{"node": "A"}]' in html
    assert 'flow-player__metadata' in html
    assert 'Node \\u003c A' in html


def test_controls_render_before_details_so_variable_text_does_not_shift_them():
    html = render_player("flowchart LR\nA[A]", {"id": "demo", "steps": [{"node": "A"}]})
    assert html.index('flow-player__controls') < html.index('flow-player__details')


def test_renderer_adds_scenario_select_for_multiple_scenarios():
    html = render_player(
        "flowchart LR\nA[A]",
        [
            {"id": "one", "title": "One", "steps": [{"node": "A"}]},
            {"id": "two", "title": "Two", "steps": [{"node": "A"}]},
        ],
        "Demo",
    )
    assert html.count('class="flow-player"') == 1
    assert 'class="flow-player__scenario-select"' in html
    assert '<option value="0">One</option>' in html
    assert '<option value="1">Two</option>' in html
    assert '"id": "one"' in html and '"id": "two"' in html
