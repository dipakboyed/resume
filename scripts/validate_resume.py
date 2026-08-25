from __future__ import annotations

import argparse
from datetime import date
import re
import sys
from pathlib import Path
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "_data" / "resume.yml"
SCHEMA_PATH = ROOT / "schema" / "resume.schema.json"
REQUIRED_HEADINGS = (
    "Executive Summary",
    "Core Skills",
    "Professional Experience",
    "Education and Certifications",
    "Patents and Selected Publication",
)
FORBIDDEN_CODEPOINTS = tuple(chr(value) for value in range(0xFB00, 0xFB07)) + ("\u00ad", "\ufffd")


def normalize(value: str) -> str:
    return " ".join(value.split()).casefold()


def load_data() -> dict[str, Any]:
    import json

    data = yaml.safe_load(DATA_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.absolute_path))
    if errors:
        details = "\n".join(
            f"- {'/'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValueError(f"Resume data does not match the schema:\n{details}")
    return data


def required_source_text(data: dict[str, Any]) -> Iterable[str]:
    yield data["name"]
    yield data["headline"]
    yield data["summary"]
    for contact in data["contacts"]:
        yield contact["label"]
    for skill in data["skills"]:
        yield skill["category"]
        yield skill["details"]
    for role in data["experience"]:
        yield role["title"]
        yield role["employer"]
        yield role["organization"]
        yield role["location"]
        yield role["dates"]
        yield from role["bullets"]
    for education in data["education"]:
        yield education["degree"]
        yield education["institution"]
        yield str(education["year"])
    for certification in data["certifications"]:
        yield certification["name"]
        yield str(certification["year"])
    for publication in data["publications"]:
        yield publication["type"]
        yield publication["title"]
        if publication.get("collaborators"):
            yield publication["collaborators"]
        if publication.get("venue"):
            yield publication["venue"]


def validate_source(data: dict[str, Any]) -> None:
    pending = [
        publication
        for publication in data["publications"]
        if publication["type"].casefold() == "patent pending"
    ]
    if not pending or pending[0]["title"] != "Rubric Engine(s) for Generation of Assessment Frameworks":
        raise ValueError("The pending Rubric Engine patent must appear in the publication data.")

    expected_degrees = {
        "University of Washington, Seattle": 2008,
        "The University of Texas at Austin": 2004,
    }
    actual_degrees = {
        education["institution"]: education["year"] for education in data["education"]
    }
    if actual_degrees != expected_degrees:
        raise ValueError(f"Education years changed: expected {expected_degrees}, got {actual_degrees}.")

    months = {
        month: index
        for index, month in enumerate(
            (
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ),
            start=1,
        )
    }
    full_date = re.compile(
        rf"^({'|'.join(months)}) (\d{{4}}) - (({'|'.join(months)}) (\d{{4}})|Present)$"
    )
    year_range = re.compile(r"^\d{4} - \d{4}$")
    role_identities: set[tuple[str, str, str, str]] = set()
    for role in data["experience"]:
        identity = (role["employer"], role["title"], role["organization"], role["dates"])
        if identity in role_identities:
            raise ValueError(f"Duplicate experience entry: {identity}")
        role_identities.add(identity)

        full_match = full_date.fullmatch(role["dates"])
        year_match = year_range.fullmatch(role["dates"])
        if not (full_match or year_match):
            raise ValueError(f"ATS date format is invalid for {role['title']}: {role['dates']}")
        if full_match and full_match.group(3) != "Present":
            start = date(int(full_match.group(2)), months[full_match.group(1)], 1)
            end = date(int(full_match.group(5)), months[full_match.group(4)], 1)
            if end < start:
                raise ValueError(f"Experience dates are reversed for {role['title']}: {role['dates']}")
        if year_match:
            start_year, end_year = (int(value) for value in role["dates"].split(" - "))
            if end_year < start_year:
                raise ValueError(f"Experience years are reversed for {role['title']}: {role['dates']}")


def dereference(value: Any) -> Any:
    return value.get_object() if hasattr(value, "get_object") else value


def validate_extracted_text(data: dict[str, Any], text: str, extractor: str) -> None:
    normalized_text = normalize(text)
    if not normalized_text.startswith(normalize(data["name"])):
        raise ValueError(f"{extractor} text does not start with the candidate name.")

    missing = [value for value in required_source_text(data) if normalize(value) not in normalized_text]
    if missing:
        missing_text = "\n".join(f"- {value}" for value in missing)
        raise ValueError(f"{extractor} omitted canonical resume text:\n{missing_text}")

    positions = [normalized_text.find(normalize(heading)) for heading in REQUIRED_HEADINGS]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise ValueError(f"{extractor} section headings are missing or appear out of order.")

    forbidden = [f"U+{ord(character):04X}" for character in FORBIDDEN_CODEPOINTS if character in text]
    if forbidden:
        raise ValueError(f"{extractor} contains forbidden code points: {', '.join(forbidden)}")


def validate_pdf(
    data: dict[str, Any],
    pdf_path: Path,
    poppler_text_path: Path | None,
    poppler_layout_path: Path | None,
) -> None:
    reader = PdfReader(pdf_path)
    if len(reader.pages) != 2:
        raise ValueError(f"The resume must contain exactly two pages, but it contains {len(reader.pages)}.")

    metadata = reader.metadata
    if not metadata or metadata.title != f"{data['name']} - Resume":
        raise ValueError("The PDF title metadata is missing or incorrect.")

    root = dereference(reader.trailer["/Root"])
    if root.get("/Lang") != "en-US":
        raise ValueError("The PDF language must be en-US.")
    mark_info = dereference(root.get("/MarkInfo", {}))
    if not mark_info.get("/Marked"):
        raise ValueError("The PDF does not declare tagged content.")

    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    validate_extracted_text(data, text, "pypdf extraction")

    annotations = sum(len(page.get("/Annots", [])) for page in reader.pages)
    if annotations < len(data["contacts"]):
        raise ValueError("The PDF does not contain all contact link annotations.")

    if not reader.outline:
        raise ValueError("The PDF does not contain heading bookmarks.")

    if bool(poppler_text_path) != bool(poppler_layout_path):
        raise ValueError("Both Poppler extraction files must be supplied together.")
    if poppler_text_path and poppler_layout_path:
        validate_extracted_text(
            data,
            poppler_text_path.read_text(encoding="utf-8"),
            "Poppler default extraction",
        )
        validate_extracted_text(
            data,
            poppler_layout_path.read_text(encoding="utf-8"),
            "Poppler layout extraction",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate canonical resume data and PDF output.")
    parser.add_argument("--pdf", type=Path, help="Generated PDF to validate.")
    parser.add_argument("--poppler-text", type=Path, help="Default pdftotext output.")
    parser.add_argument("--poppler-layout", type=Path, help="pdftotext -layout output.")
    args = parser.parse_args()

    try:
        data = load_data()
        validate_source(data)
        if args.pdf:
            validate_pdf(data, args.pdf, args.poppler_text, args.poppler_layout)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    scope = "source and PDF" if args.pdf else "source"
    print(f"Resume {scope} contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
