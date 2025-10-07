"""Tests for elasticache_scanner.aws_utils module."""

import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

from elasticache_scanner.aws_utils import (
    get_available_profiles,
    list_tags_for_resource,
    describe_cache_cluster,
    format_creation_time_from_cluster,
    try_construct_arn,
    calculate_resource_hash,
    is_invalid_client_token
)


def test_get_available_profiles_with_config_file():
    """Test getting available profiles when config file exists."""
    mock_profiles = ['default', 'dev', 'prod']
    
    with patch('boto3.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.available_profiles = mock_profiles
        mock_session_class.return_value = mock_session
        
        result = get_available_profiles()
        
        # Should include default even if it's already in the list
        assert 'default' in result
        assert 'dev' in result
        assert 'prod' in result


def test_get_available_profiles_no_default():
    """Test that default profile is added if not present."""
    mock_profiles = ['dev', 'prod']
    
    with patch('boto3.Session') as mock_session_class:
        mock_session = MagicMock()
        mock_session.available_profiles = mock_profiles
        mock_session_class.return_value = mock_session
        
        result = get_available_profiles()
        
        assert 'default' in result
        assert 'dev' in result
        assert 'prod' in result


def test_list_tags_for_resource_success():
    """Test successful tag listing."""
    mock_client = MagicMock()
    mock_client.list_tags_for_resource.return_value = {
        'TagList': [
            {'Key': 'Team', 'Value': 'DevOps'},
            {'Key': 'Environment', 'Value': 'Production'}
        ]
    }
    
    result = list_tags_for_resource(mock_client, 'arn:aws:elasticache:us-east-1:123456789012:cluster:my-cluster')
    
    expected = {'Team': 'DevOps', 'Environment': 'Production'}
    assert result == expected


def test_list_tags_for_resource_invalid_token():
    """Test tag listing with invalid token error."""
    mock_client = MagicMock()
    error = ClientError(
        error_response={'Error': {'Code': 'InvalidClientTokenId'}},
        operation_name='ListTagsForResource'
    )
    mock_client.list_tags_for_resource.side_effect = error
    
    # Should log error and re-raise since it's an auth issue
    with pytest.raises(ClientError):
        list_tags_for_resource(mock_client, 'test-arn')


def test_list_tags_for_resource_other_error():
    """Test tag listing with other errors returns empty dict."""
    mock_client = MagicMock()
    mock_client.list_tags_for_resource.side_effect = Exception("Some other error")
    
    result = list_tags_for_resource(mock_client, 'test-arn')
    assert result == {}


def test_describe_cache_cluster_success():
    """Test successful cache cluster description."""
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session.client.return_value = mock_client
    
    cluster_data = {
        'CacheClusterId': 'test-cluster',
        'CacheNodeType': 'cache.t3.micro',
        'CacheNodes': []
    }
    
    mock_client.describe_cache_clusters.return_value = {
        'CacheClusters': [cluster_data]
    }
    
    result = describe_cache_cluster(mock_session, 'us-east-1', 'test-cluster')
    assert result == cluster_data


def test_describe_cache_cluster_not_found():
    """Test cache cluster description when cluster not found."""
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session.client.return_value = mock_client
    
    mock_client.describe_cache_clusters.return_value = {'CacheClusters': []}
    
    result = describe_cache_cluster(mock_session, 'us-east-1', 'nonexistent-cluster')
    assert result == {}


def test_describe_cache_cluster_invalid_token():
    """Test cache cluster description with invalid token."""
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session.client.return_value = mock_client
    
    error = ClientError(
        error_response={'Error': {'Code': 'InvalidClientTokenId'}},
        operation_name='DescribeCacheClusters'
    )
    mock_client.describe_cache_clusters.side_effect = error
    
    # Should log error and re-raise since it's an auth issue
    with pytest.raises(ClientError):
        describe_cache_cluster(mock_session, 'us-east-1', 'test-cluster')


def test_format_creation_time_from_cluster_with_datetime():
    """Test formatting creation time from datetime object."""
    from datetime import datetime
    test_time = datetime(2023, 1, 1, 12, 0, 0)
    
    cluster = {'CacheClusterCreateTime': test_time}
    result = format_creation_time_from_cluster(cluster)
    
    assert result == "2023-01-01T12:00:00"


def test_format_creation_time_from_cluster_with_string():
    """Test formatting creation time from string."""
    cluster = {'CacheClusterCreateTime': "2023-01-01T12:00:00Z"}
    result = format_creation_time_from_cluster(cluster)
    
    assert result == "2023-01-01T12:00:00Z"


def test_format_creation_time_from_cluster_no_time():
    """Test formatting when no creation time is available."""
    cluster = {}
    result = format_creation_time_from_cluster(cluster)
    
    assert result == ""


def test_try_construct_arn():
    """Test ARN construction."""
    result = try_construct_arn('cluster', 'us-east-1', '123456789012', 'my-cluster')
    expected = 'arn:aws:elasticache:us-east-1:123456789012:cluster:my-cluster'
    
    assert result == expected


def test_calculate_resource_hash():
    """Test resource hash calculation."""
    # Hash is based on specific fields: Engine, EngineVersion, NodeTypes, NumNodes, 
    # AtRestEncryptionEnabled, TransitEncryptionEnabled, CC, Email, Team
    resource1 = {
        'Engine': 'redis', 
        'EngineVersion': '6.2', 
        'NodeTypes': 'cache.t3.micro',
        'NumNodes': 1,
        'AtRestEncryptionEnabled': True,
        'TransitEncryptionEnabled': False,
        'Team': 'DevOps'
    }
    resource2 = {
        'Engine': 'redis', 
        'EngineVersion': '6.2', 
        'NodeTypes': 'cache.t3.micro',
        'NumNodes': 1,
        'AtRestEncryptionEnabled': True,
        'TransitEncryptionEnabled': False,
        'Team': 'DevOps'
    }
    resource3 = {
        'Engine': 'redis', 
        'EngineVersion': '6.2', 
        'NodeTypes': 'cache.t3.micro',
        'NumNodes': 2,  # Different number of nodes
        'AtRestEncryptionEnabled': True,
        'TransitEncryptionEnabled': False,
        'Team': 'DevOps'
    }
    
    hash1 = calculate_resource_hash(resource1)
    hash2 = calculate_resource_hash(resource2)
    hash3 = calculate_resource_hash(resource3)
    
    # Same resources should have same hash
    assert hash1 == hash2
    # Different resources should have different hash
    assert hash1 != hash3
    
    # Hash should be a string
    assert isinstance(hash1, str)


def test_is_invalid_client_token_true_cases():
    """Test cases where token is considered invalid."""
    # Test with the actual error code that is checked
    error = ClientError(
        error_response={'Error': {'Code': 'InvalidClientTokenId'}},
        operation_name='TestOperation'
    )
    assert is_invalid_client_token(error) is True
    
    # Test with string matching
    error_with_string = Exception("InvalidClientTokenId occurred")
    assert is_invalid_client_token(error_with_string) is True
    
    error_with_expired = Exception("token expired")
    assert is_invalid_client_token(error_with_expired) is True


def test_is_invalid_client_token_false_cases():
    """Test cases where token is considered valid but other error occurred."""
    valid_codes = [
        'ResourceNotFound',
        'ThrottlingException',
        'InternalError'
    ]
    
    for code in valid_codes:
        error = ClientError(
            error_response={'Error': {'Code': code}},
            operation_name='TestOperation'
        )
        assert is_invalid_client_token(error) is False


def test_is_invalid_client_token_non_client_error():
    """Test with non-ClientError exception."""
    error = ValueError("Some other error")
    assert is_invalid_client_token(error) is False