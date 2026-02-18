
import json
import chromadb
from chromadb.utils import embedding_functions

# Configuration
DB_DIR = "chroma_db"
COLLECTION_NAME = "blog_posts"
OUTPUT_FILE = "documents.json"

def main():
    print(f"Loading ChromaDB from {DB_DIR}...")
    client = chromadb.PersistentClient(path=DB_DIR)
    
    # We need to define the EF to retrieve the collection, even if we just dump data
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    
    try:
        collection = client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)
    except Exception as e:
        print(f"Error loading collection: {e}")
        return

    # Use get() to fetch all data. 
    # ChromaDB get() without ids returns everything if limit is large enough?
    # Default limit might be small. Let's set a high limit or iterate.
    # Current count is ~100 chunks. 10000 limit is safe for now.
    
    print("Fetching all documents...")
    # .get() returns dict with keys: ids, embeddings, documents, metadatas
    data = collection.get(
        include=["documents", "metadatas", "embeddings"],
        limit=10000 
    )
    
    if not data or not data['ids']:
        print("No documents found.")
        return

    export_data = []
    
    # data['ids'] is a list of IDs
    count = len(data['ids'])
    print(f"Exporting {count} chunks...")
    
    for i in range(count):
        # Convert numpy array to list for JSON serialization
        embedding = data['embeddings'][i]
        if hasattr(embedding, 'tolist'):
            embedding = embedding.tolist()
            
        item = {
            "id": data['ids'][i],
            "page_content": data['documents'][i],
            "metadata": data['metadatas'][i],
            "embedding": embedding
        }
        export_data.append(item)
        
    print(f"Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False)
        
    # --- NEW: Export Full Posts for Reader View ---
    print("Exporting full posts to posts.json...")
    import os
    import glob
    posts_dir = "posts"
    all_posts = []
    
    if os.path.exists(posts_dir):
        files = glob.glob(os.path.join(posts_dir, "*.md"))
        for file_path in files:
            filename = os.path.basename(file_path)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Simple metadata extraction
            title = ""
            date = ""
            category = "Uncategorized"
            url = ""
            
            lines = content.split('\n')
            for line in lines[:20]:
                if line.startswith("# "):
                    title = line[2:].strip()
                elif line.startswith("**Date:**"):
                    date = line.replace("**Date:**", "").strip()
                elif line.startswith("**Category:**"):
                    category = line.replace("**Category:**", "").strip()
                elif line.startswith("**Original URL:**"):
                    url = line.replace("**Original URL:**", "").strip()
            
            all_posts.append({
                "filename": filename,
                "title": title,
                "date": date,
                "category": category,
                "url": url,
                "content": content # Full content
            })
            
    # Sort by date (descending)
    try:
        all_posts.sort(key=lambda x: x['date'], reverse=True)
    except:
        pass # Handle date parsing issues gracefully
            
    with open("posts.json", "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False)
        
    print(f"Done! Exported {count} chunks to documents.json and {len(all_posts)} posts to posts.json.")

if __name__ == "__main__":
    main()
