# Security Policy

## Supported Versions

We provide security updates for the following versions of ElastiCache Inventory:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability in ElastiCache Inventory, please report it responsibly.

### How to Report

**For security vulnerabilities, please do NOT create a public GitHub issue.**

Instead, please report security vulnerabilities by:

1. **Email**: Send details to [security@yourcompany.com] (replace with actual email)
2. **GitHub Security Advisories**: Use GitHub's private vulnerability reporting feature
3. **Encrypted communication**: If needed, request our PGP key

### What to Include

When reporting a vulnerability, please include:

- **Description**: Detailed description of the vulnerability
- **Impact**: What could an attacker achieve?
- **Reproduction**: Step-by-step instructions to reproduce
- **Affected versions**: Which versions are affected
- **Suggested fix**: If you have ideas for fixing it

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 5 business days  
- **Status updates**: Weekly until resolved
- **Fix timeline**: Depends on severity, typically within 30 days for critical issues

### Vulnerability Severity

We classify vulnerabilities using the following criteria:

**Critical**
- Remote code execution
- Privilege escalation
- Data exposure of sensitive AWS credentials

**High**  
- Local code execution
- Authentication bypass
- Access to unintended AWS resources

**Medium**
- Information disclosure
- Denial of service
- Configuration issues

**Low**
- Minor information leaks
- Best practice violations

## Security Best Practices for Users

### AWS Credentials

- **Use IAM roles** instead of access keys when possible
- **Follow principle of least privilege** - grant minimal required permissions
- **Use AWS SSO** for temporary credentials
- **Never commit credentials** to version control
- **Regularly rotate** access keys and credentials

### Recommended IAM Policy

Use the minimal IAM policy required for ElastiCache inventory:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "elasticache:DescribeCacheClusters",
                "elasticache:DescribeReplicationGroups",
                "elasticache:DescribeCacheSubnetGroups",
                "elasticache:DescribeCacheParameterGroups",
                "elasticache:ListTagsForResource"
            ],
            "Resource": "*"
        }
    ]
}
```

### Secure Usage

- **Run in secure environments** - avoid running on shared or untrusted systems
- **Validate outputs** - review generated reports before sharing
- **Network security** - ensure secure network connectivity to AWS
- **Log monitoring** - monitor scan logs for unexpected behavior

### Data Handling

- **Output files** contain sensitive information about your AWS infrastructure
- **Secure storage** - store output files in secure locations
- **Access control** - limit access to generated reports
- **Cleanup** - securely delete old reports when no longer needed

## Scope

This security policy covers:
- ElastiCache Inventory application code
- Default configurations and examples
- Documentation that could affect security

This policy does NOT cover:
- Third-party dependencies (report to respective projects)
- User-specific AWS configurations
- General AWS security best practices (see AWS documentation)

## Updates

This security policy may be updated from time to time. Check this document regularly for the latest information.

---

Thank you for helping keep ElastiCache Inventory and its users secure!