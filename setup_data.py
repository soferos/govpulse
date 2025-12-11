import sqlite3
import pandas as pd
import os
import time
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# --- CONFIGURATION ---
RANKS_FILE = "simd2020.csv"
LOOKUP_FILE = "simd2020lookup.csv"
PDF_FILE = "industrial_strategy_policy_paper.pdf"
DB_NAME = "gov_stats.db"
VECTOR_DB_NAME = "my_vector_db"

def create_sql_db():
    print(f"🔄 Processing SQL Database...")
    if not os.path.exists(RANKS_FILE) or not os.path.exists(LOOKUP_FILE):
        print("❌ CSV files not found. Skipping SQL creation.")
        return

    try:
        # Load and Merge
        df_ranks = pd.read_csv(RANKS_FILE)
        df_lookup = pd.read_csv(LOOKUP_FILE)
        
        # Merge on DataZone code
        merged_df = pd.merge(df_ranks, df_lookup, on='DataZone', how='inner')
        
        # Select and Rename columns for the Tool
        final_df = merged_df[[
            'SIMD2020V2Rank',    # Rank
            'DataZoneName',      # Neighborhood
            'IntZoneName',       # Intermediate Zone
            'CAName'             # Council Area
        ]].copy()
        
        final_df.rename(columns={
            'SIMD2020V2Rank': 'rank',
            'DataZoneName': 'neighborhood',
            'IntZoneName': 'intermediate_zone',
            'CAName': 'council_area'
        }, inplace=True)

        # Save
        conn = sqlite3.connect(DB_NAME)
        final_df.to_sql("simd_stats", conn, if_exists="replace", index=False)
        conn.close()
        print(f"✅ SQL Database created with {len(final_df)} records.")
        
    except Exception as e:
        print(f"❌ SQL Error: {e}")

def create_vector_db():
    print(f"🔄 Processing Vector Database from '{PDF_FILE}'...")
    
    if not os.path.exists(PDF_FILE):
        print(f"❌ PDF file '{PDF_FILE}' not found.")
        return

    try:
        # 1. Load PDF
        loader = PyPDFLoader(PDF_FILE)
        pages = loader.load()
        print(f"   📖 Loaded {len(pages)} pages.")

        # 2. Split into Chunks (Critical for RAG & Stability)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(pages)
        print(f"   ✂️  Split into {len(splits)} text chunks.")

        # 3. Create Embeddings in Batches
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        
        # Initialize Vector DB with the first batch to create the structure
        batch_size = 32  # Small batch size to prevent timeout
        print(f"   🚀 Starting embedding (Batch size: {batch_size})...")
        
        # Process first batch to init DB
        vector_db = FAISS.from_documents(splits[:batch_size], embeddings)
        print(f"      Batch 1/{len(splits)//batch_size + 1} done.")

        # Process remaining batches
        for i in range(batch_size, len(splits), batch_size):
            batch = splits[i : i + batch_size]
            vector_db.add_documents(batch)
            print(f"      Batch {i//batch_size + 1} done...")
            time.sleep(0.5) # Small pause to let Ollama breathe

        # 4. Save
        vector_db.save_local(VECTOR_DB_NAME)
        print(f"✅ Vector Database saved to '{VECTOR_DB_NAME}'")

    except Exception as e:
        print(f"❌ Vector DB Error: {e}")
        print("   👉 Tip: Ensure Ollama is running (`ollama serve` or app running)")

if __name__ == "__main__":
    create_sql_db()
    create_vector_db()