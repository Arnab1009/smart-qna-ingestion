from dotenv import load_dotenv
from sync_utils import SyncUtil
from ingest_pipeline import IngestUtils
from datetime import datetime, timezone
import os
from logger_config import init_logger

logger, log_path = init_logger()

def main():
    logger.info("Ingestion started.")

    # Load environment variables from .env file
    load_dotenv(override=True)
    bucket_name = os.getenv("GCS_BUCKET")
    last_sync_blob_path = os.getenv("LAST_SYNC_BLOB_PATH")
    
    # Create SyncUtil and IngestUtils object
    sync_util = SyncUtil(bucket_name, last_sync_blob_path)
    ingest_util = IngestUtils(bucket_name)
    
    # Read last sync time
    logger.info("Read last sync time.")
    last_sync_time = sync_util.get_last_sync_time()

    # If last sync time is 0, it means the file is missing
    if last_sync_time == 0:
        logger.info("last_sync file is missing. Ingestion cannot proceed.")
    else:
        # Look for new files uploaded after last sync time
        logger.info(f"Looking for new files since {last_sync_time.isoformat()}...")
        new_files = sync_util.list_new_files(last_sync_time)


        if not new_files:
            # If no files found exit
            logger.info("Ingestion complete. No new files to process.")
        else:
            # Process new files
            logger.info(f"Found {len(new_files)} new files. Processing...")
            
            split_docs = ingest_util.download_and_chunk_files(new_files)
            logger.info(f"{len(split_docs)} chunks were created!")

            # Upload chunks to Pinecone
            if ingest_util.embed_and_upload_to_pinecone(split_docs):
                logger.info(f"Uploaded {len(split_docs)} documents to Pinecone index")
            else:
                logger.info("Upload to Pinecone failed.")

            new_sync_time = datetime.now(timezone.utc)
            sync_util.update_last_sync_time(new_sync_time)

            logger.info("Ingestion complete. Timestamp updated.")
        
        # Upload log file to GCS
        sync_util.upload_log_to_gcs(log_path)

if __name__ == "__main__":
    main()
