import sys
import os
import pytest
from unittest.mock import patch, MagicMock

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

# Mock boto3.client BEFORE importing lambda_function, because the module
# calls boto3.client('lambda') at module level. Without AWS credentials/region
# configured (e.g. in CI), this would raise botocore.exceptions.NoRegionError.
mock_lambda_client = MagicMock()

with patch("boto3.client", return_value=mock_lambda_client):
    import lambda_function


@pytest.fixture(autouse=True)
def reset_mock():
    """Reset the mock client before each test, clearing all state."""
    mock_lambda_client.reset_mock(side_effect=True, return_value=True)
    lambda_function.lambda_client = mock_lambda_client
    yield mock_lambda_client


class TestGetAllLayers:
    def test_single_page(self, reset_mock):
        mock_lambda_client.list_layers.return_value = {
            "Layers": [
                {"LayerName": "layer-1"},
                {"LayerName": "layer-2"},
            ]
        }

        result = lambda_function.get_all_layers()
        assert len(result) == 2
        assert result[0]["LayerName"] == "layer-1"
        mock_lambda_client.list_layers.assert_called_once()

    def test_multiple_pages(self, reset_mock):
        mock_lambda_client.list_layers.side_effect = [
            {
                "Layers": [{"LayerName": f"layer-{i}"} for i in range(50)],
                "NextMarker": "marker-1",
            },
            {
                "Layers": [{"LayerName": f"layer-{i}"} for i in range(50, 75)],
            },
        ]

        result = lambda_function.get_all_layers()
        assert len(result) == 75
        assert mock_lambda_client.list_layers.call_count == 2

    def test_empty_response(self, reset_mock):
        mock_lambda_client.list_layers.return_value = {"Layers": []}

        result = lambda_function.get_all_layers()
        assert result == []


class TestGetAllLayerVersions:
    def test_single_page(self, reset_mock):
        mock_lambda_client.list_layer_versions.return_value = {
            "LayerVersions": [
                {"Version": 1},
                {"Version": 2},
            ]
        }

        result = lambda_function.get_all_layer_versions("test-layer")
        assert len(result) == 2
        mock_lambda_client.list_layer_versions.assert_called_once_with(
            LayerName="test-layer"
        )

    def test_multiple_pages(self, reset_mock):
        mock_lambda_client.list_layer_versions.side_effect = [
            {
                "LayerVersions": [{"Version": i} for i in range(50, 0, -1)],
                "NextMarker": "marker-1",
            },
            {
                "LayerVersions": [{"Version": i} for i in range(51, 75)],
            },
        ]

        result = lambda_function.get_all_layer_versions("test-layer")
        assert len(result) == 74
        assert mock_lambda_client.list_layer_versions.call_count == 2


class TestCleanupLambdaLayerVersions:
    def test_deletes_versions_beyond_10(self, reset_mock):
        """Should keep latest 10 and delete the rest."""
        mock_lambda_client.list_layers.return_value = {
            "Layers": [{"LayerName": "my-layer"}]
        }
        # 15 versions, versions 15 down to 1
        mock_lambda_client.list_layer_versions.return_value = {
            "LayerVersions": [{"Version": i} for i in range(15, 0, -1)]
        }

        lambda_function.cleanup_lambda_layer_versions({}, None)

        # Should delete versions 5, 4, 3, 2, 1 (the 5 oldest)
        delete_calls = mock_lambda_client.delete_layer_version.call_args_list
        assert len(delete_calls) == 5
        deleted_versions = sorted(
            [c.kwargs["VersionNumber"] for c in delete_calls]
        )
        assert deleted_versions == [1, 2, 3, 4, 5]

    def test_no_deletions_when_10_or_fewer_versions(self, reset_mock):
        """Should not delete anything when there are 10 or fewer versions."""
        mock_lambda_client.list_layers.return_value = {
            "Layers": [{"LayerName": "my-layer"}]
        }
        mock_lambda_client.list_layer_versions.return_value = {
            "LayerVersions": [{"Version": i} for i in range(10, 0, -1)]
        }

        lambda_function.cleanup_lambda_layer_versions({}, None)

        mock_lambda_client.delete_layer_version.assert_not_called()

    def test_handles_multiple_layers(self, reset_mock):
        """Should process all layers independently."""
        mock_lambda_client.list_layers.return_value = {
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

        mock_lambda_client.list_layer_versions.side_effect = (
            list_versions_side_effect
        )

        lambda_function.cleanup_lambda_layer_versions({}, None)

        # layer-a: 12 versions, delete 2 (versions 1 and 2)
        # layer-b: 5 versions, delete 0
        delete_calls = mock_lambda_client.delete_layer_version.call_args_list
        assert len(delete_calls) == 2
        for c in delete_calls:
            assert c.kwargs["LayerName"] == "layer-a"

    def test_no_layers(self, reset_mock):
        """Should handle empty account with no layers."""
        mock_lambda_client.list_layers.return_value = {"Layers": []}

        lambda_function.cleanup_lambda_layer_versions({}, None)

        mock_lambda_client.list_layer_versions.assert_not_called()
        mock_lambda_client.delete_layer_version.assert_not_called()

    def test_raises_on_error(self, reset_mock):
        """Should re-raise exceptions after logging."""
        mock_lambda_client.list_layers.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            lambda_function.cleanup_lambda_layer_versions({}, None)
