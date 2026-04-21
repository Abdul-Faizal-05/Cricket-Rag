import os
import sqlite3
import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

# --- Validate required environment variables ---
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY not found in environment variables")

tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# --- Module-level FAISS cache ---
_vectorstore_cache: FAISS | None = None

# -----------------------------------------------------------------------
# SCHEMA REFERENCE — injected into every SQL prompt so the LLM never
# has to guess column names.
# -----------------------------------------------------------------------
SCHEMA_DESCRIPTION = """
Table name: ipl_data

Key columns (use ONLY these exact names in SQL):
  match_id        - unique match identifier
  date            - match date (e.g. '2024-03-22')
  season          - IPL season year as integer: 2024 or 2025  ← use this for year filtering
  year            - same as season
  batter          - batter's name (e.g. 'V Kohli')
  runs_batter     - runs scored by the batter on that delivery
  balls_faced     - balls faced by batter on that delivery
  bowler          - bowler's name
  runs_bowler     - runs conceded by the bowler on that delivery
  wicket_kind     - type of wicket (e.g. 'caught', 'bowled'); empty string if no wicket
  player_out      - name of dismissed player; empty if no wicket
  batting_team    - team currently batting
  bowling_team    - team currently bowling
  match_won_by    - name of the winning team for that match
  player_of_match - player of the match
  venue, city     - location
  innings         - 1 or 2
  over, ball      - over number and ball number within over
  runs_total      - total runs on that delivery (batter + extras)
  runs_extras     - extra runs (wides, no-balls, etc.)

Important notes for correct SQL:
- Each delivery is ONE row. To get total runs for a batter, use SUM(runs_batter).
- To get wickets taken by a bowler, use COUNT(*) WHERE wicket_kind != '' AND wicket_kind IS NOT NULL.
- To get match-level stats (e.g. wins per team), use DISTINCT match_id with match_won_by.
- Filter by season: WHERE season = 2024  or  WHERE season = 2025

Example queries:
  -- Top run scorer in 2024:
  SELECT batter, SUM(runs_batter) AS total_runs
  FROM ipl_data WHERE season = 2024
  GROUP BY batter ORDER BY total_runs DESC LIMIT 5;

  -- Win count per team in 2025:
  SELECT match_won_by AS team, COUNT(DISTINCT match_id) AS wins
  FROM ipl_data WHERE season = 2025
  GROUP BY match_won_by ORDER BY wins DESC;

  -- Total matches played per team in 2025 (home or away):
  SELECT team, COUNT(DISTINCT match_id) AS matches_played FROM (
    SELECT batting_team AS team, match_id FROM ipl_data WHERE season = 2025
    UNION
    SELECT bowling_team AS team, match_id FROM ipl_data WHERE season = 2025
  ) GROUP BY team;
"""


def _get_vectorstore() -> FAISS:
    global _vectorstore_cache
    if _vectorstore_cache is not None:
        return _vectorstore_cache

    text_files = ["ipl_2024_summary.txt", "ipl_2025_summary.txt"]
    raw_texts = []
    for tf in text_files:
        if not os.path.exists(tf):
            print(f"Warning: {tf} not found, skipping.")
            continue
        with open(tf, "r", encoding="utf-8") as f:
            raw_texts.append(f.read())

    if not raw_texts:
        raise FileNotFoundError("No IPL summary text files found.")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.create_documents(raw_texts)
    _vectorstore_cache = FAISS.from_documents(chunks, embeddings)
    return _vectorstore_cache


async def search_docs(query: str) -> str:
    """Semantic search over unstructured IPL summary documents."""
    try:
        vectorstore = _get_vectorstore()
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        docs = retriever.invoke(query)
        results = [
            {"text_chunk": doc.page_content, "source": doc.metadata.get("source", "unknown")}
            for doc in docs
        ]
        return str(results) if results else "No relevant documents found."
    except FileNotFoundError as e:
        return f"Document search error: {e}"
    except Exception as e:
        return f"Unexpected error during document search: {e}"


async def query_data(query: str) -> str:
    """
    Query the structured IPL data table using SQL.
    The input MUST be a valid SQL SELECT query using the schema above.
    """
    db_path = "ipl_data.db"
    csv_path = "ipl_2024-2025.csv"

    if not os.path.exists(db_path):
        if not os.path.exists(csv_path):
            return f"Error: CSV file '{csv_path}' not found; cannot create database."
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_csv(csv_path, low_memory=False)
            df.to_sql("ipl_data", conn, if_exists="replace", index=False)
            conn.close()
        except Exception as e:
            return f"Error creating database from CSV: {e}"

    stripped = query.strip().upper()
    if not stripped.startswith("SELECT"):
        return "Error: Only SELECT queries are permitted."

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return str({"columns": columns, "data": rows})
    except sqlite3.Error as e:
        # Return the error AND the schema so the LLM can self-correct
        return f"Database error: {e}\n\nCorrect schema for reference:\n{SCHEMA_DESCRIPTION}"
    finally:
        conn.close()


async def web_search(query: str) -> str:
    """Search the live web for recent IPL information."""
    try:
        response = tavily_client.search(query=query, search_depth="basic", max_results=3)
        results = response.get("results", [])
        simplified = [
            {"title": r.get("title"), "url": r.get("url"), "content": r.get("content")}
            for r in results
        ]
        return str(simplified) if simplified else "No web results found."
    except Exception as e:
        return f"Web search error: {e}"