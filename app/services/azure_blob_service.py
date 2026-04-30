from azure.storage.blob import BlobServiceClient, ContentSettings
from app.core.config import settings
from uuid import uuid4
from os.path import splitext
from typing import BinaryIO, Optional

class AzureBlobService:
    def __init__(self):
        self.connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        self.container_name = settings.AZURE_STORAGE_CONTAINER_NAME
        
        if self.connection_string and self.container_name:
            self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            self.container_client = self.blob_service_client.get_container_client(self.container_name)
            try:
                if not self.container_client.exists():
                    self.container_client.create_container()
            except Exception as e:
                print(f"Error checking/creating container: {e}")
        else:
            self.blob_service_client = None
            self.container_client = None

    def upload_file(self, file_stream: BinaryIO, filename: str, content_type: str) -> Optional[str]:
        if not self.container_client:
            raise Exception("Azure Blob Storage is not configured.")

        file_ext = splitext(filename)[1]
        blob_name = f"{uuid4()}{file_ext}"

        blob_client = self.container_client.get_blob_client(blob_name)
        content_settings = ContentSettings(content_type=content_type)

        blob_client.upload_blob(file_stream, content_settings=content_settings, overwrite=True)
        return blob_name

    def download_file(self, blob_name: str) -> BinaryIO:
        if not self.container_client:
            raise Exception("Azure Blob Storage is not configured.")

        blob_client = self.container_client.get_blob_client(blob_name)
        return blob_client.download_blob().chunks()

    def get_blob_properties(self, blob_name: str):
        if not self.container_client:
            raise Exception("Azure Blob Storage is not configured.")
        blob_client = self.container_client.get_blob_client(blob_name)
        return blob_client.get_blob_properties()

    def delete_file(self, blob_name: str) -> bool:
        if not self.container_client:
            raise Exception("Azure Blob Storage is not configured.")
        
        blob_client = self.container_client.get_blob_client(blob_name)
        try:
            if blob_client.exists():
                blob_client.delete_blob()
            return True
        except Exception:
            return False

azure_blob_service = AzureBlobService()
