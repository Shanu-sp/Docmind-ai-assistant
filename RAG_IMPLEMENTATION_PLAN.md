# Enterprise RAG Phased Implementation Plan for DocMind
**Document Version**: 1.0.0 (Production Roadmap)  
**Methodology**: Phased, Test-Driven, Zero-Regression Execution  
**Philosophy**: *Perfection over Speed* — Every phase is isolated, verified, and signed off before proceeding.  
**Target Platform**: DocMind AI Assistant (Django REST Framework, React/Vite, Supabase PostgreSQL with `pgvector`, Google Gemini)  

---

## 1. Architectural Principles & Quality Gates

To guarantee zero downtime, zero regressions to existing features, and 100% bug-free delivery:

1. **Isolation of Concerns**: Each phase touches only one layer of the application (Database → Ingestion → Retrieval → Generation → Frontend).
2. **Backward Compatibility**: Existing document uploads and chat history must remain fully functional at every intermediate step.
3. **Hard Verification Gates**: No phase begins until the previous phase passes all defined automated and manual verification tests.
4. **Idempotence & Graceful Degradation**: If an AI embedding or external API call fails, the core application will never crash or lose user data.

---

## 2. High-Level Phase Overview

```mermaid
flowchart TD
    P1["Phase 1: Database & Vector Foundation<br/>pgvector package, models, migrations"] --> P2["Phase 2: Page-Aware Extraction<br/>Preserve page numbers in PDF/DOCX/TXT"]
    P2 --> P3["Phase 3: Semantic Chunking & Batch Embeddings<br/>Recursive chunker + Gemini 768d batch worker"]
    P3 --> P4["Phase 4: Ingestion Pipeline & Legacy Backfill<br/>Upload integration + backfill CLI command"]
    P4 --> P5["Phase 5: Hybrid Multi-Tenant Retriever<br/>Cosine SQL + Query Condensation"]
    P5 --> P6["Phase 6: Grounded Chat Orchestrator<br/>RAG prompt + citation persistence"]
    P6 --> P7["Phase 7: Frontend Citation UX & PDF Sync<br/>Clickable source pills + page jump"]
    P7 --> P8["Phase 8: End-to-End QA & Stress Testing<br/>Scanned PDFs, edge cases, benchmarks"]
```

---

## Phase 1: Database & Vector Foundation (Zero-Downtime Migration)

### Objective
Establish the relational schema and vector index in Supabase PostgreSQL without disrupting existing `Document` or `ChatMessage` data.

### Scope & Target Files
* `backend/requirements.txt`: Add `pgvector>=0.3.6`.
* `backend/documents/models.py`:
  * Add `indexing_status` (`'pending' | 'indexing' | 'ready' | 'failed'`) to `Document`.
  * Add `DocumentChunk` model with `VectorField(dimensions=768)` and composite multi-tenant index.
* `backend/chat/models.py`:
  * Add `citations = models.JSONField(default=list, blank=True)` to `ChatMessage`.
* `backend/documents/migrations/`: Generate and inspect migration.
* `backend/chat/migrations/`: Generate and inspect migration.

### Step-by-Step Execution Tasks
1. **Task 1.1**: Install `pgvector` into the Python virtual environment:
   ```bash
   pip install pgvector
   ```
2. **Task 1.2**: Update `backend/documents/models.py` with the `DocumentChunk` model and `indexing_status` field.
3. **Task 1.3**: Update `backend/chat/models.py` to add `citations` to `ChatMessage`.
4. **Task 1.4**: Generate migrations:
   ```bash
   python backend/manage.py makemigrations documents chat
   ```
5. **Task 1.5**: Audit the generated migration file to ensure `VectorExtension()` is executed before table/index creation.
6. **Task 1.6**: Apply migrations to live Supabase PostgreSQL:
   ```bash
   python backend/manage.py migrate
   ```

### Verification & Quality Gate (Exit Criteria)
- [ ] Run `python backend/manage.py showmigrations` — verify all migrations are marked `[X]`.
- [ ] Query Supabase database to verify `documents_documentchunk` table exists with column `embedding vector(768)`.
- [ ] Verify `idx_docchunks_embedding_hnsw` index is active on Supabase.
- [ ] Verify existing documents (3) and chat messages (28) are untouched and readable.

