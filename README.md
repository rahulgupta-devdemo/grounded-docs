# Document Chat

Upload PDF documents and ask questions about them in English or German. Answers are based only on the uploaded documents, and every statement cites the file and page it comes from. A citation can be clicked to show the exact passage the answer was built from.

---

## Quick start

**Requirements:** Docker Desktop, and a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

```bash
git clone <this repository>
cd grounded-docs
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
# open .env and set GEMINI_API_KEY=...
docker compose up --build
```

Open **http://localhost:8080**. The first build takes about four minutes.

| URL | What |
|---|---|
| http://localhost:8080 | The application |
| http://localhost:8000/docs | Interactive API documentation (FastAPI) |
| http://localhost:6333/dashboard | Qdrant dashboard: stored passages and vectors |

Stop with `docker compose down`. Uploaded documents are kept in a Docker volume; `docker compose down -v` deletes them.

### Environment variables

Only `GEMINI_API_KEY` is required. Everything else has a default.

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | – (required) | Gemini API key. Under Google's terms, an application used by people in the EEA must run on a project with billing enabled. |
| `CHAT_MODELS` | `gemini-3.1-flash-lite,gemini-3.5-flash-lite` | Answer models, tried in order when one is overloaded or too slow |
| `CHAT_TIMEOUT_SECONDS` | `10` | Time each answer model gets before the next one is tried (API minimum: 10) |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` | `gemini-embedding-2` / `768` | Embedding model and vector size |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `3000` / `400` | Passage length and overlap, in characters |
| `TOP_K` | `5` | Passages given to the model per question |

---

## What it does

- **Upload** one or more PDFs. Each is split into passages that stay within one page, embedded, and stored in Qdrant with file name and page number.
- **Ask** a question. The five most relevant passages are retrieved, optionally limited to selected documents, and the model answers only from them.
- **Check** every answer: citations such as [1] open the source passage; passages retrieved but not used are listed separately.
- **Say "not found"** when the documents do not contain the answer, instead of guessing.
- **Work across languages:** a German question can be answered from an English datasheet and the other way round; the answer is always in the language of the question.
- **Show the cost:** each answer shows the model used, tokens and cost (typically well below $0.01).
- **Stay available:** if an answer model is overloaded or takes longer than 10 seconds, the next configured model answers.

---

## How it works

```
Browser ──► nginx (frontend container, :8080)
              ├── /      → React app (static files)
              └── /api/* → FastAPI backend (:8000) ──► Gemini API (embeddings, answers)
                                                   └──► Qdrant (:6333, vectors + passages)
```

**Upload** (`POST /documents`): PDF → text per page (PyMuPDF) → passages of up to 3,000 characters with 400 characters overlap, cut at paragraph or sentence boundaries → one 768-dimensional vector per passage (`gemini-embedding-2`) → stored in Qdrant with file, page and text. The document id is a hash of the file content, so uploading the same file again replaces it instead of creating duplicates.

**Question** (`POST /chat`): question → vector → the 5 most similar passages (cosine similarity) → prompt with numbered passages and the rules: use only these passages, cite them, say when the answer is missing, answer in the question's language → answer with citations, all retrieved passages and the cost.

The frontend only ever calls `/api`. In development Vite forwards it to the backend, in Docker nginx does, so the browser talks to a single origin and no backend URL is built into the app.

---

## Key decisions

The full reasoning, rejected alternatives and trade-offs are in **[DECISIONS.md](DECISIONS.md)**, written before the implementation and updated with measurements. In short:

| Decision | Main reason | Main alternative rejected |
|---|---|---|
| RAG pipeline written directly, no framework | The pipeline is short; direct code gives control over chunk boundaries, citation metadata and the prompt, and every step can be explained | LangChain / LlamaIndex; Gemini File Search (managed, but hides retrieval) |
| Gemini for embeddings and answers | One provider, one key; multilingual; low cost | OpenAI, Anthropic (no embeddings), Grok (no embeddings, 5× input price), local models |
| Flash-Lite answer model with fallback | Measured: the larger Flash models returned "overloaded" on the free tier; Flash-Lite answered in 1–5 s | `gemini-3.8-flash` |
| Qdrant | Metadata filtering, payload next to vectors, production-grade, one container | Chroma, FAISS, pgvector |
| Passages within one page | Every citation points to exactly one page | Passages across page breaks |
| Question language detected in code | A prompt rule alone produced German answers to English questions in 4 of 9 test runs; naming the language fixed it (9 of 9) | Prompt wording only; a language-detection library |
| Retrieval instead of whole documents in the prompt | About 20× cheaper per question on long manuals, scales to many documents, reliable citations | Long-context prompting (simpler for a single short document) |
| One module per external system | `llm.py` is the only code that talks to Gemini, `vector_store.py` the only code that talks to Qdrant, so either can be replaced in one place | – |

---

## Testing

56 automated tests cover chunking, PDF extraction, the Gemini integration (batching, fallback, error handling), upload and chat endpoints, citations, cost and language detection. They run in a few seconds without Docker or an API key: Qdrant runs in memory and the Gemini calls are replaced by fakes.

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt     # Linux/macOS: .venv/bin/pip
.venv/Scripts/python -m pytest -q
```

Behaviour the unit tests cannot prove was checked against the live API and recorded in DECISIONS.md: cross-language retrieval (a German question scores 0.77 against the matching English passage vs 0.69 against an unrelated one), answer language, answers to questions the documents do not cover, model latency during the day, and the full flow in Docker (including a 5 MB upload and data surviving a container restart).

### Running without Docker (development)

```bash
docker compose up qdrant                      # or any Qdrant on localhost:6333
cd backend && .venv/Scripts/uvicorn app.main:app --reload
cd frontend && npm install && npm run dev     # http://localhost:5173
```

---

## Limitations

- **Text PDFs only.** Scanned pages, and content inside images, tables drawn as graphics or diagrams, are not read. Uploading a scanned PDF returns a clear message.
- **Exact identifiers** such as article numbers can be missed by pure vector search.
- **Whole-document questions** ("summarise the document") see only the 5 retrieved passages; the answer says so.
- **No conversation memory:** every question is answered on its own, so a follow-up like "and the 3000 K version?" lacks context.
- **Single user:** no login; all uploaded documents are visible to everyone using the instance.
- **Latency** on the free API tier varies during the day.

## Next steps, with more time

1. **Retrieval evaluation:** a set of questions with the page that holds each answer; measure hit rate and mean reciprocal rank, and use it to tune chunk size and top-k.
2. **Hybrid search and reranking:** keyword search alongside vector search for article numbers and codes; rerank the top 20 passages.
3. **Scanned pages, tables and diagrams:** `gemini-embedding-2` can embed page images directly.
4. **Whole-document summaries:** send the complete document in one call, where long context is the better tool.
5. **Conversation memory:** rewrite follow-up questions using the previous turns before retrieval.
6. **Data protection for real documents:** Vertex AI in an EU region, or an open-weight model (for example `gpt-oss-120b`) on company or EU infrastructure, behind the same `generate()` interface.
7. **Authentication** and per-user document access; ingestion as a background job for large files.
8. **Integration:** the API works without the UI, so document sources or workflow automation can use the same endpoints.

---

## Project structure

```
backend/
  app/
    main.py            FastAPI app, error handling, /health
    api/               endpoints: documents.py, chat.py
    config.py          settings from environment variables
    schemas.py         request and response models
    pdf_parser.py      PDF → text per page
    chunking.py        pages → passages
    ingestion.py       upload pipeline
    answering.py       question pipeline, prompt, citations
    llm.py             all Gemini calls (embeddings, answers, fallback)
    vector_store.py    all Qdrant calls
    language.py        German / English detection
    pricing.py         price table for the cost per answer
  tests/
frontend/
  src/
    api.ts             typed API client
    App.tsx            document list and selection
    components/        DocumentPanel, ChatPanel, Exchange, AnswerText, SourceList
  nginx.conf           serves the app, proxies /api to the backend
docker-compose.yml     qdrant, backend, frontend
DECISIONS.md           decisions, alternatives, measurements
```
