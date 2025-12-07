import sqlite3
import re
import os
from langchain_community.vectorstores import FAISS
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

def redact_pii(text):
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED_EMAIL]', text)
    return text

@tool
def get_ranking(area_name: str, ranking_type: str):
    """Retrieves top 5 neighborhoods based on deprivation ranking."""
    try:
        area_clean = area_name.replace("Glasgow", "Glasgow City").replace("Edinburgh", "City of Edinburgh")
        if "City City" in area_clean: area_clean = area_clean.replace("City City", "City")
        
        r_type = ranking_type.lower().strip()
        if "least" in r_type:
            sort_order = "DESC"
            desc = "Least Deprived (Wealthiest)"
            agg = "MAX"
        else:
            sort_order = "ASC"
            desc = "Most Deprived (Poorest)"
            agg = "MIN"
        
        if area_clean.lower() in ["scotland", "overall", "country", "national", "uk"]:
            query = f"SELECT intermediate_zone, council_area, {agg}(rank) as ranking FROM simd_stats GROUP BY intermediate_zone ORDER BY ranking {sort_order} LIMIT 5"
            label = "Scotland (Overall)"
        else:
            query = f"SELECT intermediate_zone, council_area, {agg}(rank) as ranking FROM simd_stats WHERE council_area = '{area_clean}' GROUP BY intermediate_zone ORDER BY ranking {sort_order} LIMIT 5"
            label = area_clean
            
        conn = sqlite3.connect("gov_stats.db") 
        cursor = conn.cursor()
        cursor.execute(query)
        result = [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
        conn.close()
        
        if not result: return f"No data found for '{area_clean}'. I only have data for Scotland."
        return f"Top 5 {desc} in {label}: {str(result)}"
    except Exception as e: return f"Error: {str(e)}"

@tool
def lookup_neighborhood(name: str):
    """Finds rank of specific neighborhood using fuzzy matching."""
    try:
        query = f"SELECT intermediate_zone, council_area, AVG(rank) as avg_rank FROM simd_stats WHERE intermediate_zone LIKE '%{name}%' OR neighborhood LIKE '%{name}%' GROUP BY intermediate_zone LIMIT 3"
        conn = sqlite3.connect("gov_stats.db") 
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows: return f"No data found for '{name}'."
        results_formatted = []
        for r in rows:
            zone, council, rank = r
            rank = int(rank)
            if rank < 1000: status = "High Deprivation (Bottom 15%)"
            elif rank > 5000: status = "Low Deprivation (Wealthy)"
            else: status = "Mid-range"
            results_formatted.append(f"{zone} ({council}): Rank {rank} -> {status}")
        return "\n".join(results_formatted)
    except Exception as e: return f"Error: {str(e)}"

@tool
def query_policy_documents(query: str):
    """Useful for policy questions."""
    try:
        embedding_model = OllamaEmbeddings(model="nomic-embed-text")
        if not os.path.exists("./my_vector_db"): return "Error: Policy DB not found."
        vector_db = FAISS.load_local("./my_vector_db", embedding_model, allow_dangerous_deserialization=True)
        retriever = vector_db.as_retriever(search_kwargs={"k": 3})
        docs = retriever.invoke(query)
        return "\n\n".join([d.page_content for d in docs])
    except Exception as e: return f"Error: {str(e)}"

def get_agent_executor():
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    llm = ChatOllama(model="llama3.2", temperature=0, base_url=ollama_url)
    tools = [get_ranking, lookup_neighborhood, query_policy_documents]
    
    system_prompt = (
        "You are an expert Government data assistant. "
        "1. Answer ONLY questions about Scottish Deprivation or UK Industrial Strategy.\n"
        "2. REFUSE questions about foreign countries or unrelated topics.\n"
        "3. Use 'get_ranking' for lists, 'lookup_neighborhood' for places, 'query_policy_documents' for text."
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}")
    ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)
