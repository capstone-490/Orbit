# Below 50% AI-generated

from unittest.mock import patch

import set_feature_flag


def test_main_enables_feature_flag(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "set_feature_flag.py",
            "demo-ab",
            "true",
            "100",
            "--changed_by",
            "test_user",
            "--description",
            "Test flag",
        ],
    )
    with patch("set_feature_flag.set_flag") as mock_set_flag:
        set_feature_flag.main()
    mock_set_flag.assert_called_once_with(
        "demo-ab", True, 100, "test_user", "Test flag"
    )
    output = capsys.readouterr().out
    assert "demo-ab" in output
    assert "enabled = True" in output
    assert "rollout_percent = 100" in output


def test_main_disables_feature_flag(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "set_feature_flag.py",
            "demo-ab",
            "false",
            "0",
            "--changed_by",
            "test_user",
            "--description",
            "Test flag",
        ],
    )
    with patch("set_feature_flag.set_flag") as mock_set_flag:
        set_feature_flag.main()
    mock_set_flag.assert_called_once_with("demo-ab", False, 0, "test_user", "Test flag")
    output = capsys.readouterr().out
    assert "demo-ab" in output
    assert "enabled = False" in output
    assert "rollout_percent = 0" in output
