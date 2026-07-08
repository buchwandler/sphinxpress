from pathlib import Path


def test_docs_conf_mentions_sphinxpress_not_taskledger():
    content = Path("docs/conf.py").read_text(encoding="utf-8")
    assert 'project = "sphinxpress"' in content
    assert "taskledger" not in content.lower()
