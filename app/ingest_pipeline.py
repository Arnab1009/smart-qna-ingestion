import fitz  # PyMuPDF
from typing import List
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pinecone import Pinecone
from google.cloud import storage
import logging
import os

class IngestUtils:
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.embedding_model_name = "text-embedding-005"
        self.file_path = "raw_data/"
        self.logger = logging.getLogger()

        # Initialize pinecone
        self.pc_data = {
            "pc_api_key": os.getenv("PINECONE_API_KEY"),
            "pc_env": os.getenv("PINECONE_ENVIRONMENT"),
            "pc_index_name": os.getenv("PINECONE_INDEX_NAME")
        }
        self.pinecone = Pinecone(api_key=self.pc_data["pc_api_key"], environment=self.pc_data["pc_env"])
        self.index = self.pinecone.Index(self.pc_data["pc_index_name"])

        # Initialize vector store, llm and embeddings
        self.embedding = VertexAIEmbeddings(model_name=self.embedding_model_name)
        self.vector_store = PineconeVectorStore(index=self.index, embedding=self.embedding)
    
    def _get_data_from_pdf(self, pdf_bytes):
        text = ""
        with fitz.open(stream=pdf_bytes, filename="pdf") as doc:
            for page in doc:
                text += page.get_text()
        return text

    def _download_and_extract(self, include_files):
        blobs = self.bucket.list_blobs(prefix=self.file_path)
        contents = {}

        for blob in blobs:
            if blob.name.endswith("/"):
                continue

            # Skip files if they are in the list
            if include_files and blob.name not in include_files:
                continue

            content = ""
            if blob.name.lower().endswith(".pdf"):
                pdf_bytes = blob.download_as_bytes()
                content = self._get_data_from_pdf(pdf_bytes)
            else:
                content = blob.download_as_text()
            contents[blob.name] = content

        return contents
    
    def _chunk_documents_batch(self, documents, chunk_size=1000, chunk_overlap=200):
        # Iterate through douments and create lanchain document with content and filename
        lc_documents = [Document(page_content=doc_content, metadata={"source": doc_name}) 
                        for doc_name, doc_content in documents.items()
        ]

        # Initialise RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, 
            chunk_overlap=chunk_overlap, 
            separators=["\n\n", "\n", ".", " "], 
            length_function=len
        )

        # Split langchain documents into chunks
        split_docs = text_splitter.split_documents(lc_documents)

        return split_docs
    
    def download_and_chunk_files(self, include_files):
        # Download and extract data from files
        contents = self._download_and_extract(include_files)

        # Return chunked documents
        return self._chunk_documents_batch(contents)
    
    def embed_and_upload_to_pinecone(self, documents, batch_size=100):
        if not all([self.pc_data["pc_api_key"], self.pc_data["pc_env"], self.pc_data["pc_index_name"]]):
            return False

        # Batch upload vectors to Pinecone
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            self.vector_store.add_documents(batch)
            self.logger.info(f"Uploaded batch {i//batch_size + 1} of {len(documents)//batch_size + 1}")

        return True
        


    
