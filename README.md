# ElastiCache Inventory

**📄 [Versão em Português](README-pt.md)** | **📄 English Version**

A modular Python tool to inventory ElastiCache Redis resources across AWS profiles and regions with parallel scanning, incremental updates, and comprehensive reporting.

Table of contents
- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage examples](#usage)
- [CLI options](#cli-options)
- [Configuration](#configuration)  
- [Outputs and reports](#outputs-and-reports)
- [HTML report details](#html-report-details)
- [Credential handling](#credential-handling)
- [Testing & development](#testing--development)
- [Changelog](#changelog)
- [Contributing](#contributing)

## Overview

This tool scans AWS accounts (profiles) and collects metadata about ElastiCache resources (replication groups and cache clusters) across configurable regions. Designed for inventory management, security reviews, and compliance reporting.

**Key improvements in v1.0:**
- **Configurable regions** (no longer hard-coded)
- **Configurable tags** (no longer limited to CC, Email, Team)
- **Parallel profile scanning** for better performance
- **Incremental scanning** to detect changes since last run
- **Modular codebase** with proper separation of concerns
- **Comprehensive linting and formatting** setup

## Features

- **Multi-profile scanning** — discovers profiles in `~/.aws/config` / `~/.aws/credentials` or scan specific profiles
- **Configurable regions** — specify any AWS regions to scan (required parameter)
- **Configurable tags** — specify which tags to collect (defaults to Team)
- **Parallel scanning** — scan multiple profiles concurrently for better performance
- **Incremental mode** — only scan resources that changed since last run
- **Export formats** — CSV, Excel and interactive HTML report with filters and charts
- **Friendly credential handling** — expired/invalid AWS sessions show actionable guidance

## Installation

Requirements:
- Python 3.8 or newer
- AWS CLI config / credentials in `~/.aws` for the profiles you want to scan

### Quick setup (macOS / Linux)

```bash
cd ~/elasticache_scanner
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Development setup

```bash
cd ~/elasticache_scanner
make install-dev
```

This installs development dependencies (black, flake8, mypy, pre-commit) and sets up pre-commit hooks.

### Docker setup

```bash
# Build the Docker image
docker build -t elasticache-inventory .

# Run with mounted AWS credentials and output directory
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/output:/app/output \
  elasticache-inventory --regions us-east-1 sa-east-1
```

## Usage

**Basic scan** (specify regions - required):

```bash
python3 -m elasticache_scanner --regions us-east-1 sa-east-1
```

**Scan with custom tags:**

```bash
python3 -m elasticache_scanner --regions us-east-1 --tags Team Environment Owner
```

**Parallel scan with replication groups:**

```bash
python3 -m elasticache_scanner --regions us-east-1 sa-east-1 --include-replication-groups --parallel-profiles 8
```

**Incremental scan (only changed resources):**

```bash
python3 -m elasticache_scanner --regions us-east-1 --incremental
```

**Dry run for UI testing:**

```bash
python3 -m elasticache_scanner --dry-run --sample-file elasticache_report.csv --regions us-east-1
```

**Scan specific profiles:**

```bash
python3 -m elasticache_scanner --regions us-east-1 --profile prod-profile --profile staging-profile
```

## CLI options

### Required
- `--regions REGIONS [REGIONS ...]` — AWS regions to scan (e.g., us-east-1 sa-east-1)

### Optional configuration
- `--tags TAGS [TAGS ...]` — Tags to collect from resources (default: Team)
- `--profile PROFILE` — AWS profile(s) to scan (can be used multiple times)

### Scanning options
- `--include-replication-groups` — Include replication group resources (default: clusters only)
- `--node-info` — Fetch detailed node information (increases API calls)
- `--incremental` — Only scan resources that changed since last run
- `--parallel-profiles N` — Number of profiles to scan in parallel (default: 4)

### Output options
- `--output-dir DIR` — Output directory (default: current directory)
- `--out-csv`, `--out-xlsx`, `--out-html` — Override output filenames
- `--dry-run` — Generate reports from existing CSV without AWS calls
- `--sample-file PATH` — CSV file to use for dry run

## Configuration

The tool uses a `ScanConfig` dataclass for configuration management. Key settings:

- **Regions**: Must be specified via `--regions` (no longer hard-coded)
- **Tags**: Defaults to `["Team"]` but can be customized via `--tags`
- **Parallel profiles**: Defaults to 4 concurrent profile scans
- **Incremental state**: Stored in `scan_state.json` for change detection

## Outputs and reports

- `elasticache_report.csv` — Raw CSV export of all found resources
- `elasticache_report.xlsx` — Excel workbook of the same data
- `elasticache_report.html` — Interactive HTML report with filters and charts
- `scan_errors.log` — Logging output (warnings and errors)
- `scan_failures.json` — JSON summary of failed profiles with friendly messages
- `scan_state.json` — State file for incremental scanning (auto-generated)

## HTML report details

The generated HTML report includes:

- **Interactive table**: Pagination (30 rows/page), column visibility toggles, sorting
- **Multi-select filters**: Region, Account, Team, Resource Type, and custom tags
- **Fuzzy engine matching**: Engine Groups filter supports `7.x` style grouping
- **Export capabilities**: Export filtered rows to CSV
- **Charts**: Engine versions, encryption status, regions, and top teams
- **No external dependencies**: All assets are CDN-based, no local files required

## Credential handling

The tool detects common credential issues and provides actionable guidance:

```
Profile default: AWS session token appears invalid or expired. 
Please run 'aws sso login --profile default' or refresh your credentials and try again.
```

Failed profiles are summarized in `scan_failures.json` for easy troubleshooting.

## Testing & development

### Run tests
```bash
make test
# or
pytest tests/ -v
```

### Code formatting and linting
```bash
make format  # Run black and isort
make lint    # Run flake8, mypy, and format checks
```

### Development workflow
```bash
make install-dev  # Install dev dependencies and pre-commit hooks
make run-example  # Run example scan
make dry-run      # Test UI changes without AWS calls
```

### Available make targets
Run `make help` to see all available targets including examples for different scanning modes.

## Security Checks in CI

The CI pipeline automatically runs several security checks to help keep your codebase and dependencies safe:

- **pip-audit**: Scans Python dependencies for known vulnerabilities and suggests secure versions.
- **bandit**: Analyzes Python code for common security issues (e.g., weak cryptography, unsafe exception handling).
- **truffleHog**: Scans the git history for secrets and credentials accidentally committed to the repository.
- **flake8-bugbear**: Adds extra linting for likely bugs and security issues in Python code.

These checks run on every push and pull request. If any vulnerabilities or issues are found, the CI will fail and provide details for remediation.

---

## Changelog

### v1.0.0 (2025-10-06)
- **BREAKING**: Regions are now configurable and required (use `--regions`)
- **BREAKING**: Module structure - run as `python3 -m elasticache_scanner`
- **NEW**: Configurable tags via `--tags` parameter
- **NEW**: Parallel profile scanning with `--parallel-profiles`
- **NEW**: Incremental scanning with `--incremental` and state tracking
- **NEW**: Modular codebase split into logical modules
- **NEW**: Comprehensive linting/formatting setup (black, flake8, mypy)
- **NEW**: Enhanced CLI with better help and examples
- **IMPROVED**: Friendly credential error handling with actionable messages
- **IMPROVED**: Better test coverage with mocked AWS calls

### v0.x (Previous)
- Basic scanning with hard-coded regions (us-east-1, sa-east-1)
- Hard-coded tags (CC, Email, Team)
- Single-file monolithic structure
- Sequential profile scanning

## Contributing

1. **Setup development environment:**
   ```bash
   make install-dev
   ```

2. **Make changes and test:**
   ```bash
   make format
   make lint
   make test
   ```

3. **Test with real AWS data:**
   ```bash
   make run-example
   ```

4. **Submit PR** with a clear description of changes

### Code style
- Use `black` for formatting (line length: 120)
- Follow `flake8` linting rules
- Type hints with `mypy` validation
- Pre-commit hooks enforce standards

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

For questions or issues, check the `scan_errors.log` and `scan_failures.json` files for detailed error information.