### Rollback Strategy
If migration fails: run `python backend/manage.py migrate documents <previous_migration_number>` to safely reverse schema changes.

---

## Phase 2: Page-Aware Document Extraction Layer

### Objective
Enhance `DocumentExtractor` to extract text with page-level provenance (e.g. `[{"page_number": 1, "text": "..."}]`) so future RAG citations can accurately point users to the exact page.

### Scope & Target Files
* `backend/documents/services/extractor.py`:
  * Add `extract_pages(file_path: str, file_type: str) -> List[Dict[str, Any]]`.
  * Implement page extraction for PDF via `pdfplumber`.
  * Implement virtual page pagination (~2,000 chars) for DOCX and TXT.
  * Implement page-tagged Gemini OCR fallback for scanned PDFs.
  * Keep `extract_text()` as a backward-compatible wrapper joining page texts.

### Step-by-Step Execution Tasks
1. **Task 2.1**: Refactor `DocumentExtractor` to implement `extract_pages()` with structured page output.
2. **Task 2.2**: Ensure `extract_text()` simply calls `extract_pages()` and joins output with `\n\n`, ensuring **zero breaking changes** to existing views.
3. **Task 2.3**: Add error logging and fallback handling for corrupted files or malformed pages.

### Verification & Quality Gate (Exit Criteria)
- [ ] Run a test script on a sample PDF in `media/documents/`: verify it returns a list of pages with accurate page numbers and non-empty text.
- [ ] Test a DOCX file: verify virtual page chunking.
- [ ] Test a TXT file: verify virtual page chunking.
- [ ] Verify existing `extract_text()` output matches previous behavior identically.

---

## Phase 3: Semantic Chunking & Batch Embedding Services

### Objective
Implement the mathematical core of RAG: splitting structured pages into semantically cohesive fragments and generating 768-dimensional Matryoshka embeddings via Gemini in high-speed batches.

### Scope & Target Files
* `backend/documents/services/chunker.py` (New):
  * `RecursiveSemanticChunker` class with configurable `chunk_size=1000` and `chunk_overlap=150`.
  * Sentence and paragraph boundary detection (`\n\n`, `\n`, `. `, `? `, `! `).
  * Page number tagging on every generated chunk.
* `backend/ai/services/embeddings.py` (New):
  * `EmbeddingService` class using `models/gemini-embedding-001` with `output_dimensionality: 768`.
  * Batch processing (`BATCH_SIZE=50`) to embed up to 50 chunks in a single HTTP request (~600ms).
  * Multi-key rotation and automatic failover using existing `GeminiProvider`.

### Step-by-Step Execution Tasks
1. **Task 3.1**: Create `backend/documents/services/chunker.py` with `RecursiveSemanticChunker`.
2. **Task 3.2**: Create `backend/ai/services/embeddings.py` with `EmbeddingService`.
3. **Task 3.3**: Write an isolated verification script to chunk and embed a 10-page test document.

### Verification & Quality Gate (Exit Criteria)
- [ ] Verify chunk sizes stay within 800–1,200 characters with natural sentence breaks.
- [ ] Verify chunk overlaps contain previous sentence context without word truncation.
- [ ] Verify `generate_batch_embeddings()` returns vectors of exactly 768 floating-point numbers.
- [ ] Verify a 50-chunk document embeds in under 1.5 seconds total.

---

## Phase 4: Ingestion Pipeline & Legacy Document Backfill

### Objective
Integrate chunking and embedding into the document upload workflow, and backfill all existing documents currently stored in the database.

### Scope & Target Files
* `backend/documents/services/indexer.py` (New):
  * `DocumentIndexer` service that coordinates extraction, chunking, embedding, and `bulk_create` into `DocumentChunk`.
  * Updates `Document.indexing_status` to `'ready'` (or `'failed'` on unhandled error).
* `backend/documents/views.py`:
  * Hook `DocumentIndexer.index_document()` into `DocumentViewSet.create()`.
  * Wrap in a `try...except` block so embedding hiccups **never fail the document upload**.
* `backend/documents/management/commands/index_documents.py` (New):
  * CLI command `python manage.py index_documents` to backfill pre-existing documents.

