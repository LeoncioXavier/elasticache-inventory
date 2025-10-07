"""Configuration management for ElastiCache Inventory."""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ScanConfig:
    """Configuration for ElastiCache scanning."""

    # Required parameters
    regions: List[str] = field(default_factory=list)

    # Optional parameters
    tags: List[str] = field(default_factory=lambda: ["Team"])
    include_replication_groups: bool = False
    node_info: bool = False

    # Output configuration
    output_dir: str = "."
    output_csv: str = "elasticache_report.csv"
    output_xlsx: str = "elasticache_report.xlsx"
    output_html: str = "elasticache_report.html"

    # Scanning configuration
    parallel_profiles: int = 4
    incremental: bool = False
    state_file: str = "scan_state.json"

    def validate(self) -> None:
        """Validate configuration."""
        if not self.regions:
            raise ValueError("At least one region must be specified")

        if not self.tags:
            self.tags = ["Team"]

    @property
    def output_paths(self) -> Dict[str, str]:
        """Get full output paths."""
        return {
            "csv": os.path.join(self.output_dir, self.output_csv),
            "xlsx": os.path.join(self.output_dir, self.output_xlsx),
            "html": os.path.join(self.output_dir, self.output_html),
            "log": os.path.join(self.output_dir, "scan_errors.log"),
            "failures": os.path.join(self.output_dir, "scan_failures.json"),
            "state": os.path.join(self.output_dir, self.state_file),
        }


def load_scan_state(state_file: str) -> Dict[str, Any]:
    """Load previous scan state for incremental scanning."""
    if not os.path.exists(state_file):
        return {}

    try:
        with open(state_file, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_scan_state(state_file: str, state: Dict[str, Any]) -> None:
    """Save scan state for incremental scanning."""
    try:
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2, default=str)
    except Exception:
        pass  # Don't fail the scan if we can't save state
