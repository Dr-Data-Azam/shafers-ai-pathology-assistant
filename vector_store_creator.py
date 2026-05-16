import os
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv

from config import get_config

load_dotenv()

# Lazy-initialized embedding model singleton
_embedding_model: Optional[HuggingFaceEmbeddings] = None


def get_embedding_model() -> HuggingFaceEmbeddings:
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model
    cfg = get_config()
    _embedding_model = HuggingFaceEmbeddings(
        model_name=cfg.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    return _embedding_model


def load_pdf_files(data_dir: str) -> list:
    loader = DirectoryLoader(data_dir, glob="*.pdf", loader_cls=PyPDFLoader)
    documents = loader.load()
    for idx, doc in enumerate(documents):
        doc.metadata["page_number"] = idx + 1
        doc.metadata["source"] = "Shafer"
    return documents


def create_chunks(extracted_data: list) -> list:
    cfg = get_config()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
    )
    return splitter.split_documents(extracted_data)


def build_vector_store() -> None:
    cfg = get_config()
    db_path = cfg.db_path
    data_path = cfg.data_path

    if os.path.exists(db_path):
        print("Vector DB already exists. Skipping creation.")
        return

    print("Loading PDF files...")
    documents = load_pdf_files(data_path)
    print(f"Loaded {len(documents)} documents")

    print("Creating chunks...")
    chunks = create_chunks(documents)
    print(f"Created {len(chunks)} chunks")

    print("Building vector store...")
    embedding = get_embedding_model()
    batch_size = 1000
    if len(chunks) > batch_size:
        db = FAISS.from_documents(documents=chunks[:batch_size], embedding=embedding)
        for i in range(batch_size, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            temp_db = FAISS.from_documents(documents=batch, embedding=embedding)
            db.merge_from(temp_db)
            print(f"Processed {min(i + batch_size, len(chunks))}/{len(chunks)} chunks")
    else:
        db = FAISS.from_documents(documents=chunks, embedding=embedding)

    db.save_local(db_path)
    print("Vector DB created and saved locally.")


if __name__ == "__main__":
    build_vector_store()
