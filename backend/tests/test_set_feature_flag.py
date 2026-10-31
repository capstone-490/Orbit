# Below 50% AI-generated
from scripts import set_feature_flag


def test_main_enables_feature_flag(monkeypatch, capsys):
    calls = []

    def fake_set_flag(*args):
        calls.append(args)

    monkeypatch.setattr(set_feature_flag, "set_flag", fake_set_flag)

    set_feature_flag.main(
        [
            "demo-ab",
            "true",
            "100",
            "--changed_by",
            "test_user",
            "--description",
            "Test flag",
        ]
    )

    assert calls == [("demo-ab", True, 100, "test_user", "Test flag")]

    output = capsys.readouterr().out
    assert "demo-ab" in output
    assert "enabled = True" in output
    assert "rollout_percent = 100" in output


def test_main_disables_feature_flag(monkeypatch, capsys):
    calls = []

    def fake_set_flag(*args):
        calls.append(args)

    monkeypatch.setattr(set_feature_flag, "set_flag", fake_set_flag)

    set_feature_flag.main(
        [
            "demo-ab",
            "false",
            "0",
            "--changed_by",
            "test_user",
            "--description",
            "Test flag",
        ]
    )

    assert calls == [("demo-ab", False, 0, "test_user", "Test flag")]

    output = capsys.readouterr().out
    assert "demo-ab" in output
    assert "enabled = False" in output
    assert "rollout_percent = 0" in output
