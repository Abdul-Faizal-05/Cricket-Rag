import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

# Increase if your machine / API is slow. LLM + multiple tool calls can take 2-3 min.
REQUEST_TIMEOUT = 180  # seconds


def ask_agent(question: str, retries: int = 2) -> None:
    """Send a question to the IPL agent and pretty-print the response."""
    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print('='*60)

    response = None
    for attempt in range(1, retries + 2):  # retries + 1 total attempts
        try:
            if attempt > 1:
                print(f"  Retrying... (attempt {attempt})")
                time.sleep(2)

            print("  Waiting for agent response (may take up to 3 min)...")
            response = requests.post(
                f"{BASE_URL}/agent",
                json={"question": question},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            print(f"\nFinal Answer:\n{data.get('final_answer', 'No answer returned.')}")
            print(f"\nSources used : {', '.join(data.get('citations', []))}")
            print(f"Steps taken  : {data.get('steps_used', 'N/A')}")

            # Show the full reasoning trace
            print("\n--- Full Trace ---")
            for i, step in enumerate(data.get("steps", []), start=1):
                print(f"\nStep {i}: [{step['tool']}]")
                print(f"  Input : {step['input']}")
                result_preview = str(step['result'])[:300]
                suffix = "..." if len(str(step['result'])) > 300 else ""
                print(f"  Result: {result_preview}{suffix}")

            return  # success — stop retrying

        except requests.exceptions.Timeout:
            print(f"  Attempt {attempt} timed out after {REQUEST_TIMEOUT}s.")
            if attempt == retries + 1:
                print("All attempts timed out. Try these fixes:")
                print("   1. Increase REQUEST_TIMEOUT at the top of client.py")
                print("   2. Switch to a faster Groq model in main.py (e.g. llama-3.1-70b-versatile)")
                print("   3. Check your internet connection (web_search tool needs it)")

        except requests.exceptions.ConnectionError:
            print("Could not connect to the server. Is main.py running on port 8000?")
            print("   Run:  python main.py")
            return  # no point retrying a connection error

        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error {e.response.status_code}: {e.response.text}")
            return

        except requests.exceptions.JSONDecodeError:
            status = response.status_code if response is not None else "N/A"
            body = response.text if response is not None else "N/A"
            print(f"Failed to decode JSON. Status: {status}")
            print(f"   Body: {body[:500]}")
            return

        except requests.exceptions.RequestException as e:
            print(f"Unexpected request error: {e}")
            return


if __name__ == "__main__":
    questions = [
        "How to cook pizza?",
    ]

    for q in questions:
        ask_agent(q)