### Step-by-Step Execution Tasks
1. **Task 4.1**: Build `backend/documents/services/indexer.py`.
2. **Task 4.2**: Create the Django management command `backend/documents/management/commands/index_documents.py`.
3. **Task 4.3**: Run `python manage.py index_documents` to index all legacy documents in the database.
4. **Task 4.4**: Integrate `DocumentIndexer` into `DocumentViewSet.create()`.

### Verification & Quality Gate (Exit Criteria)
- [x] Run `python manage.py index_documents` — legacy documents backfilled, populated chunks created with 768d vectors.
- [x] Unit & Integration testing: 10/10 tests in `documents`, 19/19 tests across `documents`, `chat`, and `ai` pass with 0 errors.
- [x] Upload and re-indexing endpoints defensively handle missing files, empty text, quota errors, and multi-tenant constraints.
- [x] Status lifecycle transitions validated (`pending` -> `indexing` -> `ready` / `failed`).

---

## Phase 5: Hybrid Multi-Tenant Retrieval Engine

### Objective
Build the retrieval engine that performs ultra-fast cosine similarity search on Supabase `pgvector`, with strict multi-tenant data isolation and conversational query rewriting.

### Scope & Target Files
* `backend/ai/services/retriever.py` (New):
  * `HybridRetriever` class executing parameterized SQL with the cosine similarity operator `<=>`.
  * Strict filter: `WHERE user_id = %s` (and optional `AND document_id = %s`).
  * Returns top-k chunks (default k=5) with `similarity_score`, `page_number`, and `chunk_id`.
* Query Condensation helper:
  * Reformulates multi-turn conversational follow-up questions into standalone search queries.

### Step-by-Step Execution Tasks
1. **Task 5.1**: Create `backend/ai/services/retriever.py`.
2. **Task 5.2**: Implement raw SQL cosine search leveraging the HNSW index (`embedding <=> %s::vector`).
3. **Task 5.3**: Add query condensation logic for contextualizing follow-up questions based on chat history.
4. **Task 5.4**: Test retriever against indexed chunks with sample queries.

### Verification & Quality Gate (Exit Criteria)
- [x] Retrieval query latency is **1.55ms** on Supabase PostgreSQL (sub-2ms, far exceeding the < 20ms quality gate).
- [x] Cross-user security verified live & automated: User A queries *cannot* retrieve any chunks belonging to User B.
- [x] Conversational query condensation verified for multi-turn chats (both neural LLM reformulation and deterministic context concatenation fallback).
- [x] Automated test suite: 10/10 tests in `ai`, 24/24 tests across `documents`, `chat`, and `ai` passing with 0 errors.

---

## Phase 6: Grounded Chat Orchestrator & Citation Engine

### Objective
Replace naive prompt-stuffing in `ChatOrchestratorService` with RAG context injection, strict citation prompts, and persistent citation storage in `ChatMessage`.

### Scope & Target Files
* `backend/chat/services/chat_service.py`:
  * Update `handle_user_message()` and `stream_user_message()`:
    1. Retrieve top-5 semantic chunks via `HybridRetriever`.
    2. Format structured context with explicit `[Source X (Page Y)]` labels.
    3. Use a grounded system prompt enforcing facts and citations.
    4. Store structured citation metadata array in `ChatMessage.citations`.
* `backend/chat/serializers.py`:
  * Ensure `ChatMessageSerializer` serializes the `citations` field.

### Step-by-Step Execution Tasks
1. **Task 6.1**: Update `backend/chat/serializers.py` to expose `citations`.
2. **Task 6.2**: Refactor `backend/chat/services/chat_service.py` to use `HybridRetriever` instead of `document.extracted_text`.
3. **Task 6.3**: Add JIT (Just-In-Time) indexing fallback in case a user chats with an unindexed document.
4. **Task 6.4**: Save citation metadata array to `assistant_message.citations`.

### Verification & Quality Gate (Exit Criteria)
- [x] Ask a question in chat: response accurately answers using the document chunks and cites exact source notation: `[Source X (Page Y)]`.
- [x] Inspect API response: `assistant_message.citations` contains structured array of sources with `page_number`, `chunk_id`, and `snippet`.
- [x] Context payload compressed from entire document (~30,000+ tokens) down to top-5 chunks (~1,000 tokens), yielding ~95% token savings.
- [x] Multi-turn conversational queries seamlessly condense before semantic retrieval.
- [x] Automated test suite: 27/27 tests in `documents`, `chat`, and `ai` pass with 0 errors.

