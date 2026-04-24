# 🏏 IPL Agent API

*An agentic RAG system for intelligent IPL cricket Q&A*

`FastAPI` · `Groq (LLaMA 3.3)` · `FAISS` · `SQLite` · `Tavily`

---

## What Is This?

IPL Agent API is a question-answering system built specifically for IPL cricket fans and analysts. You ask it a question in plain English — like "Who was the top scorer in IPL 2024?" or "What was KKR's win percentage last season?" — and it figures out the best way to answer it by combining multiple data sources and reasoning steps automatically.

The agent doesn't just do a single lookup. It thinks through what kind of question you've asked, picks the right tool (or tools), gathers the data, and then synthesizes a clean, human-readable answer. Think of it as having a cricket analyst on call who knows how to query databases, read documents, and browse the web — all at once.

---

## Architecture & How It All Fits Together

The system follows a multi-step agentic loop — here's the flow from the moment you ask a question:

### Step 1 — You Ask a Question

A client (`client.py`) sends your question to a REST API endpoint (`POST /agent`) running on `localhost:8000`. The question can be anything IPL-related — stats, records, recent news, you name it.

### Step 2 — The Router Decides What Tool to Use

`main.py` hands the question off to a Groq-hosted LLaMA 3.3 70B model acting as a "routing agent". This model is given the question plus a full description of available tools, and it decides which tool to call next — and with exactly what input.

The three tools available to it are:

- `search_docs` — semantic search over unstructured IPL 2024 and 2025 season summaries (narratives, records, awards)
- `query_data` — structured SQL queries against a SQLite database built from ball-by-ball CSV data
- `web_search` — live web lookup via Tavily for very recent news not in local data

### Step 3 — The Tool Runs

`tools.py` houses all three tool implementations. Each tool is async and returns a plain string result back to the agent loop. If a SQL query fails, the error plus the full schema is returned so the LLM can self-correct on the next iteration.

### Step 4 — The Loop Continues (Up to 8 Times)

The routing agent re-evaluates after every tool call. If the accumulated context already answers the question, it returns `"none"` and the loop breaks. Otherwise, it picks the next most useful tool. This continues for up to 8 steps — more than enough for even complex multi-part questions.

### Step 5 — Synthesis

Once the loop ends, a second LLM call synthesizes all the gathered tool results into a clean, accurate final answer. It's the same LLM but now acting as the analyst rather than the router.

### Step 6 — Response Back to Client

The full response — final answer, citations (which tools were used), step count, and a detailed trace of every step — is returned as JSON to the client, which pretty-prints it for you.

---

## Tech Stack

| Technology | Role in the Project |
|---|---|
| **FastAPI** | REST API framework that exposes the `/agent` endpoint |
| **Groq + LLaMA 3.3 70B** | LLM backbone for both the routing agent and answer synthesis |
| **FAISS + HuggingFace Embeddings** | Vector store for semantic search over IPL season summaries |
| **SQLite + Pandas** | Structured ball-by-ball data store, built on-demand from CSV |
| **Tavily** | Live web search for recent IPL news and results |
| **LangChain** | Text splitting and FAISS retriever abstraction |
| **Python-dotenv** | Environment variable management |
| **Uvicorn** | ASGI server to run the FastAPI app |
| **Requests** | HTTP client used in `client.py` to call the API |

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- A Groq API key (free tier available at [console.groq.com](https://console.groq.com))
- A Tavily API key (free tier available at [tavily.com](https://tavily.com))
- IPL data files: `ipl_2024-2025.csv`, `ipl_2024_summary.txt`, `ipl_2025_summary.txt`

### Installation

```bash
git clone <your-repo-url>
cd ipl-agent
pip install fastapi uvicorn groq langchain langchain-community \
    langchain-huggingface faiss-cpu sentence-transformers \
    pandas tavily-python python-dotenv requests
```

### Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

### Running the Server

```bash
python main.py
```

The API will start on `http://127.0.0.1:8000`. You can explore the auto-generated docs at `http://127.0.0.1:8000/docs`.

### Asking Questions

```bash
python client.py
```

Edit the `questions` list in `client.py` to ask whatever you want. The default timeout is 180 seconds — LLM calls with multiple tool steps can take 2–3 minutes on slower connections.

---

## Project Structure

```
ipl-agent/
├── main.py                  # FastAPI app, agent loop, LLM routing & synthesis
├── tools.py                 # search_docs, query_data, web_search implementations
├── client.py                # Test client to talk to the /agent endpoint
├── ipl_2024-2025.csv        # Ball-by-ball match data (source of truth for stats)
├── ipl_2024_summary.txt     # Narrative season summary for 2024
├── ipl_2025_summary.txt     # Narrative season summary for 2025
├── ipl_data.db              # Auto-generated SQLite DB (created on first run)
└── .env                     # API keys (never commit this)
```

