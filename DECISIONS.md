# Decisions

This file records the main technical decisions for the document chat: what was chosen, why, what was rejected, and what the choice costs. It is kept up to date while building, so the reasoning is written down when the decision is made rather than reconstructed afterwards.

Each entry has the same shape: **Decision**, **Why**, **Rejected**, **Trade-off**.

---

## 0. Problem and scope

A user uploads documents and asks questions about them. The system finds the passages that answer the question and the model replies based only on those passages, with a reference to where each fact came from.

**In scope (baseline):** PDF upload, text extraction, chunking, embedding, vector search, grounded answers with citations (file and page), a chat UI, and a single `docker compose up` start.

**Deliberately out of scope:** authentication and multiple users, OCR for scanned PDFs, DOCX and other formats, streaming responses, conversation memory, hosting, integration with company systems. Each is listed with a next step at the end of this file.

The guiding rule: a small system that works end to end and where every step can be explained, rather than a larger one with parts that cannot be defended.

---

## 1. One repository for frontend and backend

**Decision:** A single repository with `frontend/`, `backend/` and a root `docker-compose.yml`.
**Why:** The application must start on a reviewer's machine via Docker. One clone and one command is the shortest reliable path.
**Rejected:** Separate repositories. They make sense when teams release independently, which is not the case here.
**Trade-off:** Frontend and backend history are mixed in one log.

## 2. Frontend: React, TypeScript, Vite, Tailwind

**Decision:** A single-page React app written in TypeScript, built with Vite, styled with Tailwind.
**Why:** The UI is one screen (documents, chat, sources) that talks to a REST API. TypeScript catches mismatches between the UI and the API response shapes at build time.
**Rejected:** Next.js. Server-side rendering and routing add setup without benefit for a single screen that calls an existing API.
**Trade-off:** No server-side rendering, which this app does not need.

## 3. Backend: Python and FastAPI

**Decision:** FastAPI on Python.
**Why:** The PDF, embedding and vector-store libraries are strongest in Python. FastAPI validates requests and responses with typed models and generates API docs at `/docs`, which makes the API testable without the frontend.
**Rejected:** Node/Express. It would unify the language with the frontend but has weaker document-processing libraries.
**Trade-off:** Two languages in one repository.

## 4. RAG pipeline written directly, without a framework

**Decision:** The pipeline (parse, chunk, embed, store, retrieve, build prompt, generate) is written as plain functions using the provider SDK and the Qdrant client directly.
**Why:** RAG libraries such as LangChain or LlamaIndex were allowed and considered. The pipeline here is short, and writing it directly gives full control over the parts that decide answer quality: chunk boundaries, the metadata used for citations, the retrieval query and the grounding prompt. It also removes a layer between the code and its behaviour when debugging.
**Rejected:** LangChain / LlamaIndex. Also rejected: Gemini File Search, a managed RAG service that would be the fastest route, but hides chunking and retrieval, so retrieval quality could not be measured or tuned, and it ties the whole design to one vendor.
**Trade-off:** More code to write and maintain. If the system grew to multiple retrievers, reranking or agent workflows, a framework would be worth revisiting.

## 5. Model provider: Gemini API behind a small interface

**Decision:** Google Gemini for both embeddings and answer generation. The rest of the code only calls two functions, `embed()` and `generate()`. Model names are configuration (`.env`), not code.
**Why:** One provider for both steps means one API key, one SDK and one set of rate limits. The Gemini models are multilingual, which matters for a German company with German and English documents. Keeping model names in configuration matters because model generations change quickly.
**Rejected:** OpenAI (comparable quality and price; no advantage for this task and requires prepaid credit). Anthropic (no embedding API, so a second provider would be needed). xAI Grok (no embedding model in its API, and its cheapest models cost $1.25 per million input tokens against $0.25 for the Gemini model used; its larger context window does not matter when each question sends about 4,000 tokens). OpenAI's open-weight `gpt-oss-120b` on Groq (fast and cheap, but no embedding model, so a second provider and key, and its free tier allows 8,000 tokens per minute, about two questions per minute with full-size passages). A local model via Ollama (no API cost, but a multi-gigabyte install on the reviewer's machine and slower answers).
**Trade-off:** Dependence on an external API and its rate limits. Switching provider means implementing `embed()` and `generate()` for the new SDK and re-embedding the documents.

