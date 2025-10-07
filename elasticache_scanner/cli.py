#!/usr/bin/env python3
"""ElastiCache Inventory - Modern CLI interface."""

import argparse
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd

from elasticache_scanner.aws_utils import get_available_profiles, is_invalid_client_token
from elasticache_scanner.config import ScanConfig, load_scan_state, save_scan_state
from elasticache_scanner.reports import generate_html_report
from elasticache_scanner.scanner import scan_profile

logger = logging.getLogger("elasticache_scanner")


def setup_logging(log_path: str) -> None:
    """Configure logging to file and console."""
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")

    # File handler for warnings and errors
    fh = logging.FileHandler(log_path)
    fh.setLevel(logging.WARNING)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler for info and above
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)


def scan_profiles_parallel(profiles: List[str], config: ScanConfig) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
    """Scan multiple profiles in parallel."""
    all_rows = []
    failures = {}

    # Load previous state for incremental scanning
    previous_state = {}
    if config.incremental:
        previous_state = load_scan_state(config.output_paths["state"])
        logger.info(f"Loaded previous scan state: {len(previous_state.get('profiles', {}))} profiles")

    # Create thread pool for parallel scanning
    max_workers = min(config.parallel_profiles, len(profiles))
    logger.info(f"Starting parallel scan with {max_workers} workers for {len(profiles)} profiles")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all profile scan tasks
        future_to_profile = {
            executor.submit(scan_profile, profile, config, previous_state): profile for profile in profiles
        }

        # Collect results as they complete
        for future in as_completed(future_to_profile):
            profile = future_to_profile[future]
            try:
                rows, err = future.result()
                if err:
                    failures[profile] = err
                all_rows.extend(rows)
                logger.info(f"✓ Completed scan for profile: {profile} ({len(rows)} resources)")
            except Exception as e:
                # If this is an invalid/expired token situation, convert to friendly message
                if is_invalid_client_token(e):
                    friendly = (
                        f"Profile {profile}: AWS session token appears invalid or expired. "
                        f"Please run 'aws sso login --profile {profile}' or refresh your credentials and try again."
                    )
                    failures[profile] = friendly
                    logger.warning(friendly)
                    logger.debug("Details: %s", e)
                else:
                    failures[profile] = str(e)
                    logger.warning(f"Failed scanning profile {profile}: {e}")
                    logger.exception(e)

    return all_rows, failures


