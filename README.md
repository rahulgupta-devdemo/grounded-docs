# Grounded Docs

A document chat with retrieval-augmented generation (RAG). Upload PDF documents and ask questions about them in English or German. Answers are based only on the uploaded documents, and every statement cites the file and page it comes from. A citation can be clicked to show the exact passage the answer was built from.

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

Stop with `docker compose down`. Uploaded documents are kept in Docker volumes; `docker compose down -v` deletes them.

### Environment variables

Only `GEMINI_API_KEY` is required. Everything else has a default.

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | – (required) | Gemini API key. Under Google's terms, an application used by people in the EEA must run on a project with billing enabled. |
| `CHAT_MODELS` | `gemini-3.1-flash-lite,gemini-3.5-flash-lite` | Answer models, tried in order when one is overloaded or too slow |
| `CHAT_TIMEOUT_SECONDS` | `10` | Time each answer model gets before the next one is tried (API minimum: 10) |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` | `gemini-embedding-2` / `768` | Embedding model and vector size |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1500` / `200` | Passage length and overlap, in characters (chosen with the retrieval evaluation) |
| `TOP_K` | `5` | Passages given to the model per question |

---

## What it does

- **Upload** one or more PDFs. Each is split into passages that stay within one page, embedded, and stored in Qdrant with file name and page number.
- **Ask** a question. The five most relevant passages are retrieved, and the model answers only from them.
- **Choose where to search:** all documents, or a selection. With many documents, filter the list by file name and select or deselect all matches at once; the chat always shows how many documents it searches.
- **Check** every answer: citations such as [1] open the source passage, and from there the original PDF at that page; passages retrieved but not used are listed separately.
- **Summarise** a whole document with one click. Questions use a few retrieved passages; a summary sends the complete document text in one call and cites pages.
- **Open, download or delete** documents. Deleting removes both the passages and the stored PDF. The list shows when each document was uploaded and can be sorted by name or newest first; the panel can be widened for long file names.
- **Say "not found"** when the documents do not contain the answer, instead of guessing. Greetings, acknowledgements such as "ok" or "thanks", and questions about the app itself such as "what can you do" get a short hint instead of a search.
- **Work across languages:** a German question can be answered from an English datasheet and the other way round; the answer is always in the language of the question.
- **Show the cost:** each answer shows the model used, tokens and cost (typically well below $0.01).
- **Stay available:** if an answer model is overloaded or takes longer than 10 seconds, the next configured model answers.
- **Interface in English or German**, with a light and a dark theme. Both follow the browser and system settings at first and remember the user's choice.

---

## How it works

```
Browser ──► nginx (frontend container, :8080)
              ├── /      → React app (static files)
              └── /api/* → FastAPI backend (:8000) ──► Gemini API (embeddings, answers)
                                                   └──► Qdrant (:6333, vectors + passages)
```

**Upload** (`POST /documents`): PDF → text per page (PyMuPDF) → passages of up to 1,500 characters with 200 characters overlap, cut at paragraph or sentence boundaries → one 768-dimensional vector per passage (`gemini-embedding-2`) → stored in Qdrant with file, page and text. The document id is a hash of the file content, so uploading the same file again replaces it instead of creating duplicates.

The original PDF is kept on a Docker volume, so it can be opened at a cited page (`GET /documents/{id}/file#page=N`) or downloaded. Only ids of the form produced by the hash are accepted, so the endpoint cannot be used to read other files.

**Question** (`POST /chat`): question → vector → the 5 most similar passages (cosine similarity) → prompt with numbered passages and the rules: use only these passages, cite them, say when the answer is missing, answer in the question's language → answer with citations, all retrieved passages and the cost.

**Summary** (`POST /documents/{id}/summary`): the full text of the stored PDF, with each page marked, is sent in one call (up to about 100,000 tokens, roughly $0.03); the summary cites pages and is written in the document's language. Retrieval suits specific questions; a summary needs the whole document, which is where long-context models are the better tool.

The frontend only ever calls `/api`. In development Vite forwards it to the backend, in Docker nginx does, so the browser talks to a single origin and no backend URL is built into the app.

---

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS; served by nginx, which also proxies `/api` |
| Backend | Python 3.13, FastAPI, Pydantic |
| PDF extraction | PyMuPDF (text per page, in reading order) |
| Embeddings | Google `gemini-embedding-2`, 768 dimensions, multilingual |
| Answer model | Google `gemini-3.1-flash-lite`, fallback `gemini-3.5-flash-lite` |
| Vector database | Qdrant 1.19 (cosine similarity, payload filtering; keyword vectors with IDF for the optional hybrid search) |
| RAG orchestration | Own code: chunking, retrieval, prompt, citations, summaries |
| Packaging | Docker Compose: frontend, backend, Qdrant; data on Docker volumes |
| Tests | pytest with an in-memory Qdrant and fake model calls |

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
| Retrieval instead of whole documents in the prompt | About 2,000 tokens per question instead of ~100,000 for a long manual, scales to many documents, reliable citations | Long-context prompting (simpler for a single short document) |
| Semantic search, no keyword search by default | Measured: hybrid search (keyword + semantic, rank fusion) ranked the right page first for 75% instead of 88% and answered 21 instead of 22 questions correctly | Hybrid search (kept as an option) |
| 1,500-character passages | Measured: right page ranked first for 88% of 24 test questions, vs 83% with 3,000 | 3,000 (worse ranking), 800 (one question better, half the context per passage) |
| One module per external system | `llm.py` is the only code that talks to Gemini, `vector_store.py` the only code that talks to Qdrant, so either can be replaced in one place | – |

