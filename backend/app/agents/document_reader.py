"""Agent 1 - Document Reader: PDF/DOCX/XLSX/EML -> citable evidence items (E001, E002 ...)."""
from pathlib import Path

from ..extractors import extract_document
from ..text_utils import split_sentences
from .common import tag_text


def run(state):
    evidence, warnings, docs = [], [], []
    n = 0
    for f in state["files"]:
        try:
            chunks, warns = extract_document(Path(f["path"]))
        except Exception as e:  # a corrupt file must not stop the pipeline
            warnings.append(f"{f['filename']}: could not be read ({e})")
            continue
        warnings += [f"{f['filename']}: {w}" for w in warns]
        docs.append({"filename": f["filename"], "kind": f["kind"], "chunks": len(chunks)})
        for ch in chunks:
            pieces = [ch["text"]] if ch.get("atomic") else split_sentences(ch["text"])
            for s in pieces:
                s = s.strip()
                if len(s) < 6:
                    continue
                n += 1
                evidence.append({
                    "ref": f"E{n:03d}", "doc": f["filename"], "doc_kind": f["kind"],
                    "location": ch["location"], "text": s, "date": ch.get("date"),
                    "row": ch.get("row"), "kind_hint": ch.get("kind_hint"),
                    "metadata": bool(ch.get("metadata")), "people": ch.get("people", []),
                    "tags": tag_text(s)})
    if not evidence:
        warnings.append("No readable evidence found - upload at least one project document.")
    return ({"evidence": evidence, "warnings": warnings, "documents": docs},
            f"Read {len(docs)} document(s) -> {len(evidence)} evidence items")
