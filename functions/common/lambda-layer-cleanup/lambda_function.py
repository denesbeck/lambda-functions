import boto3
import logging

# Initialize the Lambda client
lambda_client = boto3.client('lambda')

def cleanup_lambda_layer_versions(event, context):
    try:
        # List all layers in the account
        response = lambda_client.list_layers()
        layers = response.get('Layers', [])
        
        # Loop through each layer in the account
        for layer in layers:
            layer_name = layer['LayerName']
            print(f"Processing layer: {layer_name}")
            
            # List all versions of the current layer
            version_response = lambda_client.list_layer_versions(LayerName=layer_name)
            layer_versions = version_response.get('LayerVersions', [])
            
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
