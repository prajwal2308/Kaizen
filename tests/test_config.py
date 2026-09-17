from onepact.config import DEFAULTS, SUPPORTED_KEYS, load_config, set_config_value


def test_load_config_returns_defaults_when_no_file(tmp_path):
    assert load_config(data_dir=tmp_path) == DEFAULTS


def test_load_config_reads_priority_from_file(tmp_path):
    (tmp_path / "config.toml").write_text('priority = "high"\n')
    assert load_config(data_dir=tmp_path)["priority"] == "high"


def test_load_config_handles_single_quoted_values(tmp_path):
    (tmp_path / "config.toml").write_text("priority = 'high'\n")
    assert load_config(data_dir=tmp_path)["priority"] == "high"


def test_load_config_handles_unquoted_values(tmp_path):
    (tmp_path / "config.toml").write_text("priority = high\n")
    assert load_config(data_dir=tmp_path)["priority"] == "high"


def test_load_config_ignores_comments_and_blank_lines(tmp_path):
    (tmp_path / "config.toml").write_text(
        '# onepact config\n\npriority = "low"  # trailing comment\n'
    )
    assert load_config(data_dir=tmp_path)["priority"] == "low"


def test_load_config_falls_back_on_invalid_priority(tmp_path):
    (tmp_path / "config.toml").write_text('priority = "urgent"\n')
    assert load_config(data_dir=tmp_path)["priority"] == "med"


def test_load_config_ignores_unknown_keys(tmp_path):
    (tmp_path / "config.toml").write_text('mystery = "value"\npriority = "low"\n')
    config = load_config(data_dir=tmp_path)
    assert config["priority"] == "low"
    assert "mystery" in config


def test_supported_keys_includes_priority():
    assert "priority" in SUPPORTED_KEYS


def test_set_config_value_creates_file(tmp_path):
    set_config_value("priority", "high", data_dir=tmp_path)
    assert load_config(data_dir=tmp_path)["priority"] == "high"


def test_set_config_value_overwrites_existing(tmp_path):
    set_config_value("priority", "high", data_dir=tmp_path)
    set_config_value("priority", "low", data_dir=tmp_path)
    assert load_config(data_dir=tmp_path)["priority"] == "low"


def test_set_config_value_preserves_other_keys(tmp_path):
    (tmp_path / "config.toml").write_text('other_key = "kept"\npriority = "low"\n')
    set_config_value("priority", "high", data_dir=tmp_path)
    text = (tmp_path / "config.toml").read_text()
    assert 'other_key = "kept"' in text
    assert 'priority = "high"' in text


def test_set_config_value_writes_quoted_string(tmp_path):
    set_config_value("priority", "high", data_dir=tmp_path)
    text = (tmp_path / "config.toml").read_text()
    assert text == 'priority = "high"\n'