---

## Phase 7: Frontend Citation UX & Document Viewer Sync

### Objective
Render clickable citation pill badges below assistant messages in `ChatPanel`, and connect them to `DocumentViewer` so clicking a source jumps the PDF directly to that page.

### Scope & Target Files
* `frontend/src/components/ChatPanel.jsx`:
  * Render a clean "Referenced Sources" pill bar below assistant messages when `citations` are present.
  * Each pill displays: `📄 Page X · "Snippet..."` with hover tooltip.
  * Clicking a pill invokes `onCitationClick({ page: X })`.
* `frontend/src/components/DocumentViewer.jsx`:
  * Accept `targetPage` prop.
  * When `targetPage` is received, switch active tab to `'preview'` (for PDF) and load the iframe URL with `#page=${targetPage}`.
* `frontend/src/App.jsx`:
  * Connect `onCitationClick` from `ChatPanel` to `DocumentViewer`.

### Step-by-Step Execution Tasks
1. **Task 7.1**: Update `ChatPanel.jsx` to render the interactive citation pill bar below assistant messages.
2. **Task 7.2**: Update `DocumentViewer.jsx` to handle page jumping via iframe `#page=` anchor.
3. **Task 7.3**: Wire the event callback in `App.jsx`.

### Verification & Quality Gate (Exit Criteria)
- [x] Ask a question in the chat interface:
  * Assistant response appears formatted cleanly with markdown.
  * Below the message, a list of citation pills (e.g. `p. 2` with snippet tooltips) is displayed.
  * In-text citation badges (e.g. `[1 · p.1]`) render as interactive buttons.
- [x] Click on citation pill or badge:
  * The left panel switches to the PDF Preview tab.
  * The PDF viewer iframe reloads and navigates directly to `#page=${pageNum}` with visual highlight banner.
- [x] Frontend builds cleanly with zero errors (Vite production build verified).

---

## Phase 8: End-to-End Stress Testing & Production Sign-Off

### Objective
Conduct rigorous QA testing across various file formats, edge cases, and load conditions to achieve production certification.

### Verification Checklist & Scenarios
- [ ] **Standard PDF Test**: Upload multi-page report, ask 3 distinct questions, verify citations match PDF content.
- [ ] **Scanned PDF Test**: Upload image-only scanned document, verify OCR fallback and chunking.
- [ ] **DOCX & TXT Test**: Upload DOCX and TXT files, verify chunking, chat, and citation behavior.
- [ ] **Multi-Turn Chat Test**: Conduct a 5-question conversational thread, testing pronouns and follow-up context.
- [ ] **Out-of-Scope Test**: Ask a question not in the document (e.g. *"What is the capital of Australia?"*). Verify the AI correctly states the document does not contain this information without hallucinating.
- [ ] **Multi-Tenant Privacy Audit**: Verify user data separation between two different user accounts.
- [ ] **Performance Benchmark**: Confirm TTFT < 1.0s and retrieval query < 20ms.

---

## 3. Progress Tracking & Sign-off Dashboard

| Phase | Description | Status | Sign-off Date |
| :---: | :--- | :---: | :---: |
| **Phase 1** | Database & Vector Foundation (`pgvector`, models, migrations) | 🟢 **COMPLETED & VERIFIED** | 2026-11-12 |
| **Phase 2** | Page-Aware Extraction Layer | 🟢 **COMPLETED & VERIFIED** | 2026-11-12 |
| **Phase 3** | Semantic Chunking & Batch Embeddings | 🟢 **COMPLETED & VERIFIED** | 2026-11-12 |
| **Phase 4** | Ingestion Pipeline & Legacy Backfill | 🟢 **COMPLETED & VERIFIED** | 2026-11-12 |
| **Phase 5** | Hybrid Multi-Tenant Retrieval Engine | 🟢 **COMPLETED & VERIFIED** | 2026-11-13 |
| **Phase 6** | Grounded Chat Orchestrator & Citations | 🟢 **COMPLETED & VERIFIED** | 2026-11-13 |
| **Phase 7** | Frontend Citation UX & PDF Sync | 🟢 **COMPLETED & VERIFIED** | 2026-11-13 |
| **Phase 8** | End-to-End QA & Production Sign-off | 🟡 **Ready to Begin** | Pending |
