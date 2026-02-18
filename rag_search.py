
import os
import chromadb
from chromadb.utils import embedding_functions
import argparse

# Configuration
DB_DIR = "chroma_db"
COLLECTION_NAME = "blog_posts"

def search(query, k=5, category=None):
    client = chromadb.PersistentClient(path=DB_DIR)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    collection = client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
    
    where_filter = {}
    if category:
        where_filter["category"] = category
        
    results = collection.query(
        query_texts=[query],
        n_results=k,
        where=where_filter if where_filter else None
    )
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Search the Naver Blog Archive")
    parser.add_argument("query", help="The search query")
    parser.add_argument("--k", type=int, default=3, help="Number of results to return")
    parser.add_argument("--category", help="Filter by category")
    
    args = parser.parse_args()
    
    print(f"Searching for: '{args.query}' (Category: {args.category or 'All'})")
    try:
        results = search(args.query, args.k, args.category)
        
        if not results['documents'][0]:
            print("No results found.")
            return

        print(f"\nFound {len(results['documents'][0])} relevant results:\n")
        
        for i, doc in enumerate(results['documents'][0]):
            meta = results['metadatas'][0][i]
            dist = results['distances'][0][i]
            
            print(f"--- Result {i+1} (Score: {dist:.4f}) ---")
            print(f"File: {meta.get('source')} | Header: {meta.get('header')}")
            print(f"Category: {meta.get('category')} | Date: {meta.get('date')}")
            print(f"URL: {meta.get('url')}")
            print(f"Content: {doc[:300]}...") # Preview content
            print("\n")
            
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have run 'python3 rag_indexer.py' first.")

if __name__ == "__main__":
    main()
