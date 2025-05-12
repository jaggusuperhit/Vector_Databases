"""
Weaviate Cloud Client v4

This module provides a client for connecting to Weaviate Cloud using the v4 client API.
It handles the connection to the Weaviate Cloud instance and provides methods for
common operations.

Usage:
    from weaviate_client_v4 import WeaviateCloudClient

    # Create a client
    client = WeaviateCloudClient()

    # Connect to Weaviate
    client.connect()

    # Get meta information
    meta_info = client.get_meta_info()
    print(f"Connected to Weaviate version: {meta_info['version']}")
"""

import os
import logging
import requests
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import weaviate
from weaviate.auth import AuthApiKey
from weaviate.connect import ConnectionParams

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WeaviateCloudClient:
    """
    Client for connecting to Weaviate Cloud using the v4 client API.
    """

    def __init__(self,
                 url: Optional[str] = None,
                 api_key: Optional[str] = None,
                 openai_api_key: Optional[str] = None,
                 openrouter_api_key: Optional[str] = None):
        """
        Initialize the Weaviate Cloud client.

        Args:
            url: The URL of the Weaviate Cloud instance. If None, it will be loaded from the environment.
            api_key: The API key for the Weaviate Cloud instance. If None, it will be loaded from the environment.
            openai_api_key: The OpenAI API key for generative search. If None, it will be loaded from the environment.
            openrouter_api_key: The OpenRouter API key for generative search. If None, it will be loaded from the environment.
        """
        # Load environment variables
        load_dotenv()

        # Set up the URL and API key
        self.url = url or os.getenv("WEAVIATE_URL")
        self.api_key = api_key or os.getenv("WEAVIATE_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openrouter_api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")

        # Validate required parameters
        if not self.url:
            raise ValueError("Weaviate URL is required. Set it in the environment or pass it to the constructor.")
        if not self.api_key:
            raise ValueError("Weaviate API key is required. Set it in the environment or pass it to the constructor.")

        # Initialize the client
        self.client = None
        self.connection_params = None
        self.auth_config = None
        self.headers = {}

        # Set up headers for generative search
        if self.openai_api_key:
            self.headers["X-OpenAI-Api-Key"] = self.openai_api_key
        elif self.openrouter_api_key:
            self.headers["X-OpenAI-Api-Key"] = self.openrouter_api_key

        logger.info(f"Initialized Weaviate Cloud client for URL: {self.url}")

    def connect(self) -> bool:
        """
        Connect to the Weaviate Cloud instance.

        Returns:
            True if the connection was successful.
        """
        try:
            # Create auth config
            self.auth_config = AuthApiKey(api_key=self.api_key)

            # Create connection parameters
            self.connection_params = ConnectionParams.from_url(
                url=f"https://{self.url}",
                grpc_port=50051,  # Default gRPC port
                grpc_secure=True  # Use secure gRPC
            )

            # Create the client with skip_init_checks=True to bypass gRPC connection checks
            self.client = weaviate.WeaviateClient(
                connection_params=self.connection_params,
                auth_client_secret=self.auth_config,
                additional_headers=self.headers,
                skip_init_checks=True  # Skip gRPC connection checks
            )

            # Connect to Weaviate
            self.client.connect()

            logger.info(f"Connected to Weaviate Cloud at {self.url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate Cloud: {e}", exc_info=True)
            raise

    def close(self) -> None:
        """
        Close the connection to the Weaviate Cloud instance.
        """
        if self.client:
            try:
                self.client.close()
                logger.info("Closed connection to Weaviate Cloud")
            except Exception as e:
                logger.error(f"Failed to close connection: {e}", exc_info=True)

    def get_meta_info(self) -> Dict[str, Any]:
        """
        Get meta information about the Weaviate Cloud instance.

        Returns:
            Dict containing meta information.
        """
        try:
            meta_info = self.client.get_meta()

            # Convert to dict if it's an object
            if not isinstance(meta_info, dict):
                meta_info_dict = {
                    "version": getattr(meta_info, "version", "Unknown"),
                    "hostname": getattr(meta_info, "hostname", "Unknown")
                }
                return meta_info_dict

            return meta_info
        except Exception as e:
            logger.error(f"Failed to get meta information: {e}", exc_info=True)

            # Try using REST API directly as fallback
            try:
                response = requests.get(
                    f"https://{self.url}/v1/meta",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                response.raise_for_status()
                return response.json()
            except Exception as e2:
                logger.error(f"Fallback REST API call failed: {e2}", exc_info=True)
                raise e

    def list_collections(self) -> List[str]:
        """
        List all collections in the Weaviate Cloud instance.

        Returns:
            List of collection names.
        """
        try:
            collections = self.client.collections.list_all()
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}", exc_info=True)

            # Try using REST API directly as fallback
            try:
                response = requests.get(
                    f"https://{self.url}/v1/schema",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                response.raise_for_status()
                schema = response.json()
                return [c["class"] for c in schema.get("classes", [])]
            except Exception as e2:
                logger.error(f"Fallback REST API call failed: {e2}", exc_info=True)
                raise e

    def create_collection(self, name: str, properties: List[Dict[str, Any]]) -> bool:
        """
        Create a new collection in the Weaviate Cloud instance.

        Args:
            name: The name of the collection.
            properties: List of property definitions.

        Returns:
            True if the collection was created successfully.
        """
        # Use REST API directly for collection creation
        try:
            # Ensure properties are in the correct format for REST API
            rest_properties = []
            for prop in properties:
                # Make a copy to avoid modifying the original
                rest_prop = prop.copy()
                # Ensure dataType is present and in the correct format
                if "dataType" not in rest_prop:
                    rest_prop["dataType"] = ["text"]  # Default to text
                rest_properties.append(rest_prop)

            class_obj = {
                "class": name,
                "properties": rest_properties,
                "vectorizer": "none"  # Use 'none' as vectorizer since text2vec-contextionary is not available
            }

            response = requests.post(
                f"https://{self.url}/v1/schema",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=class_obj
            )

            # Log the response for debugging
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response content: {response.text}")

            if response.status_code == 422:
                # Try with a simpler schema
                simple_class_obj = {
                    "class": name,
                    "vectorizer": "none"  # Use 'none' as vectorizer since text2vec-contextionary is not available
                }

                logger.info(f"Trying with simpler schema: {simple_class_obj}")

                response = requests.post(
                    f"https://{self.url}/v1/schema",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=simple_class_obj
                )

                logger.info(f"Simple schema response status: {response.status_code}")
                logger.info(f"Simple schema response content: {response.text}")

            response.raise_for_status()
            logger.info(f"Created collection {name} using REST API")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection {name}: {e}", exc_info=True)
            raise

    def delete_collection(self, name: str) -> bool:
        """
        Delete a collection from the Weaviate Cloud instance.

        Args:
            name: The name of the collection.

        Returns:
            True if the collection was deleted successfully.
        """
        try:
            self.client.collections.delete(name)
            logger.info(f"Deleted collection: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection {name}: {e}", exc_info=True)

            # Try using REST API directly as fallback
            try:
                response = requests.delete(
                    f"https://{self.url}/v1/schema/{name}",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                response.raise_for_status()
                logger.info(f"Deleted collection using REST API: {name}")
                return True
            except Exception as e2:
                logger.error(f"Fallback REST API call failed: {e2}", exc_info=True)
                raise e

    def insert_object(self, collection_name: str, data: Dict[str, Any]) -> str:
        """
        Insert an object into a collection.

        Args:
            collection_name: The name of the collection.
            data: The data to insert.

        Returns:
            The ID of the inserted object.
        """
        try:
            collection = self.client.collections.get(collection_name)
            result = collection.data.insert(data)
            logger.info(f"Inserted object into {collection_name} with ID: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to insert object into {collection_name}: {e}", exc_info=True)

            # Try using REST API directly as fallback
            try:
                response = requests.post(
                    f"https://{self.url}/v1/objects",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "class": collection_name,
                        "properties": data
                    }
                )
                response.raise_for_status()
                result = response.json()
                object_id = result.get("id")
                logger.info(f"Inserted object using REST API into {collection_name} with ID: {object_id}")
                return object_id
            except Exception as e2:
                logger.error(f"Fallback REST API call failed: {e2}", exc_info=True)
                raise e

    def query_objects(self, collection_name: str, properties: List[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Query objects from a collection.

        Args:
            collection_name: The name of the collection.
            properties: List of properties to return. If None, all properties are returned.
            limit: Maximum number of objects to return.

        Returns:
            List of objects.
        """
        try:
            # Try using REST API directly since gRPC is failing
            url = f"https://{self.url}/v1/graphql"

            # Build the GraphQL query
            properties_str = " ".join(properties) if properties else "_additional { id }"
            query = f"""
            {{
                Get {{
                    {collection_name}(limit: {limit}) {{
                        {properties_str}
                    }}
                }}
            }}
            """

            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"query": query}
            )
            response.raise_for_status()
            result = response.json()

            # Extract the objects from the response
            objects = result.get("data", {}).get("Get", {}).get(collection_name, [])
            logger.info(f"Retrieved {len(objects)} objects from {collection_name}")
            return objects
        except Exception as e:
            logger.error(f"Failed to query objects from {collection_name}: {e}", exc_info=True)
            raise

    def search_objects(self, collection_name: str, query: str, properties: List[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search objects in a collection using a text query.

        Args:
            collection_name: The name of the collection.
            query: The search query.
            properties: List of properties to return. If None, all properties are returned.
            limit: Maximum number of objects to return.

        Returns:
            List of objects.
        """
        try:
            # Try using REST API directly since gRPC is failing
            url = f"https://{self.url}/v1/graphql"

            # Build the GraphQL query
            properties_str = " ".join(properties) if properties else "_additional { id }"
            graphql_query = f"""
            {{
                Get {{
                    {collection_name}(
                        nearText: {{
                            concepts: ["{query}"]
                        }}
                        limit: {limit}
                    ) {{
                        {properties_str}
                    }}
                }}
            }}
            """

            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"query": graphql_query}
            )
            response.raise_for_status()
            result = response.json()

            # Extract the objects from the response
            objects = result.get("data", {}).get("Get", {}).get(collection_name, [])
            logger.info(f"Search for '{query}' returned {len(objects)} objects from {collection_name}")
            return objects
        except Exception as e:
            logger.error(f"Failed to search objects in {collection_name}: {e}", exc_info=True)
            raise