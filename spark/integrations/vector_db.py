"""
Vector DB Integration (Pinecone)
Stub for RAG and memory operations.
"""


import os
from dotenv import load_dotenv

import pinecone
from langchain_community.vectorstores import Pinecone as LangchainPinecone
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from pypdf import PdfReader

load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENVIRONMENT")

class PineconeMemory:
    def __init__(self, index_name="spark-memory"):
        pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
        if index_name not in pinecone.list_indexes():
            pinecone.create_index(index_name, dimension=1536)
        self.index = pinecone.Index(index_name)
        self.vectorstore = LangchainPinecone(self.index, OpenAIEmbeddings())

    def ingest_pdf(self, pdf_path):
        reader = PdfReader(pdf_path)
        text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        docs = splitter.create_documents([text])
        self.vectorstore.add_documents(docs)
        print(f"[VECTOR_DB] Ingested {len(docs)} chunks from {pdf_path}")

    def retrieve(self, query, top_k=3):
        results = self.vectorstore.similarity_search(query, k=top_k)
        return [doc.page_content for doc in results]
