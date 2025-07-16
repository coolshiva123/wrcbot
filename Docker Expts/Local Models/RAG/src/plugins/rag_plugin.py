import os
from errbot import BotPlugin, botcmd
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Document
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
from llama_index.readers.confluence import ConfluenceReader
import requests
from typing import List, Optional

class RAGPlugin(BotPlugin):
    """
    RAG (Retrieval Augmented Generation) plugin for document Q&A
    """

    def activate(self):
        """
        Initialize the RAG system on plugin activation
        """
        super().activate()
        
        # Create data directories if they don't exist
        self.docs_dir = os.path.join(self.plugin_dir, 'data', 'documents')
        self.db_dir = os.path.join(self.plugin_dir, 'data', 'chroma_db')
        os.makedirs(self.docs_dir, exist_ok=True)
        os.makedirs(self.db_dir, exist_ok=True)

        # Initialize ChromaDB and vector store
        self.chroma_client = chromadb.PersistentClient(path=self.db_dir)
        self.vector_store = ChromaVectorStore(
            client=self.chroma_client,
            collection_name="errbot_docs"
        )
        
        # Initialize the index if documents exist
        self._load_or_create_index()

    def _load_or_create_index(self):
        """
        Load existing index or create new one if documents exist
        """
        try:
            documents = SimpleDirectoryReader(self.docs_dir).load_data()
            if documents:
                self.index = VectorStoreIndex.from_documents(
                    documents,
                    vector_store=self.vector_store
                )
                self.log.info(f"Loaded {len(documents)} documents into the index")
            else:
                self.log.info("No documents found to index")
                self.index = None
        except Exception as e:
            self.log.error(f"Error loading documents: {str(e)}")
            self.index = None

    @botcmd
    def rag_load_docs(self, msg, args):
        """
        Reload and index all documents from the data directory
        """
        self._load_or_create_index()
        if self.index:
            return "Documents reloaded and indexed successfully!"
        return "No documents found to index"

    @botcmd
    def rag_query(self, msg, args):
        """
        Query the RAG system with a question
        """
        if not args:
            return "Please provide a question to answer"
        
        if not self.index:
            return "No documents have been indexed yet. Please add documents and run !rag_load_docs first"

        try:
            query_engine = self.index.as_query_engine()
            response = query_engine.query(args)
            return str(response)
        except Exception as e:
            self.log.error(f"Error querying index: {str(e)}")
            return f"Error processing query: {str(e)}"

    @botcmd
    def rag_add_confluence(self, msg, args):
        """
        Add documents from Confluence. Format: space_key page_id [page_id2 ...]
        """
        args = args.split()
        if len(args) < 2:
            return "Please provide space_key and at least one page_id"

        space_key = args[0]
        page_ids = args[1:]

        try:
            # Confluence credentials should be configured in bot config
            confluence_url = self.bot_config.CONFLUENCE_URL
            confluence_username = self.bot_config.CONFLUENCE_USERNAME
            confluence_password = self.bot_config.CONFLUENCE_PASSWORD

            reader = ConfluenceReader(
                base_url=confluence_url,
                username=confluence_username,
                api_key=confluence_password
            )
            
            documents = reader.load_data(
                space_key=space_key,
                page_ids=page_ids,
                include_attachments=True
            )

            # Add documents to index
            if not self.index:
                self.index = VectorStoreIndex.from_documents(
                    documents,
                    vector_store=self.vector_store
                )
            else:
                self.index.insert_nodes(documents)

            return f"Successfully added {len(documents)} Confluence pages to the index"
        except Exception as e:
            self.log.error(f"Error adding Confluence pages: {str(e)}")
            return f"Error adding Confluence pages: {str(e)}"
