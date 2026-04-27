from workflow.state.config import DEFAULT_CONFIG, load_config, save_config


def test_config_round_trip_merges_defaults(tmp_path):
    save_config(tmp_path, {
        "executor": {"model": "custom:13b"},
        "validation": {"test": "npm test"},
    })
    loaded = load_config(tmp_path)

    assert loaded["executor"]["model"] == "custom:13b"
    assert loaded["executor"]["timeout_seconds"] == DEFAULT_CONFIG["executor"]["timeout_seconds"]
    assert loaded["validation"]["test"] == "npm test"
    assert loaded["validation"]["lint"] is None
    assert loaded["max_attempts_per_step"] == DEFAULT_CONFIG["max_attempts_per_step"]


def test_config_user_can_null_out_a_default(tmp_path):
    save_config(tmp_path, {
        "validation": {"test": "pytest", "timeout_seconds": None},
    })
    loaded = load_config(tmp_path)

    assert loaded["validation"]["test"] == "pytest"
    assert loaded["validation"]["timeout_seconds"] is None


