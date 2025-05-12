"""
Fixed Weaviate client initialization for v4 API.
This script can be run directly or its code can be copied into your notebook cell.
"""

import os
from dotenv import load_dotenv
import weaviate
from weaviate.auth import AuthApiKey

# Load environment variables from .env file
load_dotenv()

# Get environment variables
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")  # Default if not set

# Debug output to check if environment variables are loaded
print(f"WEAVIATE_URL: {'Set' if WEAVIATE_URL else 'Not set'}")
print(f"WEAVIATE_API_KEY: {'Set' if WEAVIATE_API_KEY else 'Not set'}")
print(f"OPENROUTER_API_KEY: {'Set' if OPENROUTER_API_KEY else 'Not set'}")
print(f"OPENROUTER_MODEL: {OPENROUTER_MODEL}")

print("Initializing Weaviate client...")
try:
    if not all([WEAVIATE_URL, WEAVIATE_API_KEY, OPENROUTER_API_KEY]):
        raise ValueError("Missing Weaviate or OpenRouter credentials in environment variables.")

    # Create authentication configuration
    auth_config = AuthApiKey(api_key=WEAVIATE_API_KEY)

    # Set up headers for OpenRouter integration
    headers = {
        "X-OpenAI-Api-Key": OPENROUTER_API_KEY  # Use this for OpenAI/compatible APIs like OpenRouter
    }

    # Import necessary modules for connection
    from weaviate.connect import ConnectionParams
    import weaviate.classes as wvc  # For schema definition helpers

    # Create connection parameters - try with different parameter names
    try:
        # First attempt with auth_credentials
        connection_params = ConnectionParams.from_url(
            url=f"https://{WEAVIATE_URL}",
            auth_credentials=auth_config,
            headers=headers
        )
        print("Using auth_credentials parameter")
    except TypeError as e:
        print(f"First attempt failed: {e}")
        try:
            # Second attempt without auth parameter, will add it to client directly
            connection_params = ConnectionParams.from_url(
                url=f"https://{WEAVIATE_URL}",
                headers=headers
            )
            print("Using connection without auth parameter")
        except Exception as e2:
            print(f"Second attempt also failed: {e2}")
            raise

    # Create the client
    try:
        # First try with just connection_params
        client = weaviate.WeaviateClient(connection_params=connection_params)
        print("Created client with connection_params only")
    except Exception as client_err:
        print(f"Client creation failed: {client_err}")
        try:
            # Try with auth parameter directly to client
            client = weaviate.WeaviateClient(
                connection_params=connection_params,
                auth_client_secret=auth_config
            )
            print("Created client with auth_client_secret parameter")
        except Exception as client_err2:
            print(f"Second client creation attempt failed: {client_err2}")
            try:
                # Third attempt using a completely different approach
                print("Trying a completely different approach...")
                # Direct connection without ConnectionParams
                client = weaviate.WeaviateClient(
                    url=f"https://{WEAVIATE_URL}",
                    auth_client_secret=auth_config,
                    additional_headers=headers
                )
                print("Created client with direct parameters")
            except Exception as client_err3:
                print(f"Third client creation attempt failed: {client_err3}")
                raise

    # Check if client is ready
    try:
        # In v4, we can check if the client is ready by making a simple API call
        meta_info = client.misc.get_meta()
        print("✅ Successfully connected to Weaviate!")
        print(f"  Version: {meta_info.version}")
    except Exception as conn_err:
        print(f"❌ Weaviate is not ready. Check URL, API key, and instance status: {conn_err}")
        client = None  # Ensure client is None if connection failed

except Exception as e:
    print(f"❌ Failed to connect to Weaviate: {e}")
    client = None
