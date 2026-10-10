"""
Orbit POC: run a local LLM via Ollama to ingest -> process -> output data.

Usage:
    ollama pull llama3.2:3b
    pip install requests faster-whisper   # faster-whisper only needed for audio
    python poc_agent.py sample_input.txt
    python poc_agent.py meeting.mp3 --model qwen2.5:3b
    python poc_agent.py sample_input.txt --ctx 8192   # larger context window (uses more RAM)

Output: <input>.out.json  +  a benchmark summary printed to the console.
"""
import argparse
import json
import platform
import sys
import time
from pathlib import Path

import requests

OLLAMA_URL = "http://localhost:11434/api/chat"

SYSTEM_PROMPT = """You are a data-processing agent for financial advisor meeting notes.
Read the input text and return ONLY valid JSON with exactly these keys:
{
  "summary": "2-3 sentence summary",
  "action_items": [{"task": "...", "owner": "name(s) or null", "due": "date or null"}],
  "decisions": ["..."],
  "open_questions": ["..."]
}

Rules:
- The advisor leads the meeting. Everyone else is a client. Tasks the advisor asks clients to do
  (like sending documents) are owned by the clients, not the advisor.
- "owner" is the person who must do the task, not the person who benefits from it.
  If several people are asked, list all of them.
- "decisions" only includes things people explicitly agreed to.
- A question that was asked but not answered or settled belongs in "open_questions", not "decisions".
- If a number is corrected during the conversation, use the corrected value.
- Include follow-up meetings and any preparation someone promised for them.
- Use dates exactly as they appear in the text. Do not guess or invent dates.
- Do not invent information that is not in the text.
- Do not add a year. Write dates as the text does, such as "October 21" or "Friday"."""


def ingest(path: Path) -> str:
    """Text files are read directly; audio is transcribed locally with Whisper."""
    if path.suffix.lower() in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".mp3", ".wav", ".m4a", ".flac"}:
        from faster_whisper import WhisperModel  # lazy import

        t0 = time.time()
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(path))
        text = " ".join(s.text.strip() for s in segments)
        print(f"[audio] transcribed in {time.time() - t0:.1f}s")
        return text
    sys.exit(f"Unsupported file type: {path.suffix}")


def process(text: str, model: str, ctx: int) -> tuple[dict, dict]:
    payload = {
        "model": model,
        "stream": False,
        "format": "json",  # forces valid JSON output
        "options": {"temperature": 0, "seed": 42, "num_ctx": ctx},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    }
    r = requests.post(OLLAMA_URL, json=payload, timeout=600)
    r.raise_for_status()
    data = r.json()
    try:
        result = json.loads(data["message"]["content"])
    except json.JSONDecodeError:
        result = {"error": "model returned invalid JSON", "raw": data["message"]["content"]}
    return result, data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--model", default="llama3.2:3b")
    ap.add_argument("--ctx", type=int, default=4096, help="context window in tokens")
    args = ap.parse_args()

    path = Path(args.input)
    text = ingest(path)
    path.with_suffix(".transcript.txt").write_text(text, encoding="utf-8")
    print(f"[ingest] {len(text)} characters")

    t0 = time.time()
    result, raw = process(text, args.model, args.ctx)
    wall = time.time() - t0

    out = path.with_suffix(".out.json")
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    # Benchmark numbers for the findings write-up
    tok = raw.get("eval_count", 0)
    tok_s = tok / (raw["eval_duration"] / 1e9) if raw.get("eval_duration") else 0
    print("\n=== BENCHMARK ===")
    print(f"machine        : {platform.platform()} / {platform.processor()}")
    print(f"model          : {args.model}")
    print(f"context window : {args.ctx}")
    print(f"prompt tokens  : {raw.get('prompt_eval_count')}")
    print(f"output tokens  : {tok}")
    print(f"speed          : {tok_s:.1f} tokens/sec")
    print(f"wall time      : {wall:.1f}s")
    print(f"output file    : {out}")
    print("Also run `ollama ps` in another terminal to see RAM/VRAM used.")


if __name__ == "__main__":
    main()