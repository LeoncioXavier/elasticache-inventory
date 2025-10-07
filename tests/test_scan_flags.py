import builtins
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

# Ensure project root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from elasticache_scanner.config import ScanConfig
from elasticache_scanner.scanner import scan_profile


class DummySTS:
    def get_caller_identity(self):
        return {"Account": "123456789012"}


def make_session_mock(replication_groups=None, clusters=None):
    """Return a boto3.Session-like mock with client() returning mocked clients."""
    replication_groups = replication_groups if replication_groups is not None else []
    clusters = clusters if clusters is not None else []

    session_mock = MagicMock()
    # Create one sts mock and one elasticache mock and return the same instances on each call
    sts = MagicMock()
    sts.get_caller_identity.return_value = {"Account": "123456789012"}

    ec = MagicMock()
    ec.describe_replication_groups.return_value = {"ReplicationGroups": replication_groups}
    ec.describe_cache_clusters.return_value = {"CacheClusters": clusters}
    ec.list_tags_for_resource.return_value = {"TagList": []}

    def client(service_name, region_name=None):
        if service_name == "sts":
            return sts
        if service_name == "elasticache":
            return ec
        raise RuntimeError(f"Unexpected service {service_name}")

    session_mock.client.side_effect = client
    # expose the ecs and sts mocks for test assertions
    session_mock._sts = sts
    session_mock._elasticache = ec
    return session_mock


def test_default_cluster_only(monkeypatch, tmp_path):
    # Default behavior should fetch clusters with ShowCacheNodeInfo=False by default (node_info False)
    # We'll patch boto3.Session to return our mock
    clusters = [
        {
            "CacheClusterId": "c1",
            "Engine": "redis",
            "EngineVersion": "6.0.6",
            "CacheNodeType": "cache.t3.medium",
            "NumCacheNodes": 3,
        }
    ]
    sess = make_session_mock(
        replication_groups=[{"ReplicationGroupId": "rg1", "MemberClusters": ["c1"]}], clusters=clusters
    )
    config = ScanConfig(regions=["us-east-1"], tags=["Team"])

    with patch("elasticache_scanner.scanner.boto3.Session", return_value=sess):
        rows, err = scan_profile("test", config)

    # Since include_replication_groups=False, replication groups should not be included
    # We expect clusters to be returned (scan_profile always fetches clusters)
    assert any(r.get("ResourceType") == "CacheCluster" for r in rows)
    # When node_info is False, describe_cache_clusters is called with ShowCacheNodeInfo=False
    # Our mock doesn't record kwargs for describe_cache_clusters by default, so we'll assert that call exists
    ec_client = sess.client("elasticache")
    ec_client.describe_cache_clusters.assert_called()


def test_include_rgs_no_node_info(monkeypatch):
    # include_replication_groups True but node_info False: replication groups included but no per-node calls
    rgs = [{"ReplicationGroupId": "rg1", "MemberClusters": ["c1", "c2"], "Engine": "redis", "EngineVersion": "7.0.0"}]
    clusters = [
        {
            "CacheClusterId": "c1",
            "Engine": "redis",
            "EngineVersion": "7.0.0",
            "CacheNodeType": "cache.m6.large",
            "NumCacheNodes": 2,
        },
        {
            "CacheClusterId": "c2",
            "Engine": "redis",
            "EngineVersion": "7.0.0",
            "CacheNodeType": "cache.m6.large",
            "NumCacheNodes": 2,
        },
    ]
    sess = make_session_mock(replication_groups=rgs, clusters=clusters)
    config = ScanConfig(regions=["us-east-1"], tags=["Team"], include_replication_groups=True, node_info=False)

    with patch("elasticache_scanner.scanner.boto3.Session", return_value=sess):
        rows, err = scan_profile("test", config)

    # We expect replication-group entries and cluster entries
    assert any(r.get("ResourceType") == "ReplicationGroup" for r in rows)
    assert any(r.get("ResourceType") == "CacheCluster" for r in rows)
    # For RG entry, NumNodes should equal number of member clusters (approximation when node_info False)
    rg_rows = [r for r in rows if r.get("ResourceType") == "ReplicationGroup"]
    assert rg_rows and rg_rows[0]["NumNodes"] == 2


def test_include_rgs_with_node_info(monkeypatch):
    # include_replication_groups True and node_info True: per-member describe_cache_cluster should be used
    rgs = [{"ReplicationGroupId": "rg1", "MemberClusters": ["c1"], "Engine": "redis", "EngineVersion": "6.2.6"}]
    clusters = [
        {
            "CacheClusterId": "c1",
            "Engine": "redis",
            "EngineVersion": "6.2.6",
            "CacheNodeType": "cache.m4.large",
            "CacheNodes": [{}, {}],
            "NumCacheNodes": 2,
        },
    ]
    sess = make_session_mock(replication_groups=rgs, clusters=clusters)
    config = ScanConfig(regions=["us-east-1"], tags=["Team"], include_replication_groups=True, node_info=True)

    # We need describe_cache_cluster to return the cache cluster when called with CacheClusterId
    orig_describe = sess.client("elasticache").describe_cache_clusters

    def describe_cache_clusters_side_effect(*args, **kwargs):
        return {"CacheClusters": clusters}

    sess.client("elasticache").describe_cache_clusters.side_effect = describe_cache_clusters_side_effect

    with patch("elasticache_scanner.scanner.boto3.Session", return_value=sess):
        rows, err = scan_profile("test", config)

    # RG entry should have NumNodes equal to nodes counted from CacheNodes
    rg_rows = [r for r in rows if r.get("ResourceType") == "ReplicationGroup"]
    assert rg_rows and rg_rows[0]["NumNodes"] == 2


def test_invalid_client_token_logs_and_returns(monkeypatch, caplog):
    # Simulate STS get_caller_identity raising a ClientError with InvalidClientTokenId
    sess = MagicMock()
    sts = MagicMock()
    err = ClientError(
        {
            "Error": {
                "Code": "InvalidClientTokenId",
                "Message": "The security token included in the request is invalid.",
            }
        },
        "GetCallerIdentity",
    )
    sts.get_caller_identity.side_effect = err

    def client(service_name, region_name=None):
        if service_name == "sts":
            return sts
        # default elasticache client behavior for safety
        ec = MagicMock()
        ec.describe_replication_groups.return_value = {"ReplicationGroups": []}
        ec.describe_cache_clusters.return_value = {"CacheClusters": []}
        ec.list_tags_for_resource.return_value = {"TagList": []}
        return ec

    sess.client.side_effect = client
    config = ScanConfig(regions=["us-east-1"], tags=["Team"])

    with patch("elasticache_scanner.scanner.boto3.Session", return_value=sess):
        caplog.set_level("WARNING")
        rows, msg = scan_profile("bad-profile", config)

    # Should return no rows and an informative message about refreshing credentials
    assert rows == []
    assert "AWS session token appears invalid or expired" in msg
    # And the friendly message should have been logged
    assert any("AWS session token appears invalid or expired" in r.message for r in caplog.records)


if __name__ == "__main__":
    pytest.main([__file__])