def save_new_scan_state(config: ScanConfig, all_rows: List[Dict[str, Any]]) -> None:
    """Save scan state for incremental scanning."""
    if not config.incremental:
        return

    # Build new state structure
    new_state = {"last_scan": datetime.now(timezone.utc).isoformat(), "profiles": {}}

    # Group resources by profile and region
    for row in all_rows:
        profile = row.get("Profile")
        region = row.get("Region")
        resource_id = row.get("ResourceId")

        if not all([profile, region, resource_id]):
            continue

        if profile not in new_state["profiles"]:
            new_state["profiles"][profile] = {"regions": {}}

        if region not in new_state["profiles"][profile]["regions"]:
            new_state["profiles"][profile]["regions"][region] = {}

        # Calculate hash for change detection
        from elasticache_scanner.aws_utils import calculate_resource_hash

        resource_hash = calculate_resource_hash(row)

        new_state["profiles"][profile]["regions"][region][resource_id] = {
            "hash": resource_hash,
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }

    save_scan_state(config.output_paths["state"], new_state)
    logger.info(f"Saved scan state to {config.output_paths['state']}")


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Inventory ElastiCache resources across AWS profiles and regions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Scan specific regions with default tags
  python3 -m elasticache_scanner --regions us-east-1 sa-east-1

  # Scan with custom tags and include replication groups
  python3 -m elasticache_scanner --regions us-east-1 --tags Team Environment Owner --include-replication-groups

  # Incremental scan (only changed resources)
  python3 -m elasticache_scanner --regions us-east-1 --incremental

  # Dry run from existing CSV
  python3 -m elasticache_scanner --dry-run --sample-file elasticache_report.csv
        """,
    )

    # Required arguments
    parser.add_argument("--regions", nargs="+", required=True, help="AWS regions to scan (e.g., us-east-1 sa-east-1)")

    # Optional configuration
    parser.add_argument("--tags", nargs="+", default=["Team"], help="Tags to collect from resources (default: Team)")

    parser.add_argument(
        "--profile",
        action="append",
        help="AWS profile(s) to scan (can be used multiple times). "
        "If not specified, all available profiles are scanned.",
    )

    # Scanning options
    parser.add_argument(
        "--include-replication-groups",
        action="store_true",
        help="Include replication group resources (default: clusters only)",
    )

    parser.add_argument(
        "--node-info", action="store_true", help="Fetch detailed node information (increases API calls)"
    )

    parser.add_argument(
        "--incremental", action="store_true", help="Only scan resources that have changed since last run"
    )

    parser.add_argument(
        "--parallel-profiles", type=int, default=4, help="Number of profiles to scan in parallel (default: 4)"
    )

    # Output options
    parser.add_argument("--output-dir", default=".", help="Output directory (default: current directory)")
    parser.add_argument("--out-csv", help="Override CSV output filename")
    parser.add_argument("--out-xlsx", help="Override Excel output filename")
    parser.add_argument("--out-html", help="Override HTML output filename")

    # Dry run
    parser.add_argument("--dry-run", action="store_true", help="Generate reports from existing CSV without AWS calls")
    parser.add_argument("--sample-file", help="CSV file to use for dry run (default: elasticache_report.csv)")

    return parser


def build_config_from_args(args) -> ScanConfig:
    """Build ScanConfig from parsed arguments."""
    config = ScanConfig(
        regions=args.regions,
        tags=args.tags,
        include_replication_groups=args.include_replication_groups,
        node_info=args.node_info,
        output_dir=args.output_dir,
        parallel_profiles=args.parallel_profiles,
        incremental=args.incremental,
    )

    # Override output paths if specified
    if args.out_csv:
        config.output_csv = args.out_csv
    if args.out_xlsx:
        config.output_xlsx = args.out_xlsx
    if args.out_html:
        config.output_html = args.out_html

    return config


def determine_profiles(args) -> List[str]:
    """Determine which profiles to scan based on arguments."""
    if args.profile:
        profiles = []
        for p in args.profile:
            for part in p.split(","):
                part = part.strip()
                if part:
                    profiles.append(part)
        # dedupe while preserving order
        seen = set()
        profiles = [x for x in profiles if not (x in seen or seen.add(x))]
    else:
        profiles = get_available_profiles()

    return profiles


def handle_dry_run(args, config: ScanConfig) -> List[Dict[str, Any]]:
    """Handle dry run mode by loading sample data."""
    sample_path = args.sample_file or config.output_paths["csv"]
    if not os.path.exists(sample_path):
        logger.error(f"Dry-run requested but sample file not found: {sample_path}")
        sys.exit(1)

    df = pd.read_csv(sample_path)
    all_rows = df.to_dict(orient="records")
    logger.info(f"Loaded {len(all_rows)} rows from {sample_path} for dry-run")
    return all_rows


def write_outputs(df: pd.DataFrame, profiles: List[str], config: ScanConfig) -> None:
    """Write CSV, Excel and HTML outputs."""
    # Write CSV and Excel
    df.to_csv(config.output_paths["csv"], index=False)
    df.to_excel(config.output_paths["xlsx"], index=False)
    logger.info(f"Wrote CSV to {config.output_paths['csv']}")
    logger.info(f"Wrote Excel to {config.output_paths['xlsx']}")

    # Generate HTML report
    try:
        generate_html_report(df, profiles, config.output_paths["html"], config)
    except Exception as e:
        logger.warning(f"Failed to generate HTML report: {e}")


def handle_failures(failures: Dict[str, str], config: ScanConfig) -> None:
    """Handle and log scan failures."""
    if failures:
        logger.warning("Some profiles failed during scanning. Summary:")
        for p, msg in failures.items():
            logger.warning(f"  {p}: {msg}")
        # Also write a small JSON with failures
        try:
            with open(config.output_paths["failures"], "w", encoding="utf-8") as fh:
                json.dump(failures, fh, indent=2)
            logger.info(f"Wrote failures summary to {config.output_paths['failures']}")
        except Exception:
            logger.exception("Failed to write failures JSON")


def main() -> None:
    """Main CLI entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Build configuration
    config = build_config_from_args(args)

    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Setup logging
    setup_logging(config.output_paths["log"])

    logger.info("ElastiCache Inventory starting...")
    logger.info(f"Regions: {config.regions}")
    logger.info(f"Tags: {config.tags}")
    logger.info(f"Include replication groups: {config.include_replication_groups}")
    logger.info(f"Node info: {config.node_info}")
    logger.info(f"Incremental: {config.incremental}")
    logger.info(f"Parallel profiles: {config.parallel_profiles}")

    # Determine profiles to scan
    profiles = determine_profiles(args)
    logger.info(f"Found profiles: {profiles}")

    # Get data - either from dry run or actual scan
    if args.dry_run:
        all_rows = handle_dry_run(args, config)
        failures = {}
    else:
        all_rows, failures = scan_profiles_parallel(profiles, config)

    if not all_rows:
        logger.info("No resources found across profiles/regions.")
        return

    # Create DataFrame and reorder columns
    df = pd.DataFrame(all_rows)

    # Build column order dynamically based on configured tags
    base_cols = [
        "Profile",
        "AccountId",
        "Region",
        "ResourceType",
        "ResourceId",
        "ARN",
        "Engine",
        "EngineVersion",
        "CreationTime",
        "NodeTypes",
        "NumNodes",
        "AtRestEncryptionEnabled",
        "TransitEncryptionEnabled",
    ]

    # Add configured tags
    all_cols = base_cols + config.tags
    df = df[[c for c in all_cols if c in df.columns]]

    # Write outputs
    write_outputs(df, profiles, config)

    # Save scan state for incremental scanning
    if not args.dry_run:
        save_new_scan_state(config, all_rows)

    # Handle failures
    handle_failures(failures, config)

    logger.info("Scan complete. See warnings/errors in the log file if present.")


if __name__ == "__main__":
    main()
