# Contributing to ElastiCache Inventory

Thank you for your interest in contributing to ElastiCache Inventory! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Code Style](#code-style)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

By participating in this project, you agree to maintain a welcoming and inclusive environment. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- AWS CLI configured with appropriate credentials
- Basic familiarity with AWS ElastiCache

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/yourusername/elasticache-inventory.git
   cd elasticache-inventory
   ```

2. **Set up development environment:**
   ```bash
   make install-dev
   ```

   This command will:
   - Create a virtual environment
   - Install all dependencies including dev tools
   - Set up pre-commit hooks

3. **Verify setup:**
   ```bash
   make lint
   make test
   ```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-new-region-support`
- `bugfix/fix-html-export-encoding`
- `docs/improve-installation-guide`

### Commit Messages

Write clear, descriptive commit messages:
```
feat: add support for ElastiCache Serverless clusters

- Add detection logic for serverless cluster types
- Update HTML report to display serverless-specific metrics
- Add tests for serverless cluster scanning

Closes #123
```

Commit message format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test-related changes
- `refactor:` for code refactoring
- `style:` for formatting changes

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_scanner.py -v

# Run with coverage
pytest tests/ --cov=elasticache_scanner --cov-report=html
```

### Test Requirements

- All new features must include tests
- Bug fixes should include regression tests
- Maintain or improve test coverage
- Tests should be independent and repeatable

### Test Structure

```python
def test_feature_description():
    """Test that feature works as expected."""
    # Arrange
    setup_test_data()
    
    # Act
    result = function_under_test()
    
    # Assert
    assert result == expected_value
```

## Code Style

### Formatting and Linting

The project uses several tools to maintain code quality:

```bash
# Format code
make format  # Runs black and isort

# Check linting
make lint    # Runs flake8, mypy, and format checks
```

### Style Guidelines

- **Line length:** 120 characters (configured in `pyproject.toml`)
- **Import sorting:** Use `isort` (imports grouped and sorted)
- **Type hints:** Required for all public functions and methods
- **Docstrings:** Use Google-style docstrings for modules, classes, and functions

### Example Function

```python
def scan_elasticache_cluster(
    client: boto3.client, 
    cluster_id: str, 
    include_tags: bool = True
) -> Dict[str, Any]:
    """Scan a single ElastiCache cluster for metadata.
    
    Args:
        client: Boto3 ElastiCache client instance
        cluster_id: The cluster identifier to scan
        include_tags: Whether to fetch tag information
        
    Returns:
        Dictionary containing cluster metadata and configuration
        
    Raises:
        ClientError: If cluster is not accessible or doesn't exist
    """
    # Implementation here
    pass
```

### Pre-commit Hooks

Pre-commit hooks automatically run before each commit:
- `black` - Code formatting
- `isort` - Import sorting
- `flake8` - Linting
- `mypy` - Type checking

## Submitting Changes

### Pull Request Process

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes and commit:**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

3. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create a Pull Request** on GitHub with:
   - Clear title describing the change
   - Detailed description of what was changed and why
   - Reference to any related issues
   - Screenshots if UI changes are involved

### Pull Request Template

When creating a PR, include:

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Tests pass locally with my changes
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes

## Checklist
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
```

## Reporting Issues

### Bug Reports

When reporting bugs, include:

1. **Environment information:**
   - Python version
   - Operating system
   - AWS CLI version
   - ElastiCache Scanner version

2. **Steps to reproduce:**
   - Exact commands run
   - Configuration used
   - Expected vs actual behavior

3. **Logs and error messages:**
   - Content of `scan_errors.log`
   - Content of `scan_failures.json`
   - Any terminal output

### Feature Requests

When requesting features:

1. **Use case description:** Why is this feature needed?
2. **Proposed solution:** How should it work?
3. **Alternatives considered:** What other approaches were considered?
4. **Additional context:** Any other relevant information

### Issue Templates

Use the provided issue templates when available:
- Bug report template
- Feature request template
- Documentation improvement template

## Development Guidelines

### Adding New Features

1. **Design consideration:** Consider impact on existing functionality
2. **Configuration:** Add appropriate configuration options
3. **Documentation:** Update README and inline documentation
4. **Testing:** Include comprehensive tests
5. **Examples:** Add usage examples where appropriate

### Modifying Existing Features

1. **Backward compatibility:** Avoid breaking changes when possible
2. **Migration guide:** Document any necessary migration steps
3. **Deprecation warnings:** Use deprecation warnings before removing features
4. **Testing:** Ensure existing tests still pass

### Performance Considerations

- **AWS API calls:** Minimize unnecessary API calls
- **Memory usage:** Consider memory efficiency for large scans
- **Parallel execution:** Respect AWS API rate limits
- **Error handling:** Implement proper retry logic

## Getting Help

- **GitHub Issues:** For bug reports and feature requests
- **GitHub Discussions:** For questions and general discussion
- **Code Review:** Request reviews from maintainers for complex changes

## Recognition

Contributors will be recognized in:
- `CONTRIBUTORS.md` file
- Release notes for significant contributions
- GitHub contributor graphs

Thank you for contributing to ElastiCache Inventory!