**Why Qdrant.** Search is often limited to selected documents, so metadata filtering is needed; Qdrant stores each passage's text, file and page next to its vector, so a search result is already a citation; and it is the kind of vector database a production setup would use, while running here as a single container. Chroma would have meant fewer moving parts but a weaker path to production, FAISS is a library without metadata or persistence, and pgvector makes sense where Postgres is already operated.

**Why a lightweight custom RAG instead of LangChain.** RAG libraries were considered. The pipeline is short (extract, chunk, embed, store, retrieve, prompt, cite), and writing it directly keeps the parts that decide answer quality under direct control: where chunks are cut, which metadata travels with them, how the prompt is built and how citations are checked. It also removes a layer between the code and its behaviour when something goes wrong. With several retrievers, reranking or agent workflows, a framework would be worth revisiting.

**Why Gemini for embeddings and answers.** One provider for both steps means one key and one SDK; the embedding model is multilingual, so a German question finds an English passage. Model names are configuration, not code, and all model calls sit behind two functions in `llm.py`.

---

## Testing

99 automated tests cover chunking, PDF extraction, the Gemini integration (batching, fallback, error handling), upload, chat, file, summary and delete endpoints (including attempts to read other files through the file endpoint), citations and their validation, cost, language detection and the optional hybrid search. They run in a few seconds without Docker or an API key: Qdrant runs in memory and the Gemini calls are replaced by fakes.

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt     # Linux/macOS: .venv/bin/pip
.venv/Scripts/python -m pytest -q
```

Behaviour the unit tests cannot prove was checked against the live API and recorded in DECISIONS.md: cross-language retrieval (a German question scores 0.77 against the matching English passage vs 0.69 against an unrelated one), answer language, answers to questions the documents do not cover, model latency during the day, and the full flow in Docker (including a 5 MB upload and data surviving a container restart).

### Long real document

A public 212-page product catalogue (41 MB) indexed in 119 seconds into 269 passages. Across six indexed documents, 9 of 9 questions about catalogue facts, in German and English, returned the correct value and cited the correct page, in 1.2–4.3 seconds; a summary of all 212 pages took 4.9 seconds and cost about $0.02. Uploads are limited to 100 MB.

### Retrieval evaluation

**Method.** A set of questions, each listing every page that holds its answer. The script indexes the documents with the application's own extraction, chunking and embedding code into a separate in-memory Qdrant, so a running instance is never touched, retrieves the top 5 passages per question and records the rank of the first passage from a correct page. Only retrieval is measured, not the answer model. Metrics:

- **hit@k**: share of questions with a correct page among the top k passages.
- **MRR** (mean reciprocal rank): average of 1 / rank of the first correct page (1.0 means always first; a miss counts 0).

**Data.** 24 questions (11 German, 13 English) on four public product documents from a lighting manufacturer: a 24-page product brochure in German, its 22-page English edition, and two 3-page technical datasheets, one English and one German. Questions cover facts in running text, numbers in specification tables, article numbers, and questions in one language whose answer is only in a document in the other. The documents and questions are not part of this repository.

**Results.**

| Chunk size / overlap (characters) | Passages | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|---|
| 800 / 100 | 71 | 0.92 | 0.96 | 0.96 | 0.93 |
| **1500 / 200 (default)** | 54 | 0.88 | 0.96 | 0.96 | 0.91 |
| 3000 / 400 | 44 | 0.83 | 0.92 | 0.96 | 0.88 |

All brochure questions rank the right page first, in both languages. Every miss is a datasheet question: by article number, or in English about the German-only datasheet. Smaller passages rank better because a long specification page as one passage mixes too many facts. 1,500 was chosen over 800 because the difference is one question of 24, while 1,500 keeps twice the context per passage. Details in DECISIONS.md, section 18.

**Hybrid search, built and measured.** Because the misses involve article numbers, a keyword search was added next to the semantic search: each passage also gets a sparse word vector, Qdrant weights words by rarity (IDF, as in BM25), and the two rankings are merged with reciprocal rank fusion. On the same questions it was worse for every chunk size:

| 1500 / 200 | hit@1 | hit@3 | hit@5 | MRR | Answers correct |
|---|---|---|---|---|---|
| **Semantic (default)** | **0.88** | **0.96** | **0.96** | **0.91** | **22 of 24** |
| Hybrid | 0.75 | 0.92 | 0.92 | 0.83 | 21 of 24 |

The answer evaluation varies between runs of the same setup (22 and 21 of 24, see below), so this comparison rests on the retrieval metrics, with the answer counts as an additional signal. Semantic search is already strong on these documents, and an equally weighted keyword ranking mostly adds noise: words such as the product name occur on many pages. Keyword matching also cannot bridge languages: for an English question about the German datasheet, the English word "order" matched the English datasheet's "Order No." header and pulled the wrong document up. The default therefore stays semantic; `RETRIEVAL_MODE=hybrid` switches the experiment on, and both evaluation scripts compare the two modes.

### Answer-quality evaluation

The same 24 questions went through the full pipeline (retrieval, prompt, answer model, citations), together with 8 questions the documents cannot answer (price, warranty, delivery time, reference customers, ATEX approval, production CO₂, packaging colour, the manufacturer's CEO). Each answer was checked automatically for the expected facts, and each "not answerable" question for a clear statement that the documents do not contain the information; the two automatic misses were then checked by hand.

The full evaluation was run twice with the same documents, questions and settings, because the answer model does not give identical answers every time:

| Check | Run 1 | Run 2 |
|---|---|---|
| Answer contains the expected facts | **22 of 24** | **21 of 24** |
| Answer cites a page that holds the answer | 23 of 24 | 23 of 24 |
| Unanswerable question correctly declined | **8 of 8** | **8 of 8** |
| Answers stating a wrong value | none | 1 |

Two misses appear in both runs, and both are datasheet cases the retrieval evaluation already pointed to. An English question about a value that only exists in the German datasheet found the right page but not the passage with the value, and the answer said the documents do not contain it: wrong, but a safe failure rather than a guess. A question about "certifications" was answered with the product family's certificate list from the brochure, which is correct there, but missed the approval marks listed in the datasheet.

Run 2 also had one real error. The brochure page prints "50 % lighter than the previous model" directly above "25 % faster installation", and asked how much faster installation is, the answer said 50 %. The number is on the cited page, so one click on the citation shows the mistake, but the answer is wrong. Mixing up neighbouring figures on a page of short claims is a known weakness of language models, and it is the reason every answer shows its sources.

**Run them on your own documents:** copy `evaluation/questions.example.json` to `evaluation/questions.json`, list your PDFs, questions, expected pages and expected facts, then:

```bash
cd backend
.venv/Scripts/python ../evaluation/run_eval.py --docs <folder with the PDFs>          # retrieval
.venv/Scripts/python ../evaluation/run_answer_eval.py --docs <folder with the PDFs>   # answers
```

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
- **Whole-document questions typed into the chat** ("summarise the document") see only the 5 retrieved passages; the answer says so and the Summary button covers the whole document. Summaries are limited to about 100,000 tokens; for longer documents the summary states which pages it covers.
- **No conversation memory:** every question is answered on its own, so a follow-up like "and the 3000 K version?" lacks context.
- **Single user:** no login; all uploaded documents are visible to everyone using the instance.
- **Latency** on the free API tier varies during the day.
- **The free tier also has a daily embedding limit** (about 1,000 texts at the time of writing, resetting at midnight Pacific time). Normal use stays far below it, but repeated evaluation runs and several large uploads on one day can exhaust it; uploads then fail with a clear quota message while questions keep working until the last embeddings are used.
- **Large uploads are slow on the free tier:** embeddings are limited to about 100 passages per minute. Measured: a 170-page manual (276 passages) took 150 seconds to index; the upload waits up to 10 minutes. With billing enabled the limit is much higher. For very large collections, indexing should move to a background job.

## Next steps, with more time

1. **Better retrieval for identifiers and cross-language datasheets:** plain hybrid search measured worse (see above). Next candidates, each measured with the same questions plus the catalogue check as a holdout: a reranker over the top 20 passages; keyword matching only for identifier-like terms such as article numbers; fusion weighted towards semantic search.
2. **A larger evaluation set** built from real user questions, including answer quality, not only retrieval.
3. **Scanned pages, tables and diagrams:** `gemini-embedding-2` can embed page images directly.
4. **Conversation memory:** rewrite follow-up questions using the previous turns before retrieval.
5. **Data protection for real documents:** Vertex AI in an EU region, or an open-weight model (for example `gpt-oss-120b`) on company or EU infrastructure, behind the same `generate()` interface.
6. **Authentication** and per-user document access; indexing as a background job with a progress indicator, so large uploads return immediately.
7. **For larger document collections:** filters by metadata (product family, document type, date) beyond the file-name filter, stored chat sessions, suggested questions per document. Stored sessions are left out on purpose: they need users and a database first.
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
    file_store.py      original PDFs (open, download, summarise)
    answering.py       question pipeline, prompt, citations
    summarizing.py     whole-document summaries
    llm.py             all Gemini calls (embeddings, answers, fallback)
    vector_store.py    all Qdrant calls
    language.py        German / English detection
    pricing.py         price table for the cost per answer
  tests/
frontend/
  src/
    api.ts             typed API client
    App.tsx            document list and selection
    useChat.ts         chat state for questions and summaries
    components/        DocumentPanel, ChatPanel, Exchange, AnswerText, SourceList
  nginx.conf           serves the app, proxies /api to the backend
docker-compose.yml     qdrant, backend, frontend
evaluation/            retrieval and answer-quality evaluation scripts, question format
DECISIONS.md           decisions, alternatives, measurements
```
