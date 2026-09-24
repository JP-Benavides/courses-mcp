"""Catalog discovery and evidence-based advising, without inferring eligibility."""

import math
import re
from collections import Counter

from fastmcp.tools import tool
from toon_format import encode

from src.db.connection import get_supabase


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string.")
    return value.strip()


def _limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer between 1 and 100.")


def _catalog(**filters) -> list[dict]:
    client = get_supabase()
    rows = []
    while True:
        query = client.table("courses").select("code,program,program_name,school,metadata")
        for field, value in filters.items():
            query = query.eq(field, value)
        page = query.order("code").range(len(rows), len(rows) + 999).execute().data
        if not page:
            return rows
        rows.extend(page)


def _metadata(row: dict) -> dict:
    value = row.get("metadata")
    return value if isinstance(value, dict) else {}


def _normalize(value: str) -> str:
    return " ".join(value.upper().split())


def _find(rows: list[dict], code: str) -> dict:
    matches = [row for row in rows if _normalize(row.get("code") or "") == _normalize(code)]
    if len(matches) != 1:
        raise ValueError(f"Expected one catalog entry for {code}; found {len(matches)}.")
    return matches[0]


def _tokens(text: str) -> Counter:
    stop = {"the", "and", "for", "with", "this", "that", "from", "will", "are",
            "course", "students", "their", "into", "has", "have", "can", "its"}
    return Counter(word for word in re.findall(r"\w+", text.casefold())
                   if len(word) > 2 and word not in stop)


def _search_text(row: dict) -> str:
    meta = _metadata(row)
    values = [row.get(key) for key in ("code", "program", "program_name", "school")]
    values += [meta.get(key) for key in ("title", "name", "description")]
    return " ".join(value for value in values if isinstance(value, str))


def _evidence(row: dict, rows: list[dict]) -> dict:
    meta = _metadata(row)
    explicit = {key: meta[key] for key in ("prerequisites", "prerequisite", "corequisites")
                if key in meta}
    description = meta.get("description")
    description = description if isinstance(description, str) else ""
    # Include full source text: sentence splitting can lose alternatives or conditions.
    source = " ".join([description, *(str(value) for value in explicit.values())])
    normalized = _normalize(source)
    mentions = sorted({other["code"] for other in rows if other.get("code")
                       and _normalize(other["code"]) != _normalize(row["code"])
                       and re.search(r"(?<![\w-])" + re.escape(_normalize(other["code"]))
                                     + r"(?![\w-])", normalized)})
    return {"status": "unverified", "prerequisite_fields": explicit,
            "description": description, "course_url": meta.get("courseUrl"),
            "referenced_codes": mentions,
            "has_requirement_language": bool(explicit) or bool(re.search(
                r"prerequisite|co-?requisite|placement|permission|consent", source, re.I)),
            "note": "Course references are not necessarily prerequisites. Review the source for "
                    "alternatives, grades, placement, permission, and other conditions. "
                    "Missing prerequisite data does not establish eligibility."}


@tool(annotations={"readOnlyHint": True}, description="Search catalog codes, program names, "
      "schools, titles and descriptions by case-insensitive words. All query words must match. "
      "Optional program and school filters match exactly. Returns ranked TOON results.")
def search_courses(query: str, program: str | None = None,
                   school: str | None = None, limit: int = 20) -> str:
    query = _text(query, "query")
    _limit(limit)
    filters = {key: _text(value, key) for key, value in
               {"program": program, "school": school}.items() if value is not None}
    terms = query.casefold().split()
    matches = []
    for row in _catalog(**filters):
        text = _search_text(row).casefold()
        if all(term in text for term in terms):
            score = sum(text.count(term) for term in terms)
            matches.append((score, row))
    matches.sort(key=lambda item: (-item[0], item[1]["code"]))
    return encode({"total_matches": len(matches), "courses": [row for _, row in matches[:limit]]})


@tool(annotations={"readOnlyHint": True}, description="Get a program's course count, schools, "
      "names and paginated course summaries. Program matches exactly. Returns TOON.")
