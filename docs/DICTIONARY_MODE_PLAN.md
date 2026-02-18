# Dictionary Mode Game Plan (No-AI)

Status: Phase 3 complete (backend + UI integration complete; dictionary data import pending)
Branch: `feature/dictionary-mode-plan`
Owner role: `comms/roles/ARCHITECT.md`

Progress:
- Phase 1 core services implemented (`services/dictionary_loader.py`, `services/dictionary_lookup.py`)
- Phase 1 unit tests added (`tests/test_dictionary_services.py`)
- Phase 2 API route implemented (`routes_dictionary.py`)
- Phase 2 route tests added (`tests/test_dictionary_route.py`)
- Phase 3 reader UI integration implemented (`templates/reader.html`, `static/js/reader.js`, `static/css/reader.css`)
- Full project unit suite passes after Phase 3 changes

## 1. Goal
Add a Cantonese dictionary feature to Reader without breaking existing behavior.

Primary user value:
- Tap text to get useful English definitions for words/phrases.
- Keep current tap-to-read functionality intact via mode toggle.

## 2. Non-Goals (v1)
- No LLM usage for dictionary definitions.
- No automatic learning/retraining pipeline.
- No full linguistic analysis guarantees.
- No major redesign of page architecture.

## 3. Product Decisions Locked
- Dictionary must be local/data-driven (no AI inference for definitions).
- Reader interaction uses a mode toggle:
  - `Read` mode: current behavior (tap plays/reads)
  - `Dictionary` mode: tap looks up definition
- Phrase-level lookup preferred over single-character lookup.
- Keep existing TTS and translation features unchanged.

## 4. Success Criteria
1. Existing Read mode works exactly as before.
2. Dictionary mode returns definitions for common words/phrases in normal news-style text.
3. If no phrase definition is found, user sees graceful fallback (single-character or “No definition found”).
4. UI remains uncluttered and mobile-friendly.
5. Memory/CPU impact stays small for low-resource VPS operation.

## 5. Data Strategy (v1)
## 5.1 Base sources
- CC-CEDICT (broad Chinese dictionary coverage)
- CC-Canto (Cantonese-specific complement)

Why:
- Good quality/coverage tradeoff for a local, no-AI solution.
- Compatible text-dictionary style for manageable ingestion.

## 5.2 Licensing requirements
- Treat dictionary data as licensed artifacts requiring attribution.
- Include explicit attribution and license text in repo docs.
- Keep source/version pinning to avoid ambiguity.

Planned docs addition during implementation:
- `docs/DICTIONARY_DATA_LICENSES.md`

## 6. Technical Architecture
## 6.1 Backend components
1. `services/dictionary_loader.py`
- Parses dictionary source files at startup.
- Builds in-memory lookup indexes.

2. `services/dictionary_lookup.py`
- Performs phrase-first matching using longest-match approach.
- Fallback to single-character lookup if phrase not found.
- Returns candidate definitions and match metadata.

3. `routes_dictionary.py`
- API endpoint for lookup requests.
- Input: full passage text + click offset/index.
- Output: matched span, term, jyutping (if available), definitions.

## 6.2 Frontend components
1. Reader mode toggle (`Read` / `Dictionary`)
2. Click handler branching by mode:
- Read mode -> existing behavior unchanged
- Dictionary mode -> call dictionary endpoint
3. Dictionary result panel under Reader
- Term
- Span highlight
- Definitions list
- “No match” state

## 6.3 Caching & performance
- Preload dictionary once at app start.
- Optional small in-process LRU cache for repeated lookups.
- Keep request payload/response small.

## 7. Segmentation & Matching Plan
Use deterministic local matching (no AI):
1. At click index, attempt longest phrase match around index.
2. Prefer multi-character terms over single-character entries.
3. Use fallback ranking when multiple candidates exist:
- Exact phrase length priority
- Source priority (Cantonese-first entries preferred where possible)
- Frequency/ordering heuristic if available
4. If still ambiguous, show top 2–3 candidates.

## 8. UX Behavior Details
- Default mode remains `Read`.
- Switching to `Dictionary` mode changes tap intent only; no hidden side effects.
- Reader highlights detected term span when definition shown.
- Definition panel updates in place; no modal.
- If lookup fails, show concise feedback and recovery hint.

## 9. Risk Register
1. Segmentation ambiguity
- Mitigation: phrase-first matching + ranked candidates + clear fallback state.

2. License compliance drift
- Mitigation: explicit data source/version/attribution docs and checklists.

3. UI interaction conflicts
- Mitigation: hard mode separation between Read and Dictionary actions.

4. Low-resource VPS constraints
- Mitigation: startup preload, bounded memory structures, conservative indexing.

## 10. Delivery Plan (Phased)
Phase 0: Planning/approval (current)
- Finalize this spec and confirm data sources.

Phase 1: Data ingestion + backend lookup
- Implement loader + lookup service + unit tests.

Phase 2: Dictionary API
- Add endpoint and API tests.

Phase 3: Reader UI integration
- Toggle + dictionary panel + highlight span.

Phase 4: QA + tuning
- Regression pass for Read mode.
- Accuracy tuning on sample passages.
- Performance check on VPS-like constraints.

Phase 5: Documentation
- Update README and deployment/env docs (if new vars/files needed).
- Add dictionary data licensing document.

## 11. Open Decisions Requiring Your Approval
1. Data file storage location in repo:
- Option A: keep raw source files in `data/` (simpler deployment)
- Option B: fetch/build at deploy time (smaller repo, more complexity)

2. Candidate display behavior:
- Option A: show only best match
- Option B: show best + “alternatives” accordion

3. Tone/format of definitions:
- Option A: concise one-line gloss
- Option B: include part-of-speech/extra metadata when present

## 11.1 Decisions Locked (2026-02-17)
1. Data storage strategy: Option A
- Keep dictionary files in-repo.

2. Candidate display behavior: Option B
- Show best match with alternatives collapsed by default.

3. Definition format: Option A
- Concise gloss only for v1.

## 12. Implementation Readiness Checklist
- [x] Scope approved
- [x] Source dictionaries approved
- [x] License handling approved
- [x] UX behavior approved
- [x] Storage strategy approved

---
If approved, next step is Phase 1 implementation on this branch.
