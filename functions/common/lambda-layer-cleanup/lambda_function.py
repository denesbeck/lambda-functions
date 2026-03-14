import boto3
import json
import logging
import time

# Initialize the Lambda client
lambda_client = boto3.client('lambda')

# Configure structured JSON logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def log(level, message, **extra):
    """Output a structured JSON log entry."""
    entry = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "level": level, "message": message, **extra}
    print(json.dumps(entry))


def get_all_layers():
    """List all Lambda layers, handling pagination."""
    layers = []
    response = lambda_client.list_layers()
    layers.extend(response.get('Layers', []))
    while 'NextMarker' in response:
        response = lambda_client.list_layers(Marker=response['NextMarker'])
        layers.extend(response.get('Layers', []))
    return layers


def get_all_layer_versions(layer_name):
    """List all versions of a Lambda layer, handling pagination."""
    versions = []
    response = lambda_client.list_layer_versions(LayerName=layer_name)
    versions.extend(response.get('LayerVersions', []))
    while 'NextMarker' in response:
        response = lambda_client.list_layer_versions(
            LayerName=layer_name, Marker=response['NextMarker']
        )
        versions.extend(response.get('LayerVersions', []))
    return versions


def cleanup_lambda_layer_versions(event, context):
    try:
        layers = get_all_layers()
        log("info", "Found layers to process", layer_count=len(layers))

        total_deleted = 0

        for layer in layers:
            layer_name = layer['LayerName']

            layer_versions = get_all_layer_versions(layer_name)
            layer_versions.sort(key=lambda x: x['Version'], reverse=True)

            versions_to_delete = layer_versions[10:]

            if versions_to_delete:
                for version in versions_to_delete:
                    version_number = version['Version']
                    lambda_client.delete_layer_version(
                        LayerName=layer_name,
                        VersionNumber=version_number
                    )
                    total_deleted += 1

                log("info", "Deleted old layer versions", layer=layer_name,
                    deleted_count=len(versions_to_delete),
                    kept_count=min(len(layer_versions), 10))
            else:
                log("info", "No versions to delete", layer=layer_name,
                    version_count=len(layer_versions))

        log("info", "Cleanup complete", total_layers=len(layers), total_deleted=total_deleted)

    except Exception as e:
        log("error", "Error cleaning up Lambda layers", error=str(e))
        raise e
