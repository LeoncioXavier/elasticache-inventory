"""Core scanning logic for ElastiCache resources."""

import logging
from typing import Any, Dict, List, Optional, Tuple

import boto3

from .aws_utils import (
    calculate_resource_hash,
    describe_cache_cluster,
    format_creation_time_from_cluster,
    is_invalid_client_token,
    list_tags_for_resource,
    try_construct_arn,
)
from .config import ScanConfig

logger = logging.getLogger(__name__)


def scan_profile(
    profile: str, config: ScanConfig, previous_state: Optional[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Scan a single AWS profile for ElastiCache resources.

    Args:
        profile: AWS profile name
        config: Scan configuration
        previous_state: Previous scan state for incremental scanning

    Returns:
        Tuple of (resource_rows, error_message)
    """
    rows: List[Dict[str, Any]] = []
    logger.info(f"Scanning profile: {profile}")

    try:
        session = boto3.Session(profile_name=profile)
        sts = session.client("sts")
        account_id = sts.get_caller_identity()["Account"]
    except Exception as e:
        # Detect expired/invalid SSO/session token issues and provide a helpful message
        if is_invalid_client_token(e):
            friendly = (
                f"Profile {profile}: AWS session token appears invalid or expired. "
                f"Please run 'aws sso login --profile {profile}' or refresh your credentials and try again."
            )
            logger.warning(friendly)
            # Avoid printing the full stack trace for expired/invalid credentials — it's noisy
            logger.debug("STS/GetCallerIdentity failure details: %s", e)
            return rows, friendly
        else:
            # For other unexpected errors include the full traceback to aid debugging
            logger.exception(e)

        logger.warning(f"Profile {profile} failed to create session or STS call: {str(e)}")
        return rows, str(e)

    # Get previous state for this profile if doing incremental scanning
    profile_previous_state = {}
    if previous_state and config.incremental:
        profile_previous_state = previous_state.get("profiles", {}).get(profile, {})

    for region in config.regions:
        logger.info(f"  Region: {region}")
        try:
            client = session.client("elasticache", region_name=region)
        except Exception as e:
            logger.warning(f"  Could not create Elasticache client for {profile} @ {region}: {e}")
            continue

        # Scan replication groups if requested
        if config.include_replication_groups:
            rows.extend(
                _scan_replication_groups(client, session, profile, account_id, region, config, profile_previous_state)
            )

        # Scan cache clusters
        rows.extend(_scan_cache_clusters(client, session, profile, account_id, region, config, profile_previous_state))

    return rows, ""


def _get_replication_group_node_info(
    session: boto3.session.Session,
    region: str,
    member_clusters: List[str],
    config: ScanConfig,
) -> tuple:
    """Get node information for replication group member clusters."""
    node_types = set()
    total_nodes = 0
    creation_times: List[str] = []
    resource_arn = None

    if config.node_info:
        # fetch per-member cluster details only if node_info requested
        for mc in member_clusters:
            cc = describe_cache_cluster(session, region, mc)
            if cc:
                nt = cc.get("CacheNodeType")
                if nt:
                    node_types.add(nt)
                nodes = cc.get("CacheNodes", []) or []
                total_nodes += len(nodes)
                ctime = format_creation_time_from_cluster(cc)
                if ctime:
                    creation_times.append(ctime)
                if not resource_arn:
                    resource_arn = cc.get("ARN") or cc.get("ReplicationGroupId")
    else:
        # If skipping node info, just approximate nodes by the number of member clusters
        total_nodes = len(member_clusters)

    return node_types, total_nodes, creation_times, resource_arn


def _build_replication_group_row(
    rg: Dict[str, Any],
    profile: str,
    account_id: str,
    region: str,
    config: ScanConfig,
    client: Any,
    session: boto3.session.Session,
) -> Dict[str, Any]:
    """Build a row dictionary for a replication group."""
    rg_id = rg.get("ReplicationGroupId")
    engine = rg.get("Engine")
    engine_version = rg.get("EngineVersion")
    at_rest = rg.get("AtRestEncryptionEnabled", False)
    transit = rg.get("TransitEncryptionEnabled", False)
    member_clusters = rg.get("MemberClusters", [])

    # Get node information
    node_types, total_nodes, creation_times, resource_arn = _get_replication_group_node_info(
        session, region, member_clusters, config
    )

    # Construct ARN if not found
    if not resource_arn and rg_id:
        resource_arn = try_construct_arn("replication-group", region, account_id, rg_id)
    if not resource_arn:
        resource_arn = rg.get("ARN") or rg.get("ReplicationGroupARN")

    # Get tags
    tags: Dict[str, str] = {}
    if resource_arn:
        tags = list_tags_for_resource(client, resource_arn) or {}

    creation_time = min(creation_times) if creation_times else ""

    row = {
        "Profile": profile,
        "AccountId": account_id,
        "Region": region,
        "ResourceType": "ReplicationGroup",
        "ResourceId": rg_id,
        "Engine": engine,
        "EngineVersion": engine_version,
        "CreationTime": creation_time,
        "NodeTypes": ";".join(sorted(node_types)) if node_types else "",
        "NumNodes": total_nodes,
        "AtRestEncryptionEnabled": bool(at_rest),
        "TransitEncryptionEnabled": bool(transit),
        "ARN": resource_arn or "",
    }

    # Add requested tags
    for tag in config.tags:
        row[tag] = tags.get(tag, "not found")

    return row


def _scan_replication_groups(
    client: Any,
    session: boto3.session.Session,
    profile: str,
    account_id: str,
    region: str,
    config: ScanConfig,
    previous_state: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Scan replication groups in a region."""
    rows: List[Dict[str, Any]] = []

    try:
        resp = client.describe_replication_groups()
        rgs = resp.get("ReplicationGroups", [])
    except Exception as e:
        if is_invalid_client_token(e):
            friendly = (
                f"Profile {profile} @ {region}: AWS session token appears invalid or expired. "
                f"Please run 'aws sso login --profile {profile}' or refresh your credentials and try again."
            )
            logger.warning(friendly)
            raise
        logger.warning(f"  Failed to describe replication groups for {profile} @ {region}: {e}")
        return rows

    for rg in rgs:
        try:
            rg_id = rg.get("ReplicationGroupId")

            # Check if this resource changed (for incremental scanning)
            if config.incremental and _resource_unchanged(rg_id, rg, previous_state, region):
                logger.debug(f"  Skipping unchanged replication group: {rg_id}")
                continue

            row = _build_replication_group_row(rg, profile, account_id, region, config, client, session)
            rows.append(row)

        except Exception as e:
            logger.warning(f"  Error processing replication group in {profile} @ {region}: {e}")

    return rows


def _extract_cache_cluster_node_info(cc: Dict[str, Any]) -> tuple:
    """Extract node information from cache cluster data."""
    node_types = set()
    nt = cc.get("CacheNodeType")
    if nt:
        node_types.add(nt)

    # If we didn't request node info, CacheNodes may be absent; fall back to NumCacheNodes
    nodes = cc.get("CacheNodes", []) or []
    num_nodes = len(nodes)
    if num_nodes == 0:
        num_nodes = cc.get("NumCacheNodes") or cc.get("NumNodes") or 0

    return node_types, num_nodes


def _build_cache_cluster_row(
    cc: Dict[str, Any],
    profile: str,
    account_id: str,
    region: str,
    config: ScanConfig,
    client: Any,
) -> Dict[str, Any]:
    """Build a row dictionary for a cache cluster."""
    cc_id = cc.get("CacheClusterId")
    engine = cc.get("Engine")
    engine_version = cc.get("EngineVersion")
    at_rest = cc.get("AtRestEncryptionEnabled", False)
    transit = cc.get("TransitEncryptionEnabled", False)

    # Extract node information
    node_types, num_nodes = _extract_cache_cluster_node_info(cc)

    # Get ARN
    resource_arn = cc.get("ARN") or cc.get("ClusterARN")
    if not resource_arn and cc_id:
        resource_arn = try_construct_arn("cluster", region, account_id, cc_id)

    # Get tags
    tags = {}
    if resource_arn:
        tags = list_tags_for_resource(client, resource_arn) or {}

    creation_time = format_creation_time_from_cluster(cc)

    row = {
        "Profile": profile,
        "AccountId": account_id,
        "Region": region,
        "ResourceType": "CacheCluster",
        "ResourceId": cc_id,
        "Engine": engine,
        "EngineVersion": engine_version,
        "CreationTime": creation_time,
        "NodeTypes": ";".join(sorted(node_types)) if node_types else "",
        "NumNodes": num_nodes,
        "AtRestEncryptionEnabled": bool(at_rest),
        "TransitEncryptionEnabled": bool(transit),
        "ARN": resource_arn or "",
    }

    # Add requested tags
    for tag in config.tags:
        row[tag] = tags.get(tag, "not found")

    return row


def _scan_cache_clusters(
    client: Any,
    session: boto3.session.Session,
    profile: str,
    account_id: str,
    region: str,
    config: ScanConfig,
    previous_state: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Scan cache clusters in a region."""
    rows: List[Dict[str, Any]] = []

    try:
        # If node_info is False, avoid fetching per-node details to speed up the call
        resp = client.describe_cache_clusters(ShowCacheNodeInfo=bool(config.node_info))
        clusters = resp.get("CacheClusters", [])
    except Exception as e:
        if is_invalid_client_token(e):
            friendly = (
                f"Profile {profile} @ {region}: AWS session token appears invalid or expired. "
                f"Please run 'aws sso login --profile {profile}' or refresh your credentials and try again."
            )
            logger.warning(friendly)
            raise
        logger.warning(f"  Failed to describe cache clusters for {profile} @ {region}: {e}")
        return rows

    for cc in clusters:
        try:
            cc_id = cc.get("CacheClusterId")

            # Check if this resource changed (for incremental scanning)
            if config.incremental and _resource_unchanged(cc_id, cc, previous_state, region):
                logger.debug(f"  Skipping unchanged cache cluster: {cc_id}")
                continue

            row = _build_cache_cluster_row(cc, profile, account_id, region, config, client)
            rows.append(row)

        except Exception as e:
            logger.warning(f"  Error processing cache cluster in {profile} @ {region}: {e}")

    return rows


def _resource_unchanged(
    resource_id: str, resource_data: Dict[str, Any], previous_state: Dict[str, Any], region: str
) -> bool:
    """Check if a resource has changed since the last scan."""
    if not previous_state:
        return False

    region_state = previous_state.get("regions", {}).get(region, {})
    resource_state = region_state.get(resource_id, {})

    if not resource_state:
        return False

    # Calculate current resource hash
    current_hash = calculate_resource_hash(resource_data)
    previous_hash = str(resource_state.get("hash", ""))

    return bool(current_hash == previous_hash)
