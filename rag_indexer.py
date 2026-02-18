
import os
import glob
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

# Configuration
POSTS_DIR = "posts"
DB_DIR = "chroma_db"
COLLECTION_NAME = "blog_posts"

def load_markdown_files():
    files = glob.glob(os.path.join(POSTS_DIR, "*.md"))
    documents = []
    metadatas = []
    ids = []
    
    for file_path in files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract basic metadata from header (simple parsing)
        lines = content.split('\n')
        title = ""
        date = ""
        category = "Uncategorized"
        url = ""
        body_start_idx = 0
        
        for i, line in enumerate(lines[:20]): # Check first 20 lines for metadata
            if line.startswith("# "):
                title = line[2:].strip()
            elif line.startswith("**Date:**"):
                date = line.replace("**Date:**", "").strip()
            elif line.startswith("**Category:**"):
                category = line.replace("**Category:**", "").strip()
            elif line.startswith("**Original URL:**"):
                url = line.replace("**Original URL:**", "").strip()
            elif line.startswith("---"):
                body_start_idx = i + 1
                
        body = "\n".join(lines[body_start_idx:])
        
        # Split text logic
        # 1. Split by headers first
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        md_header_splits = markdown_splitter.split_text(body)
        
        # 2. Recursive split for large chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(md_header_splits)
        
        filename = os.path.basename(file_path)
        
        for i, split in enumerate(splits):
            chunk_id = f"{filename}_{i}"
            
            # Combine metadata
            meta = {
                "source": filename,
                "title": title,
                "date": date,
                "category": category,
                "url": url,
                "header": split.metadata.get("Header 1") or split.metadata.get("Header 2") or split.metadata.get("Header 3") or ""
            }
            
            documents.append(split.page_content)
            metadatas.append(meta)
            ids.append(chunk_id)
            
    return documents, metadatas, ids

def main():
    print("Loading documents...")
    docs, metas, ids = load_markdown_files()
    if not docs:
        print("No documents found to index.")
        return

    print(f"Found {len(ids)} chunks from {len(set(m['source'] for m in metas))} files.")

    print("Initializing ChromaDB...")
    client = chromadb.PersistentClient(path=DB_DIR)
    
    # Use default embedding function (all-MiniLM-L6-v2)
    # Explicitly defining it ensures consistency
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME, 
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )
    
    # Upsert (overwrite if exists)
    print("Indexing chunks...")
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        end = min(i + batch_size, len(ids))
        print(f"  Processing batch {i} to {end}...")
        collection.upsert(
            documents=docs[i:end],
            metadatas=metas[i:end],
            ids=ids[i:end]
        )
        
    print(f"Indexing complete. Saved to '{DB_DIR}'.")

if __name__ == "__main__":
    main()
