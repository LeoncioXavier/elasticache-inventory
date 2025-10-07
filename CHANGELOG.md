# Changelog

All notable changes to ElastiCache Inventory will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub repository structure with CI/CD workflows
- Comprehensive security policy and vulnerability reporting process
- Issue templates for bugs, features, and documentation
- Pull request template with detailed checklist

## [1.0.0] - 2025-10-06

### Added
- **BREAKING**: Configurable regions via mandatory `--regions` parameter
- **BREAKING**: Modular package structure - run as `python3 -m elasticache_scanner`
- Configurable tags via `--tags` parameter (defaults to Team)
- Parallel profile scanning with `--parallel-profiles` option
- Incremental scanning with `--incremental` flag and state tracking
- Enhanced CLI interface with comprehensive help and examples
- Modern Python packaging with `pyproject.toml`
- Comprehensive linting and formatting setup (black, flake8, mypy, isort)
- Pre-commit hooks for code quality
- Makefile with development tasks
- Interactive HTML reports with filters and charts
- CC column support in HTML inventory with mixed data type handling
- Friendly credential error handling with actionable guidance
- Portuguese documentation (`README-pt.md`)
- Enhanced test coverage with mocked AWS calls

### Changed
- **BREAKING**: Regions are no longer hard-coded to us-east-1, sa-east-1
- **BREAKING**: Tags are no longer hard-coded to CC, Email, Team
- **BREAKING**: Script structure changed from single file to modular package
- Improved error handling and user feedback
- Better project organization and code separation
- Enhanced documentation with usage examples and migration guide

### Fixed
- HTML report filters and charts functionality
- JavaScript template placeholder issues
- Mixed data type sorting in tag columns
- Import organization and code style issues

### Removed
- Hard-coded region limitations
- Hard-coded tag restrictions
- Monolithic script structure
- Obsolete files and unused code

### Migration from v0.x
- Update commands to include `--regions` parameter
- Use `python3 -m elasticache_scanner` instead of direct script execution
- Specify custom tags with `--tags` if different from default Team tag
- Consider using `--parallel-profiles` for faster scanning
- Use `--incremental` for regular monitoring with change detection

## [0.x] - Previous Versions

### Features (Historical)
- Basic ElastiCache cluster and replication group scanning
- CSV and Excel export functionality
- Multi-profile AWS account support
- Basic HTML report generation
- Hard-coded regions (us-east-1, sa-east-1)
- Hard-coded tags (CC, Email, Team)
- Sequential profile scanning
- Monolithic script structure

---

## Release Notes Format

### Types of Changes
- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for now removed features
- `Fixed` for any bug fixes
- `Security` for vulnerability fixes

### Version Numbering
This project follows [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

### Breaking Changes
Breaking changes are clearly marked with **BREAKING** and include migration instructions.