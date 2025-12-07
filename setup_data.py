import sqlite3
import pandas as pd
import os
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain.schema import Document

def create_dummy_db():
    print("creating sqlite db...")
    data = {
        'rank': [1, 5, 50, 100, 500, 5000, 6000, 6500],
        'neighborhood': ['Govan', 'Possil Park', 'Easterhouse', 'Parkhead', 'City Centre', 'Hyndland', 'Bearsden', 'Newton Mearns'],
        'intermediate_zone': ['Govan', 'Possil Park', 'Easterhouse', 'Parkhead', 'City Centre', 'Hyndland', 'Bearsden', 'Newton Mearns'],
        'council_area': ['Glasgow City', 'Glasgow City', 'Glasgow City', 'Glasgow City', 'Glasgow City', 'Glasgow City', 'East Dunbartonshire', 'East Renfrewshire']
    }
    df = pd.DataFrame(data)
    conn = sqlite3.connect("gov_stats.db")
    df.to_sql("simd_stats", conn, if_exists="replace", index=False)
    conn.close()
    print("✅ gov_stats.db created.")

def create_vector_db():
    print("creating vector db (requires ollama)...")
    try:
        text = "The UK Industrial Strategy focuses on clean energy, advanced manufacturing, and digital technologies. It aims to boost growth across all nations including Scotland."
        docs = [Document(page_content=text, metadata={"source": "policy.pdf"})]
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        vector_db = FAISS.from_documents(docs, embeddings)
        vector_db.save_local("my_vector_db")
        print("✅ my_vector_db created.")
    except Exception as e:
        print(f"⚠️ Could not create Vector DB: {e}. Make sure Ollama is running.")

if __name__ == "__main__":
    create_dummy_db()
    create_vector_db()
