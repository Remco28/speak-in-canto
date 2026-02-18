from __future__ import annotations

from dataclasses import dataclass

from services.dictionary_loader import DictionaryEntry


@dataclass(slots=True)
class DictionaryCandidate:
    term: str
    start: int
    end: int
    definitions: tuple[str, ...]
    source: str
    jyutping: str = ""


@dataclass(slots=True)
class DictionaryLookupResult:
    best: DictionaryCandidate | None
    alternatives: tuple[DictionaryCandidate, ...]


class DictionaryLookupService:
    def __init__(self, entries_by_term: dict[str, list[DictionaryEntry]]) -> None:
        self.entries_by_term = entries_by_term
        lengths = {len(term) for term in entries_by_term.keys() if term}
        self.lengths_desc = sorted(lengths, reverse=True)

    def lookup_at(self, text: str, index: int, max_alternatives: int = 3) -> DictionaryLookupResult:
        if not text or index < 0 or index >= len(text):
            return DictionaryLookupResult(best=None, alternatives=())

        candidates = self._candidates_for_index(text, index)
        if not candidates:
            return DictionaryLookupResult(best=None, alternatives=())

        ranked = sorted(candidates, key=lambda c: self._score(c, index))
        best = ranked[0]

        alternatives: list[DictionaryCandidate] = []
        for candidate in ranked[1:]:
            if candidate.term == best.term and candidate.start == best.start and candidate.end == best.end:
                continue
            alternatives.append(candidate)
            if len(alternatives) >= max(0, max_alternatives):
                break

        return DictionaryLookupResult(best=best, alternatives=tuple(alternatives))

    def _candidates_for_index(self, text: str, index: int) -> list[DictionaryCandidate]:
        found: list[DictionaryCandidate] = []
        seen: set[tuple[str, int, int, str]] = set()

        for start in range(index, -1, -1):
            max_span = len(text) - start
            for length in self.lengths_desc:
                if length > max_span:
                    continue
                end = start + length
                if not (start <= index < end):
                    continue

                term = text[start:end]
                entries = self.entries_by_term.get(term)
                if not entries:
                    continue

                for entry in entries:
                    key = (term, start, end, entry.source)
                    if key in seen:
                        continue
                    seen.add(key)
                    found.append(
                        DictionaryCandidate(
                            term=term,
                            start=start,
                            end=end,
                            definitions=entry.definitions,
                            source=entry.source,
                            jyutping=entry.jyutping,
                        )
                    )

        return found

    def _score(self, candidate: DictionaryCandidate, index: int) -> tuple[int, float, int, str]:
        length = candidate.end - candidate.start
        midpoint = (candidate.start + candidate.end - 1) / 2.0
        center_distance = abs(midpoint - index)

        # Prefer longer phrase matches, then click-centered matches, then earlier span.
        return (-length, center_distance, candidate.start, candidate.source)
