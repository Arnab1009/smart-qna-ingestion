from google.cloud import storage
from datetime import datetime
import json, os
import logging


class SyncUtil:
    def __init__(self, bucket_name: str, blob_path: str):
        self.bucket_name = bucket_name
        self.blob_path = blob_path
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.blob = self.bucket.blob(blob_path)
        self.gcs_log_path = "sync_data/logs"
        self.logger = logging.getLogger()
    
    # Function to get last sync time
    def get_last_sync_time(self):
        if not self.blob.exists():
            return 0
        else:
            content = self.blob.download_as_text()
            data = json.loads(content)
            return datetime.fromisoformat(data["last_sync"])

    # Function to list newly added files after previous run
    def list_new_files(self, since_time: datetime) -> list:
        blobs = self.bucket.list_blobs(prefix="raw_data/")
        new_files = [
            blob.name for blob in blobs
            if blob.updated > since_time
        ]
        return new_files

    # Function to sync new timestamp
    def update_last_sync_time(self, timestamp: datetime):
        data = {
            "last_sync": timestamp.isoformat()
        }
        self.blob.upload_from_string(json.dumps(data), content_type="application/json")

    # Function to sync logfile to GCS
    def upload_log_to_gcs(self, local_log_path):
        filename = os.path.basename(local_log_path)
        blob = self.bucket.blob(f"{self.gcs_log_path}/{filename}")
        blob.upload_from_filename(local_log_path)
        self.logger.info(f"Log file uploaded to: gs://{self.bucket_name}/{self.gcs_log_path}/{filename}")
