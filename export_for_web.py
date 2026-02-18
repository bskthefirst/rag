
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
        
    print("Done!")

if __name__ == "__main__":
    main()