**Answer model, chosen by measurement:** the plan was the newest stable Flash model (`gemini-3.8-flash`). Tested on the free tier on 2026-09-25, it returned `503 model overloaded` on every call, and `gemini-3.5-flash` timed out after 60 seconds. The two Flash-Lite models were the only ones that answered reliably, but their speed changed during the day:

| Model | Morning | Afternoon |
|---|---|---|
| `gemini-3.5-flash-lite` | 0.8 s | 8–19 s |
| `gemini-3.1-flash-lite` | 1.4–2.2 s | 1.9–3.3 s |

The app uses `gemini-3.1-flash-lite` (the more consistent one, and the cheapest) with `gemini-3.5-flash-lite` as fallback. Each model gets one attempt with a 10-second deadline (the minimum the API accepts); on 429, 500, 503 or 504 (504 is what the API returns when the deadline passes) the next model in `CHAT_MODELS` answers. Other errors, such as an invalid request, are not retried on another model, because a second model would fail the same way. If every model fails, the user gets a clear 502 or 504 message instead of a long wait. A first version retried each model twice with a 20-second timeout; one answer took 38 seconds, which is why the retries were removed.

In tests with the chosen model, 8 of 9 answers were correct in content and language; the ninth hit the timeout on both models during a slow period. On a paid tier or with reserved capacity, latency is expected to be more stable and the stronger model becomes a configuration change.

## 6. Embeddings: `gemini-embedding-2`, 768 dimensions

**Decision:** `gemini-embedding-2` with an output size of 768.
**Why:**
- It is the current stable model, supports 100+ languages and accepts up to 8,192 input tokens.
- Google's published benchmark shows 768 dimensions scoring almost the same as 1,536 (MTEB 67.99 vs 68.17), so the smaller size halves storage and speeds up search at a negligible quality cost.
- It can also embed images and scanned PDF pages, which gives a path to datasheets with tables and diagrams later.

**Implementation details that follow from the documentation:**
- Passing a list of texts to this model returns **one combined vector**, not one per text. Each chunk is therefore sent as its own `Content` object, and a test checks that the number of vectors equals the number of chunks. Without this, retrieval would fail silently.
- The model takes the task as a text prefix instead of a parameter: questions are embedded as `task: question answering | query: …`, chunks as `title: <file name> | text: …`.
- Vectors from different embedding models cannot be compared. The Qdrant collection name contains the model name and dimension, so changing the model can never mix old and new vectors.

**Verified against the live API:** a batch of 20 chunks returns 20 distinct 768-dimensional vectors of length 1.0. A German question ("Welche Schutzart hat die Leuchte?") scored 0.77 against an English passage about IP66 and 0.69 against an English passage about luminous flux, so cross-language retrieval ranks the right passage higher.

**Rejected:** `gemini-embedding-001`. Batching is simpler, but it is the older model, limited to 2,048 input tokens and text only. It remains the fallback if rate limits for the newer model are too tight.
**Trade-off:** Per-chunk wrapping is slightly more code than a plain list.

## 7. Vector store: Qdrant

**Decision:** Qdrant in its own container, with data on a Docker volume.
**Why:** It supports filtering by metadata (search only in selected documents), stores the chunk metadata next to each vector, and is the same kind of component a production version would use. It runs as one extra service in the Compose file.
**Rejected:** Chroma (embedded, fewer moving parts, weaker path to a production setup). FAISS (a library, not a store: no metadata, filtering or persistence without extra code). pgvector (a good choice where Postgres is already operated; there is no such dependency here).
**Trade-off:** One more container to start.

## 8. Documents: PDF only, extracted page by page

**Decision:** Accept PDF files. Extract text per page with PyMuPDF.
**Why:** PDF is the dominant format for datasheets, manuals and specifications. Extracting per page keeps the page number, which the citations need.
**Rejected:** Adding DOCX and plain text now. Each format adds its own parsing edge cases and none of them changes what is being tested: retrieval and grounding.
**Trade-off:** Scanned PDFs without a text layer return no text. The upload response reports this instead of failing silently.

## 9. Chunking: fixed size with overlap, within a page

