import os
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = "data/"
DB_PATH = "vectorDB/my_FAISS_db"

# Step 1: Load PDF with optimized embedding model
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'},  # Explicitly set device
    encode_kwargs={'normalize_embeddings': True}  # Normalize for better similarity
)

def load_pdf_files(data_dir):
    loader = DirectoryLoader(data_dir, glob="*.pdf", loader_cls=PyPDFLoader)
    documents = loader.load()
    for idx, doc in enumerate(documents):
        # Fixed page number calculation - no offset needed since we'll correct it during retrieval
        doc.metadata["page_number"] = idx + 1  # Start from page 1
        doc.metadata["source"] = "Shafer"
    return documents

# Step 2: Create chunks with optimized parameters
def create_chunks(extracted_data):
    # Reduced chunk size and overlap for better performance
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,  # Reduced from 750
        chunk_overlap=50,  # Reduced from 75
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    return splitter.split_documents(extracted_data)

# Step 3 + 4: Create Embeddings and Save Vector Store
def build_vector_store():
    if os.path.exists(DB_PATH):
        print("Vector DB already exists. Skipping creation.")
        return

    print("Loading PDF files...")
    documents = load_pdf_files(DATA_PATH)
    print(f"Loaded {len(documents)} documents")
    
    print("Creating chunks...")
    chunks = create_chunks(documents)
    print(f"Created {len(chunks)} chunks")
    
    print("Building vector store...")
    # Process in batches for better memory management
    batch_size = 1000
    if len(chunks) > batch_size:
        # Create initial database with first batch
        db = FAISS.from_documents(documents=chunks[:batch_size], embedding=embedding_model)
        
        # Add remaining chunks in batches
        for i in range(batch_size, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            temp_db = FAISS.from_documents(documents=batch, embedding=embedding_model)
            db.merge_from(temp_db)
            print(f"Processed {min(i+batch_size, len(chunks))}/{len(chunks)} chunks")
    else:
        db = FAISS.from_documents(documents=chunks, embedding=embedding_model)
    
    db.save_local(DB_PATH)
    print("Vector DB created and saved locally.")

if __name__ == "__main__":
    build_vector_store()