def program_overview(program: str, limit: int = 20, offset: int = 0) -> str:
    program = _text(program, "program")
    _limit(limit)
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("offset must be a non-negative integer.")
    rows = _catalog(program=program)
    return encode({"program": program, "course_count": len(rows),
                   "program_names": sorted({r["program_name"] for r in rows if r.get("program_name")}),
                   "schools": sorted({r["school"] for r in rows if r.get("school")}),
                   "courses": rows[offset:offset + limit],
                   "next_offset": offset + limit if offset + limit < len(rows) else None})


@tool(annotations={"readOnlyHint": True}, description="Compare available metadata for up to 20 "
      "course codes using consistent fields. Missing values are null; unmatched codes are explicit. Returns TOON.")
def compare_courses(codes: list[str]) -> str:
    if not 1 <= len(codes) <= 20:
        raise ValueError("Provide between 1 and 20 course codes.")
    requested = {_normalize(_text(code, "code")) for code in codes}
    rows = [row for row in _catalog() if _normalize(row.get("code") or "") in requested]
    fields = sorted({key for row in rows for key in _metadata(row)})
    return encode({"courses": [{**row, "metadata": {key: _metadata(row).get(key) for key in fields}}
                                for row in rows],
                   "unmatched_codes": sorted(requested - {_normalize(row["code"]) for row in rows})})


@tool(annotations={"readOnlyHint": True}, description="Find courses with similar descriptions "
      "using word-frequency cosine similarity. Scores indicate text overlap, not equivalency or credit transfer. Returns TOON.")
def find_similar_courses(code: str, limit: int = 10) -> str:
    code = _text(code, "code")
    _limit(limit)
    rows = _catalog()
    source = _find(rows, code)
    description = _metadata(source).get("description")
    vector = _tokens(description if isinstance(description, str) else "")
    norm = math.sqrt(sum(n * n for n in vector.values()))
    matches = []
    for row in rows:
        if row["code"] == source["code"]:
            continue
        description = _metadata(row).get("description")
        other = _tokens(description if isinstance(description, str) else "")
        denominator = norm * math.sqrt(sum(n * n for n in other.values()))
        score = sum(n * other[word] for word, n in vector.items()) / denominator if denominator else 0
        if score > 0:
            matches.append({"similarity": round(score, 6), **row})
    matches.sort(key=lambda row: (-row["similarity"], row["code"]))
    return encode({"code": source["code"], "description_available": bool(vector),
                   "courses": matches[:limit]})


@tool(annotations={"readOnlyHint": True}, description="Retrieve prerequisite evidence and mark "
      "which referenced courses are in the supplied completed list. Eligibility stays unverified: "
      "prose may include alternatives and non-course conditions. Returns TOON.")
def check_prerequisites(code: str, completed_codes: list[str]) -> str:
    code = _text(code, "code")
    completed = {_normalize(_text(value, "completed_code")) for value in completed_codes}
    rows = _catalog()
    row = _find(rows, code)
    evidence = _evidence(row, rows)
    return encode({"code": row["code"], **evidence,
                   "completed_references": [c for c in evidence["referenced_codes"] if _normalize(c) in completed],
                   "not_completed_references": [c for c in evidence["referenced_codes"] if _normalize(c) not in completed]})


@tool(annotations={"readOnlyHint": True}, description="Find possible follow-on courses whose "
      "requirement-related descriptions or fields mention a course. These are candidates, not "
      "confirmed unlocks; source evidence and eligibility limitations are returned in TOON.")
def courses_unlocked_by(code: str, limit: int = 20) -> str:
    code = _text(code, "code")
    _limit(limit)
    rows = _catalog()
    source = _find(rows, code)
    candidates = []
    for row in rows:
        if row["code"] == source["code"]:
            continue
        evidence = _evidence(row, [source])
        if evidence["referenced_codes"] and evidence["has_requirement_language"]:
            candidates.append({"code": row["code"], **evidence})
    return encode({"code": source["code"], "total_candidates": len(candidates),
                   "candidates": candidates[:limit]})
