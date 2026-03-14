import sys
import os
import pytest
from unittest.mock import patch, MagicMock, call

# Add the function directory to the path so we can import it
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "functions",
        "common",
        "lambda-layer-cleanup",
    ),
)


@pytest.fixture(autouse=True)
def mock_boto3_client():
    """Mock the boto3 Lambda client for all tests."""
    with patch("lambda_function.lambda_client") as mock_client:
        yield mock_client


@pytest.fixture
def reload_module(mock_boto3_client):
    """Reimport the module to get fresh references."""
    import lambda_function

    return lambda_function


class TestGetAllLayers:
    def test_single_page(self, reload_module, mock_boto3_client):
        mock_boto3_client.list_layers.return_value = {
            "Layers": [
                {"LayerName": "layer-1"},
                {"LayerName": "layer-2"},
            ]
        }

        result = reload_module.get_all_layers()
        assert len(result) == 2
        assert result[0]["LayerName"] == "layer-1"
        mock_boto3_client.list_layers.assert_called_once()

    def test_multiple_pages(self, reload_module, mock_boto3_client):
        mock_boto3_client.list_layers.side_effect = [
            {
                "Layers": [{"LayerName": f"layer-{i}"} for i in range(50)],
                "NextMarker": "marker-1",
            },
            {
                "Layers": [{"LayerName": f"layer-{i}"} for i in range(50, 75)],
            },
        ]

        result = reload_module.get_all_layers()
        assert len(result) == 75
        assert mock_boto3_client.list_layers.call_count == 2

    def test_empty_response(self, reload_module, mock_boto3_client):
        mock_boto3_client.list_layers.return_value = {"Layers": []}

        result = reload_module.get_all_layers()
        assert result == []


class TestGetAllLayerVersions:
    def test_single_page(self, reload_module, mock_boto3_client):
        mock_boto3_client.list_layer_versions.return_value = {
            "LayerVersions": [
                {"Version": 1},
                {"Version": 2},
            ]
        }

        result = reload_module.get_all_layer_versions("test-layer")
        assert len(result) == 2
        mock_boto3_client.list_layer_versions.assert_called_once_with(
            LayerName="test-layer"
        )

    def test_multiple_pages(self, reload_module, mock_boto3_client):
        mock_boto3_client.list_layer_versions.side_effect = [
            {
                "LayerVersions": [{"Version": i} for i in range(50, 0, -1)],
                "NextMarker": "marker-1",
            },
            {
                "LayerVersions": [{"Version": i} for i in range(51, 75)],
            },
        ]

        result = reload_module.get_all_layer_versions("test-layer")
        assert len(result) == 74
        assert mock_boto3_client.list_layer_versions.call_count == 2


class TestCleanupLambdaLayerVersions:
    def test_deletes_versions_beyond_10(self, reload_module, mock_boto3_client):
        """Should keep latest 10 and delete the rest."""
        mock_boto3_client.list_layers.return_value = {
            "Layers": [{"LayerName": "my-layer"}]
        }
        # 15 versions, versions 15 down to 1
        mock_boto3_client.list_layer_versions.return_value = {
            "LayerVersions": [{"Version": i} for i in range(15, 0, -1)]
        }

        reload_module.cleanup_lambda_layer_versions({}, None)

        # Should delete versions 5, 4, 3, 2, 1 (the 5 oldest)
        delete_calls = mock_boto3_client.delete_layer_version.call_args_list
        assert len(delete_calls) == 5
        deleted_versions = sorted(
            [c.kwargs["VersionNumber"] for c in delete_calls]
        )
        assert deleted_versions == [1, 2, 3, 4, 5]

    def test_no_deletions_when_10_or_fewer_versions(
        self, reload_module, mock_boto3_client
    ):
        """Should not delete anything when there are 10 or fewer versions."""
        mock_boto3_client.list_layers.return_value = {
            "Layers": [{"LayerName": "my-layer"}]
        }
        mock_boto3_client.list_layer_versions.return_value = {
            "LayerVersions": [{"Version": i} for i in range(10, 0, -1)]
        }

        reload_module.cleanup_lambda_layer_versions({}, None)

        mock_boto3_client.delete_layer_version.assert_not_called()

    def test_handles_multiple_layers(self, reload_module, mock_boto3_client):
        """Should process all layers independently."""
        mock_boto3_client.list_layers.return_value = {
            "Layers": [
                {"LayerName": "layer-a"},
                {"LayerName": "layer-b"},
            ]
        }

        def list_versions_side_effect(LayerName):
            if LayerName == "layer-a":
                return {
                    "LayerVersions": [{"Version": i} for i in range(12, 0, -1)]
                }
            else:
                return {
                    "LayerVersions": [{"Version": i} for i in range(5, 0, -1)]
                }

        mock_boto3_client.list_layer_versions.side_effect = (
            list_versions_side_effect
        )

        reload_module.cleanup_lambda_layer_versions({}, None)

        # layer-a: 12 versions, delete 2 (versions 1 and 2)
        # layer-b: 5 versions, delete 0
        delete_calls = mock_boto3_client.delete_layer_version.call_args_list
        assert len(delete_calls) == 2
        for c in delete_calls:
            assert c.kwargs["LayerName"] == "layer-a"

    def test_no_layers(self, reload_module, mock_boto3_client):
        """Should handle empty account with no layers."""
        mock_boto3_client.list_layers.return_value = {"Layers": []}

        reload_module.cleanup_lambda_layer_versions({}, None)

        mock_boto3_client.list_layer_versions.assert_not_called()
        mock_boto3_client.delete_layer_version.assert_not_called()

    def test_raises_on_error(self, reload_module, mock_boto3_client):
        """Should re-raise exceptions after logging."""
        mock_boto3_client.list_layers.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            reload_module.cleanup_lambda_layer_versions({}, None)
