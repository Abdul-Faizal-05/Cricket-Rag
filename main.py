from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
import os
import json
from groq import Groq
from tools import search_docs, query_data, web_search, SCHEMA_DESCRIPTION

load_dotenv()

app = FastAPI(title="IPL Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables")

client = Groq(api_key=GROQ_API_KEY)


class QueryRequest(BaseModel):
    question: str


tool_definitions = [
    {
        "name": "search_docs",
        "description": (
            "Semantic search over unstructured IPL 2024 and 2025 summary documents. "
            "Use for narrative or contextual questions (tournament overview, records, awards)."
        ),
        "input": "A natural language query string.",
    },
    {
        "name": "query_data",
        "description": (
            "Query the structured IPL ball-by-ball data table using SQL. "
            "Use for statistics, counts, rankings, win percentages, or any numerical question. "
            "The table schema and example queries are provided in the system context."
        ),
        "input": "A valid SQL SELECT query. Use ONLY the exact column names from the schema.",
    },
    {
        "name": "web_search",
        "description": "Search the live web for very recent IPL news or results not in local data.",
        "input": "A short search query string (under 10 words).",
    },
]

tools_map = {
    "search_docs": search_docs,
    "query_data": query_data,
    "web_search": web_search,
}


def get_tool_choice(user_question: str, context_so_far: list) -> tuple[str, str]:
    """Ask the LLM which tool to call next (or 'none' if context is sufficient)."""
    context_summary = json.dumps(context_so_far, indent=2) if context_so_far else "None yet."

    prompt = f"""You are a routing agent for an IPL cricket question-answering system.

=== DATABASE SCHEMA (read carefully before writing any SQL) ===
{SCHEMA_DESCRIPTION}
=== END SCHEMA ===

User question: "{user_question}"

Context gathered so far:
{context_summary}

Available tools:
{json.dumps(tool_definitions, indent=2)}

Instructions:
1. If the context already fully answers the question, return {{"tool_name": "none", "input_query": ""}}.
2. If a previous query_data step returned a "Database error", fix the SQL using the schema above and try again.
3. For win percentage questions, you need two queries:
   a) wins per team: SELECT match_won_by, COUNT(DISTINCT match_id) AS wins FROM ipl_data WHERE season=YEAR GROUP BY match_won_by
   b) matches played per team using a UNION subquery (see schema examples)
   Then compute percentage in the synthesis step — do NOT try to do division in one query if it is complex.
4. Always use the EXACT column names from the schema. Never guess column names.
5. Pick the single best next tool and return ONLY a JSON object with keys "tool_name" and "input_query".

Respond ONLY with a JSON object. No explanation, no markdown."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    choice = json.loads(response.choices[0].message.content)
    return choice.get("tool_name", "none"), choice.get("input_query", "")


def synthesize_answer(question: str, context: list) -> str:
    """Use an LLM to produce a clean, human-readable answer from accumulated tool results."""
    context_str = json.dumps(context, indent=2)

    prompt = f"""You are an expert IPL cricket analyst.

A user asked: "{question}"

Here is the data gathered from various sources:
{context_str}

Using only the information above, write a clear, concise, and accurate answer.
If win percentage is needed and you have both wins and total matches, compute it yourself.
If the data is insufficient, say so honestly. Do not make up facts."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


@app.post("/agent")
async def run_agent(request: QueryRequest):
    question = request.question

    MAX_CALLS = 8
    tool_calls = 0
    context = []
    trace = {"question": question, "steps": []}

    while tool_calls < MAX_CALLS:
        tool_name, tool_input = get_tool_choice(question, context)

        if not tool_name or tool_name == "none":
            break

        tool_fn = tools_map.get(tool_name)
        if not tool_fn:
            trace["steps"].append({"tool": tool_name, "input": tool_input, "result": "Unknown tool."})
            break

        try:
            result = await tool_fn(tool_input)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Tool '{tool_name}' raised an error: {e}")

        context.append({"tool": tool_name, "input": tool_input, "result": result})
        trace["steps"].append({"tool": tool_name, "input": tool_input, "result": result})
        tool_calls += 1

    if tool_calls >= MAX_CALLS:
        raise HTTPException(status_code=400, detail="Tool call limit reached without a conclusive answer.")

    if not context:
        trace["final_answer"] = "I couldn't find any relevant information to answer your question."
        return trace

    trace["final_answer"] = synthesize_answer(question, context)
    trace["citations"] = list({step["tool"] for step in trace["steps"]})
    trace["steps_used"] = f"{tool_calls} / {MAX_CALLS} max"

    return trace


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)