---
name: Bug Report
about: Create a report to help us improve ElastiCache Inventory
title: '[BUG] '
labels: ['bug', 'needs-triage']
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Run command: `python3 -m elasticache_scanner --regions us-east-1 ...`
2. With configuration: '...'
3. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Error Output**
Please include relevant portions of:
- Terminal output
- `scan_errors.log` file
- `scan_failures.json` file

```
Paste error messages here
```

**Environment Information**
- OS: [e.g. macOS 14.0, Ubuntu 20.04]
- Python version: [e.g. 3.9.7]
- AWS CLI version: [e.g. 2.7.12]
- ElastiCache Inventory version: [e.g. 1.0.0]

**AWS Configuration**
- Number of profiles: [e.g. 5]
- Regions being scanned: [e.g. us-east-1, sa-east-1]
- Authentication method: [e.g. AWS SSO, IAM roles, access keys]

**Additional context**
- Are you using any specific AWS profiles or cross-account roles?
- Size of your ElastiCache environment (approximate number of clusters)?
- Any custom tags or naming conventions?
- Screenshots if applicable

**Possible Solution**
If you have ideas about what might be causing the issue or how to fix it, please share them here.