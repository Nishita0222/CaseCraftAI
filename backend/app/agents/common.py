"""Keyword rules shared by agents. Deterministic regexes: no model can 'invent' a fact here."""
import re

SCOPE_RE = re.compile(
    r"scope change|change request|change order|\bCR-\d+|out of scope|de-?scop|additional requirement|"
    r"added to (?:the )?scope|scope extension|revised scope|(?:extended|expanded|reduced) the scope|"
    r"scope (?:was|has been) (?:extended|expanded|reduced|revised|changed)|new requirement", re.I)
MILESTONE_RE = re.compile(
    r"kick-?off|go-?live|launched|completed|delivered|deployed|signed|milestone|commenced|hand-?over|"
    r"pilot|roll-?out|rolled out|acceptance|phase \d|started", re.I)
NDA_RE = re.compile(
    r"confidential|non-?disclosure|\bNDA\b|not\s+(?:be\s+)?disclosed|do\s+not\s+(?:share|distribute|disclose)|"
    r"not\s+for\s+(?:publication|public)|internal\s+only|proprietary|"
    r"(?:must|may|should|shall)\s+not\s+be\s+(?:named|shared|published|disclosed)", re.I)
CONTEXT_RE = re.compile(r"\b(objective|goal|aim|purpose)\b|engagement is to|project (?:was|is) to", re.I)
QUOTE_VERB = r"(?:said|says|noted|stated|commented|added|shared|told)"


def tag_text(text: str) -> list:
    tags = []
    if SCOPE_RE.search(text):
        tags.append("scope")
    if MILESTONE_RE.search(text):
        tags.append("milestone")
    if NDA_RE.search(text):
        tags.append("restricted")
    if CONTEXT_RE.search(text):
        tags.append("context")
    if re.search(r"[“\"][^”\"]{20,}[”\"]", text):
        tags.append("quote")
    return tags
