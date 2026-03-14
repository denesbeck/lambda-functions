import boto3
import logging

# Initialize the Lambda client
lambda_client = boto3.client('lambda')


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

        # Loop through each layer in the account
        for layer in layers:
            layer_name = layer['LayerName']
            print(f"Processing layer: {layer_name}")

            # List all versions of the current layer
            layer_versions = get_all_layer_versions(layer_name)

            # Sort the versions by the version number (in descending order)
            layer_versions.sort(key=lambda x: x['Version'], reverse=True)

            # Only keep the latest 10 versions
            versions_to_delete = layer_versions[10:]

            if versions_to_delete:
                for version in versions_to_delete:
                    version_number = version['Version']
                    print(f"Deleting layer {layer_name} version: {version_number}")

                    # Delete the older layer version
                    lambda_client.delete_layer_version(
                        LayerName=layer_name,
                        VersionNumber=version_number
                    )
            else:
                print(f"No versions to delete for layer {layer_name}, keeping the latest 10.")

    except Exception as e:
        logging.error(f"Error cleaning up Lambda layers: {str(e)}")
        raise e
