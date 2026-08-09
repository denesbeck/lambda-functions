import boto3
import json
import logging
import os
import time

# Initialize the Lambda client
lambda_client = boto3.client('lambda')

# Configure structured JSON logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

KEEP_VERSIONS = 10


def log(level, message, **extra):
    """Output a structured JSON log entry."""
    entry = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "level": level, "message": message, **extra}
    print(json.dumps(entry))


def get_managed_layer_names():
    """Read the allowlist of layers this function may prune from MANAGED_LAYER_NAMES."""
    raw = os.environ.get('MANAGED_LAYER_NAMES', '')
    return [name.strip() for name in raw.split(',') if name.strip()]


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
    layer_names = get_managed_layer_names()
    if not layer_names:
        log("info", "MANAGED_LAYER_NAMES is empty, nothing to clean up")
        return

    log("info", "Found layers to process", layer_count=len(layer_names))

    total_deleted = 0
    failed_layers = []

    for layer_name in layer_names:
        try:
            layer_versions = get_all_layer_versions(layer_name)
            layer_versions.sort(key=lambda x: x['Version'], reverse=True)

            versions_to_delete = layer_versions[KEEP_VERSIONS:]

            if versions_to_delete:
                for version in versions_to_delete:
                    lambda_client.delete_layer_version(
                        LayerName=layer_name,
                        VersionNumber=version['Version']
                    )
                    total_deleted += 1

                log("info", "Deleted old layer versions", layer=layer_name,
                    deleted_count=len(versions_to_delete),
                    kept_count=min(len(layer_versions), KEEP_VERSIONS))
            else:
                log("info", "No versions to delete", layer=layer_name,
                    version_count=len(layer_versions))
        except Exception as e:
            failed_layers.append(layer_name)
            log("error", "Error cleaning up layer", layer=layer_name, error=str(e))

    log("info", "Cleanup complete", total_layers=len(layer_names),
        total_deleted=total_deleted, failed_layers=failed_layers)

    if failed_layers:
        raise RuntimeError(f"Cleanup failed for layers: {', '.join(failed_layers)}")
