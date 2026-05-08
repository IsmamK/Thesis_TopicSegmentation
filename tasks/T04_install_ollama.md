# T04 — Install Ollama & Pull LLM Models

**Phase 1 · Setup · Estimated time: 20 min + 10 GB download · Owner: Alimool**

---

## 🎯 What you are doing
Installing Ollama, a tool that runs open-source language models (like Llama 3.1) **locally** on our computer — no API costs, no internet needed, fully reproducible.

## 🤔 Why
Our **N4** novelty claim is "local-LLM boundary refinement and auto-titling". For it to be a real contribution, we must NOT use a closed model like GPT-4. Ollama + Llama 3.1 gives us the same capability for free.

## ✅ How to know you are done
- `ollama --version` prints a version.
- `ollama list` shows `llama3.1:8b` and `mistral:7b`.
- A test prompt returns coherent text (see verify step).

---

## 📝 Steps

### Step 1 — Download Ollama

- **Windows:** https://ollama.com/download/windows → run installer → reboot if asked.
- **Mac:** https://ollama.com/download/mac → drag to Applications.
- **Linux:** `curl -fsSL https://ollama.com/install.sh | sh`

### Step 2 — Start Ollama

- **Windows / Mac:** Ollama runs as a background service after install. Check the system tray/menu bar for the Ollama icon.
- **Linux:** `ollama serve &` (keep running) — or set up as systemd service.

### Step 3 — Pull the models

In a terminal:

```
ollama pull llama3.1:8b
ollama pull mistral:7b
```

Each is ~4–5 GB. Total download: ~10 GB. Both models run on CPU (slowly) or GPU (fast). 8 GB RAM is the minimum.

### Step 4 — Test

```
ollama run llama3.1:8b "In one sentence, what is lecture topic segmentation?"
```

Expected output: a coherent English sentence about dividing lectures into topics. (Exit with `Ctrl+D`.)

Also test from Python:

```
python -c "import ollama; print(ollama.generate(model='llama3.1:8b', prompt='Say hi in 3 words.')['response'])"
```

Should print something like `"Hi there, friend."`.

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **LLM (Large Language Model)** | An AI model that predicts the next word given context. Examples: GPT-4, Llama 3.1, Claude. |
| **Open-weight model** | An LLM whose model weights you can download for free and run yourself (e.g., Llama, Mistral). Opposite of "proprietary" (GPT-4). |
| **Ollama** | A program that makes running open-weight LLMs as easy as `ollama run`. Think "Docker for LLMs". |
| **Inference** | "Running a trained model to make predictions" — what happens when you give the LLM a prompt. |
| **Context window** | How many tokens (≈ words) the LLM can read at once. Llama 3.1 8B has 128K. |
| **8B / 7B** | Number of model parameters in billions. More = smarter + slower + more RAM. |

---

## 🆘 Troubleshooting

| Problem | Fix |
|---|---|
| Pull is slow (stuck at 0%) | Large files; check your internet. Sometimes Cloudflare blocks it — retry. |
| "Error: model requires more memory than available" | Your machine has <8 GB RAM. Use `ollama pull llama3.2:3b` instead (smaller model) and update configs to use it. |
| Ollama not starting on Windows | Open "Services" (Win+R → services.msc) → find Ollama → right-click → Start. |
| GPU not used | Run `ollama ps` during generation — it should show your GPU. If not, Ollama uses CPU. Install NVIDIA CUDA drivers if you have an NVIDIA GPU. |

---

## ➡️ When done

```
python scripts/mark_done.py T04
python scripts/next.py
```
