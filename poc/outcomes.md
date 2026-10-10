# Outcomes: Local AI Agent POC (Issue #49)

**Verdict: yes, we can run our own AI agent locally.** It runs on an ordinary laptop with no GPU and no
usage fees, and it turns text or audio into useful structured data. Its output still needs a human check,
so think of it as a drafting assistant, not an autopilot.

## What we tried
- **Tool:** Ollama, which runs open-source AI models on your own computer.
- **Task:** read a made-up financial advisor meeting and output JSON with a summary, action items
  (who / what / when), decisions and open questions.
- **Inputs:** text, and audio (Whisper speech-to-text first, then the same model).
- **Models:** llama3.2:3b, qwen2.5:3b, llama3.1:8b.
- **Test laptop:** Windows 11, AMD CPU, no GPU. Everything ran on the CPU.
- **Files:** `poc_agent.py` is the script, `results/` has the raw outputs.

## Results

| Model | RAM used | Speed | Time for the test meeting | Quality (out of 5) |
|---|---|---|---|---|
| llama3.2:3b | 2.6 GB | 15-20 tokens/sec | about 25 s | 3 |
| qwen2.5:3b | 2.2 GB | about 20 tokens/sec | about 18 s | 3 |
| llama3.1:8b | 5.6 GB | about 10 tokens/sec | about 40 s | 3.5 |

Quality is a rough score: we checked each output against six known details in the test conversation
(corrected loan payment, who owns which task, the Friday and Nov 4 tasks, the unanswered TFSA vs RRSP
question, and the actual decision). Each model was run once or twice and results changed between runs, so
treat the scores as a general impression, not a precise benchmark.

**Audio:** Whisper turned a short recording into text in about 11 seconds, and the rest of the pipeline
worked the same as with text.

## What resources do we need?
- **3B models:** about 2.5 GB of RAM. Fine on a normal laptop.
- **8B model:** about 5.6 GB of RAM and half the speed. Works, but a 16 GB machine is more comfortable.
- **Disk:** 2-5 GB per model.
- **GPU:** not needed at this size.
- **Length limit:** the default window (4,096 tokens) fits a short meeting. A real 30+ minute meeting would
  need to be split into chunks, or we raise the limit and use more RAM.

## Can we use it in our project?
- **Cost:** no per-use fees. Our costs are the hardware and developer time.
- **Privacy:** client conversations never leave the machine, a real plus for financial data.
- **Hardware:** works on a regular laptop. We should still test on teammates' machines with less RAM.
- **Deployment options:** every user runs it locally, we host it on a server (a cost), or we call a hosted
  API instead (per-use cost, better quality, no hardware needed).
- **Docker:** Ollama could be added as a service in our compose file, or our app could call Ollama on the
  host machine.

## What worked and what didn't
**Worked:** valid JSON every time, numbers and dates, catching the corrected loan payment ($400 to $450),
and accurate speech-to-text for numbers and dates.

**Didn't work well:**
- Small models drop details, such as the unanswered TFSA vs RRSP question and some tasks.
- They sometimes give a task to the wrong person, and one model (qwen) invented years in dates.
- The same model gave different answers on different runs.
- Audio: names were slightly misspelled ("Nayiri" became "Nairi"), and Whisper doesn't say who is
  speaking, so who-said-what gets lost.
- The 8B model was the most accurate but also the most cautious, leaving out several items.

## Recommendation
We can use it but with these conditions:
1. Use it to **draft** summaries and action items that a person reviews, not for unattended use on client
   records.
2. Start with a 3B model for speed and low memory. After you test your local machine move to 8B since accuracy matters more than speed.
3. Keep a hosted API in mind as a fallback for weaker machines or higher quality.


## How to run it 
First install ollama:  
https://ollama.com/download 
Choose Mac or Windows based on your device. 
Then run these models and check output.json
```

ollama pull llama3.2:3b
ollama pull llama3.1:8b  # Be careful it is larger and Slower
pip install requests faster-whisper
python poc_agent.py sample_input.txt --model llama3.2:3b

python poc_agent.py test.wav          # audio
```
If audio fails with `unexpected keyword argument 'metadata_errors'`, run `pip install "av>=14,<16"`.