**Decision:** Split each page's text into chunks of a fixed maximum length with overlap, preferring paragraph and sentence boundaries. Chunks do not cross page boundaries. Each chunk stores document id, file name, page number and chunk index. Initial size: ~3,000 characters (~800 tokens) with ~400 characters overlap. Final values are set by the retrieval evaluation.
**Why:** Fixed-size chunking is predictable and easy to reason about. The overlap keeps a fact that sits on a chunk boundary retrievable from at least one chunk. Keeping chunks within one page makes every citation point to exactly one page. Length is measured in characters because it needs no tokenizer and behaves the same for German and English text.
**Rejected:** Semantic chunking (boundaries chosen by embedding similarity). It adds tuning parameters that cannot be validated properly in the time available, for an unproven gain on this kind of document.
**Trade-off:** A passage that runs across a page break is split into two chunks.

## 10. Retrieval: top-k cosine similarity

**Decision:** Embed the question, return the 5 most similar chunks from Qdrant (cosine similarity), optionally restricted to selected documents.
**Why:** It is the simplest retrieval that works, and it gives a clear baseline to measure improvements against.
**Rejected for now:** Hybrid search (keyword plus vector) and reranking. Both are the most likely next improvements, especially for exact product codes and part numbers, but they should be added when the evaluation shows where the baseline fails, not before.
**Trade-off:** Pure vector search can miss exact identifiers such as article numbers.
**Observed:** in a first end-to-end test, the question about the protection class ranked a datasheet's title page (which repeats the product name) above the technical-data page that holds the answer. The answer was still correct because both were in the top 5, but it shows why the evaluation measures the rank of the right page, not just whether it was found.

## 11. Why retrieval at all, when models accept very long inputs

Current models accept around one million tokens, so the whole document could be sent with every question. This was considered.
**Chosen:** retrieval, because
- **Cost:** a 200-page manual is roughly 100,000 tokens per question, against about 4,000 with retrieval (about 20 times less).
- **Scale:** a company's full set of datasheets, manuals and specifications does not fit into any context window.
- **Traceability:** with retrieval it is known exactly which passages the model saw, so the citations are reliable.

**Where the alternative wins:** for a single short document, sending it whole is simpler and a valid choice.

## 12. Grounded answers with citations

**Decision:** The model receives only the retrieved passages, each labelled with file and page. It is instructed to answer only from them, to cite the passages it used, to say plainly when the documents do not contain the answer, and to reply in the language of the question.
**Why:** The value of the tool depends on trust. Users must be able to check any statement against its source, and a clear "not in the documents" is better than a plausible guess. Replying in the question's language lets a German question be answered from an English document and the other way round.
**Rejected:** Letting the model add general knowledge. It makes answers look better and makes them impossible to verify.
**Trade-off:** Some answers will be "not found" where a general model would have produced something.

**Answer language, fixed after testing:** with the rule "answer in the language of the question" only in the instructions, English questions about a German manual were answered in German in 4 of 9 runs; the model follows the language of the passage, especially when the answer is close to a quote. The code now detects whether the question is German or English (a word list plus umlauts, no extra dependency) and states the language explicitly ("Answer in English"). Result: 9 of 9 correct. Other languages fall back to the general rule; supporting more languages would need a language-identification library.

**Prompt injection:** document text is placed in numbered passages and the instructions say to ignore any instructions inside them. An uploaded document is data, not a command.

**No documents selected:** the model is not called at all, so there is no cost and no chance of an answer without sources.

## 13. API

**Decision:** Three endpoints: `POST /documents` (upload and index), `GET /documents` (list), `POST /chat` (question in, answer with sources and cost out).
**Why:** The API is the product boundary. The chat UI is one client; a script or a workflow automation tool could call the same endpoints.
**Trade-off:** No delete or re-index endpoint in the baseline.

## 14. Cost shown per answer

**Decision:** Each answer reports the model used, its token usage and the cost, from a price table in `pricing.py` that records its source and the date it was checked. Thinking tokens are counted as output, because they are billed as output.
**Why:** Whether a tool like this is worth running at scale is a cost question. Showing the figure on every answer makes it concrete instead of assumed. Measured in the first end-to-end test: about $0.0002–0.0003 per question with short documents; with full-size chunks about $0.002.
**Trade-off:** The price table must be kept current (the `gemini-3.8-flash` price doubles on 2027-01-01). Unknown models report no cost rather than a wrong one.

