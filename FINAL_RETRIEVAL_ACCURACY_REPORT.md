# Retrieval Transparency & Accuracy Report

## Overview
To provide users with visibility into how answers are generated and ensure balanced multi-document comparisons, we implemented enhanced metadata aggregation, structured diagnostics, and round-robin chunk interleaving.

---

## Retrieval Interleaving & Comparison Logic

### 1. The Multi-Document Dominance Problem
Standard vector search queries retrieve the top $N$ globally matching chunks. If Document A is long and has high similarity, it can easily occupy all $N$ slots, leaving 0 chunks for Document B. This makes cross-document comparisons or gap analyses impossible since the LLM only receives context from a single file.

### 2. The Interleaved Round-Robin Fix
To guarantee fair representation, when multiple documents are selected, `retrieve_chunks()` uses a two-stage aggregation:
1. **Per-File Query**: Queries ChromaDB separately for each target document, requesting up to `max(n_results, 6)` chunks.
2. **Min-Chunk Guarantee**: Extracts and appends the top 3 chunks from each document.
3. **Round-Robin Interleaving**: Fills the remaining $N - (3 \times \text{files})$ slots by taking the next best chunks from each document in a round-robin sequence until the requested count is satisfied.

---

## Source Attribution and Diagnostics API

### 1. Aggregated Source Schema
Instead of raw chunk references, the `/ask` API aggregates metadata per file:
```json
{
  "filename": "GDPR_Policy.pdf",
  "document_type": "regulation",
  "chunks_used": 4,
  "sections": ["Article 5 - Principles", "Article 6 - Lawfulness"],
  "confidence": 91.5,
  "drive_web_view_link": "https://drive.google.com/..."
}
```

### 2. Search Diagnostics
A dedicated `diagnostics` block is returned to the frontend to audit retrieval execution:
```json
{
  "matched_files": ["GDPR_Policy.pdf"],
  "selected_files": ["GDPR_Policy.pdf"],
  "retrieved_chunks_per_file": {
    "GDPR_Policy.pdf": 4
  },
  "total_chunks": 4,
  "retrieval_mode": "filtered"
}
```

---

## Frontend Display Details

### 1. File Source Cards
Attributions are displayed on the frontend as responsive grid cards, showing:
* Filename with matching extension icon.
* A visual **Model Confidence** progress bar, colored dynamically (Green $\ge 80\%$, Amber $\ge 50\%$, Red $< 50\%$).
* Tags indicating the specific sections that matched the query.
* A "View Original" link that opens the corresponding document directly in Google Drive.

### 2. Collapsible Diagnostics Panel
A collapsible monospace container displays raw diagnostic metrics, giving auditors insight into the chunk retrieval counts, retrieval mode, and filter parameters.
