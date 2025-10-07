"""AWS client utilities and helpers."""

import logging
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def is_invalid_client_token(err: Exception) -> bool:
    """Return True if the exception looks like an invalid/expired client token error."""
    try:
        if isinstance(err, ClientError):
            code = err.response.get("Error", {}).get("Code")
            if code == "InvalidClientTokenId":
                return True
    except Exception:
        pass
    # fallback to string matching
    try:
        s = str(err)
        if "InvalidClientTokenId" in s or "invalid client token id" in s.lower() or "expired" in s.lower():
            return True
    except Exception:
        pass
    return False


def get_available_profiles() -> List[str]:
    """Return a list of available AWS profiles from boto3 session."""
    sess = boto3.Session()
    profiles = list(sess.available_profiles or [])
    # If 'default' isn't in available_profiles include it; boto3 treats default specially
    if "default" not in profiles:
        profiles.append("default")
    return profiles


def list_tags_for_resource(client, resource_arn: str) -> Dict[str, str]:
    """List tags for an ElastiCache resource."""
    try:
        resp = client.list_tags_for_resource(ResourceName=resource_arn)
        taglist = resp.get("TagList", [])
        return {t["Key"]: t["Value"] for t in taglist}
    except Exception as e:
        if is_invalid_client_token(e):
            logger.error(
                f"Failed to list tags for {resource_arn}: credentials appear invalid or expired. "
                "Refresh your AWS session."
            )
            raise
        logger.warning(f"Failed to list tags for {resource_arn}: {e}")
        return {}


def describe_cache_cluster(session: boto3.session.Session, region: str, cluster_id: str) -> Dict[str, Any]:
    """Describe a specific cache cluster with node details."""
    client = session.client("elasticache", region_name=region)
    try:
        resp = client.describe_cache_clusters(CacheClusterId=cluster_id, ShowCacheNodeInfo=True)
        clusters = resp.get("CacheClusters", [])
        if clusters:
            return clusters[0]
    except Exception as e:
        if is_invalid_client_token(e):
            logger.warning(
                f"Failed to describe cache cluster {cluster_id} in {region}: "
                "credentials appear invalid or expired. Refresh your AWS session."
            )
            raise
        logger.warning(f"Failed to describe cache cluster {cluster_id} in {region}: {e}")
    return {}


def format_creation_time_from_cluster(cc: Dict[str, Any]) -> str:
    """Extract and format creation time from cluster metadata."""
    # Try known keys for creation timestamps and return first found in ISO format
    for k in ("CacheClusterCreateTime", "ClusterCreateTime", "SnapshotCreateTime"):
        v = cc.get(k)
        if v:
            try:
                return v.isoformat()
            except Exception:
                return str(v)
    return ""


def try_construct_arn(resource_type: str, region: str, account_id: str, resource_id: str) -> str:
    """Attempt to construct an ElastiCache ARN for the resource."""
    if resource_type not in ("replication-group", "cluster"):
        return ""
    return f"arn:aws:elasticache:{region}:{account_id}:{resource_type}:{resource_id}"


def calculate_resource_hash(resource_data: Dict[str, Any]) -> str:
    """Calculate a hash for a resource to detect changes in incremental scanning."""
    # Create a stable hash based on key resource attributes
    import hashlib

    key_fields = [
        resource_data.get("Engine", ""),
        resource_data.get("EngineVersion", ""),
        resource_data.get("NodeTypes", ""),
        str(resource_data.get("NumNodes", 0)),
        str(resource_data.get("AtRestEncryptionEnabled", False)),
        str(resource_data.get("TransitEncryptionEnabled", False)),
        resource_data.get("CC", ""),
        resource_data.get("Email", ""),
        resource_data.get("Team", ""),
    ]

    content = "|".join(key_fields)
    return hashlib.md5(content.encode()).hexdigest()