## 15. Packaging: Docker Compose

**Decision:** Three services (frontend, backend, qdrant) started with `docker compose up`. The API key and model names come from a `.env` file; `.env.example` lists every variable.
**Why:** Running from the container on the reviewer's machine is a hard requirement, so Docker is set up at the start of the build and kept working, not added at the end.
**Details:** The frontend image builds the app with Node and serves it with nginx, which also forwards `/api` to the backend; nginx's default 1 MB upload limit is raised to match the backend's 20 MB. The backend image uses the same Python version as local development. Base images and Qdrant are pinned to exact versions.
**Verified:** a build from scratch takes about four minutes; a 5 MB upload goes through nginx; German and English questions are answered in 2–3 seconds; uploaded documents survive `docker compose down` and `up`.
**Trade-off:** Requires Docker Desktop on the reviewer's machine.

## 16. Data protection and provider terms

- Under Google's Gemini API terms, applications made available to users in the EEA, Switzerland or the UK may use **only paid services**. The application should therefore run on a Google Cloud project with billing enabled. The cost at this scale is a few cents.
- For users in the EEA, Google applies its paid-service data terms even to free quota: prompts and responses are not used to improve Google's products.
- The paid Gemini API does not guarantee where data is processed. For confidential documents that must stay in the EU, the next step is to run the same models through Vertex AI in an EU region. The application code stays the same; only the client configuration changes.
- The demo uses public documents only.

## 17. Original files and whole-document summaries

**Decision:** Keep the original PDF on its own Docker volume. Serve it for viewing (the UI links to `#page=N`, so a citation opens the PDF at the cited page) and download. Add a Summary action per document that sends the document's complete text, with page markers, in one call.
**Why:** Users need to check an answer in the original, not only in the extracted passage. And a summary is a whole-document task: retrieval would give the model five passages and a summary of those would look complete while missing most of the document. For this task, sending everything is the right tool, the same trade-off as in section 11 from the other side. The summary is written in the document's language and cites pages.
**Security:** The file endpoint only accepts ids of exactly 16 hex characters, the form the content hash produces, so a request cannot point at another file on the server. Tested directly and through nginx; in addition the API key is not a file in the container at all, only an environment variable.
**Limits:** Summaries send up to about 400,000 characters (about 100,000 tokens, roughly $0.03) and get 60 seconds instead of 10. Longer documents are summarised from the first pages, and the summary says which pages it covers.
**Left out on purpose:** search in the document list, stored chat sessions and suggested questions. They help with large collections and many users; for a handful of documents they add little, and stored sessions need users and a database first.
**Trade-off:** Documents uploaded before this change have no stored file and must be uploaded again to be opened or summarised.

## 18. Evaluation (planned)

A set of test questions, each with the page that contains the answer. Metrics: hit rate at 1, 3 and 5 (is the right page among the top results) and mean reciprocal rank (how high it appears). Used to compare two or three chunk sizes. Results will be added here.

---

## Next steps, with more time

| Item | Why it was left out | Next step |
|---|---|---|
| Hybrid search and reranking | Should follow evaluation results | Add keyword search for exact identifiers; rerank the top 20 |
| Scanned PDFs, tables and diagrams | Needs OCR or image embeddings | Embed page images with `gemini-embedding-2` |
| DOCX, XLSX and other formats | Not needed to test retrieval | Add parsers behind the same ingestion interface |
| Conversation memory | Each question is answered independently | Rewrite follow-up questions using the last turns before retrieval |
| Streaming answers | Improves perceived speed only | Stream tokens from the model to the UI |
| Authentication and per-user documents | Single-user local demo | Add login and store an owner id with each chunk for filtering |
| EU data residency | Demo uses public documents | Move to Vertex AI in an EU region |
| Full control over data | Needs own infrastructure | Run an open-weight model (for example `gpt-oss-120b`) on company or EU servers behind the same `generate()` interface |
| Integration with company systems | Outside the case scope | Connect document sources and automation tools through the existing API |
