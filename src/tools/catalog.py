from fastmcp.tools import tool
from toon_format import encode
from src.db.connection import get_supabase


# List Programs
@tool(annotations={"readOnlyHint": True}, 
      description="Discover valid program identifiers, program names, and schools in the course catalog. " \
      "Call before filtering courses by program. Returns TOON.")
def list_programs() -> str:
    """
    List Programs, Program_names, and schools for discovery
    Returns in TOON format
    """
    supabase = get_supabase()
    programs = {}
    offset = 0
    page_size = 1000

    while True:
        rows = (
            supabase.table("courses")
            .select("program,program_name,school")
            .order("code")
            .range(offset, offset + page_size - 1)
            .execute()
            .data
        )
        if not rows:
            break

        for row in rows:
            if not row["program"] or not row["program"].strip():
                continue
            key = (row["program"], row["program_name"], row["school"])
            programs[key] = {
                "program": row["program"],
                "program_name": row["program_name"],
                "school": row["school"],
            }

        # Advance by the actual count even if the server caps pages below 1000.
        offset += len(rows)

    sorted_programs = sorted(
        programs.values(),
        key=lambda row: (row["program"], row["program_name"] or "", row["school"] or ""),
    )

    return encode({"programs": sorted_programs})

#Get Course Codes
@tool(
    annotations={"readOnlyHint": True},
    description="List course codes filtered by program, program_name, and/or school. "
    "Provide at least one non-empty filter; supplied filters must all match exactly. "
    "Use list_programs to discover valid filter values. Returns sorted course codes in TOON format.",
)
def course_codes(
    program: str | None = None,
    school: str | None = None,
    program_name: str | None = None,
) -> str:
    """Return distinct, sorted course codes matching all supplied filters as TOON."""
    filters = {}
    for field, value in {
        "program": program,
        "program_name": program_name,
        "school": school,
    }.items():
        if value is not None:
            if not value.strip():
                raise ValueError(f"{field} must not be blank.")
            filters[field] = value.strip()

    if not filters:
        raise ValueError("Provide at least one of program, program_name, or school.")

    supabase = get_supabase()
    codes = set()
    offset = 0
    page_size = 1000
    while True:
        query = supabase.table("courses").select("code")
        for field, value in filters.items():
            query = query.eq(field, value)

        rows = (
            query.order("code")
            .range(offset, offset + page_size - 1)
            .execute()
            .data
        )
        if not rows:
            break

        codes.update(row["code"] for row in rows if row["code"] and row["code"].strip())
        # Continue even when the server caps pages below the requested size.
        offset += len(rows)

    return encode({"course_codes": sorted(codes)})


# Get course details
@tool(
    annotations={"readOnlyHint": True},
    description="Retrieve or compare one or more courses, including program, school, metadata, and "
    "prerequisites. Input codes ignore case and normalize whitespace. Metadata fields are aligned "
    "with null for missing values. Unknown codes are listed in unmatched_codes. Returns sorted TOON.",
)
def course_details(codes: list[str]) -> str:
    """Retrieve course details with consistent fields for single or multiple courses."""
    if not codes:
        raise ValueError("Provide at least one course code.")
    if any(not isinstance(code, str) or not code.strip() for code in codes):
        raise ValueError("Each course code must be a non-empty string.")

    supabase = get_supabase()
    requested_codes = sorted({" ".join(code.upper().split()) for code in codes})
    courses = []
    offset = 0
    page_size = 1000
    while True:
        rows = (
            supabase.table("courses")
            .select("code,program,program_name,school,metadata,prerequisites")
            .in_("code", requested_codes)
            .order("code")
            .range(offset, offset + page_size - 1)
            .execute()
            .data
        )
        if not rows:
            break

        courses.extend(rows)
        # Continue even when the server caps pages below the requested size.
        offset += len(rows)

    fields = sorted({key for row in courses if isinstance(row.get("metadata"), dict)
                     for key in row["metadata"]})
    results = []
    for row in sorted(courses, key=lambda row: row["code"]):
        metadata = row.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        results.append({**row, "metadata": {key: metadata.get(key) for key in fields}})
    found = {" ".join(row["code"].upper().split()) for row in courses}
    return encode({"courses": results,
                   "unmatched_codes": sorted(set(requested_codes) - found)})


@tool(
    annotations={"readOnlyHint": True},
    description="Deprecated alias for course_details; keeps compatibility for compare_courses clients.",
)
def compare_courses(codes: list[str]) -> str:
    return course_details(codes)


# Search courses
