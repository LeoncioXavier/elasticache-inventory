"""Tests for elasticache_scanner.config module."""

import os
import tempfile
from unittest.mock import patch

import pytest

from elasticache_scanner.config import ScanConfig, load_scan_state, save_scan_state


def test_scan_config_defaults():
    """Test ScanConfig default values."""
    config = ScanConfig(regions=["us-east-1"], tags=["Team"])

    assert config.regions == ["us-east-1"]
    assert config.tags == ["Team"]
    assert config.include_replication_groups is False
    assert config.node_info is False
    assert config.output_dir == "."
    assert config.parallel_profiles == 4
    assert config.incremental is False


def test_scan_config_validation_success():
    """Test that valid configuration passes validation."""
    config = ScanConfig(regions=["us-east-1"], tags=["Team"])
    # Should not raise an exception
    config.validate()


def test_scan_config_validation_empty_regions():
    """Test that empty regions list fails validation."""
    config = ScanConfig(regions=[], tags=["Team"])

    with pytest.raises(ValueError, match="At least one region must be specified"):
        config.validate()


def test_scan_config_validation_empty_tags():
    """Test that empty tags list gets set to default Team."""
    config = ScanConfig(regions=["us-east-1"], tags=[])

    # Should not raise an exception but set default
    config.validate()
    assert config.tags == ["Team"]


def test_scan_config_output_paths():
    """Test output paths generation."""
    config = ScanConfig(regions=["us-east-1"], tags=["Team"], output_dir="/tmp")

    paths = config.output_paths
    assert paths["csv"] == "/tmp/elasticache_report.csv"
    assert paths["xlsx"] == "/tmp/elasticache_report.xlsx"
    assert paths["html"] == "/tmp/elasticache_report.html"
    assert paths["log"] == "/tmp/scan_errors.log"
    assert paths["state"] == "/tmp/scan_state.json"
    assert paths["failures"] == "/tmp/scan_failures.json"


def test_load_scan_state_nonexistent_file():
    """Test loading state from non-existent file returns empty dict."""
    result = load_scan_state("nonexistent.json")
    assert result == {}


def test_load_scan_state_invalid_json():
    """Test loading state from invalid JSON file returns empty dict."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("invalid json content")
        f.flush()
        temp_path = f.name

    try:
        result = load_scan_state(temp_path)
        assert result == {}
    finally:
        os.unlink(temp_path)


def test_load_scan_state_valid_file():
    """Test loading state from valid JSON file."""
    test_data = {
        "last_scan": "2023-01-01T00:00:00Z",
        "profiles": {
            "test-profile": {
                "regions": {"us-east-1": {"resource1": {"hash": "abc123", "last_seen": "2023-01-01T00:00:00Z"}}}
            }
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        import json

        json.dump(test_data, f)
        f.flush()
        temp_path = f.name

    try:
        result = load_scan_state(temp_path)
        assert result == test_data
    finally:
        os.unlink(temp_path)


def test_save_scan_state():
    """Test saving state to JSON file."""
    test_data = {"last_scan": "2023-01-01T00:00:00Z", "profiles": {}}

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = f.name

    try:
        save_scan_state(temp_path, test_data)

        # Verify file was created and contains correct data
        import json

        with open(temp_path, "r") as f:
            saved_data = json.load(f)

        assert saved_data == test_data
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_save_scan_state_write_error():
    """Test save_scan_state handles write errors gracefully."""
    test_data = {"test": "data"}

    # Try to save to an invalid path (directory that doesn't exist)
    invalid_path = "/nonexistent/directory/file.json"

    # Should not raise an exception but log the error
    save_scan_state(invalid_path, test_data)
