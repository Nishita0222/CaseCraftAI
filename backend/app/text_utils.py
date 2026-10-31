"""Small text / number helpers shared by all agents. Maths uses Decimal (no float drift)."""
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

_SENT_SPLIT = re.compile(r'(?<=[.!?”"])\s+(?=[A-Z“"\'\[(0-9])')
NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
ISO_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
REF_RE = re.compile(r"\[E\d+(?:\s*,\s*E\d+)*\]")


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    return [p.strip() for p in _SENT_SPLIT.split(text) if p.strip()]


def parse_number(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(value))
    if not m:
        return None
    try:
        return Decimal(m.group(0).replace(",", ""))
    except InvalidOperation:
        return None


def fmt_num(d) -> str:
    d = Decimal(d)
    sign = "-" if d < 0 else ""
    s = format(abs(d).normalize(), "f")
    if "." in s:
        i, f = s.split(".")
        return f"{sign}{int(i):,}.{f}"
    return f"{sign}{int(s):,}"


def fmt_val(d, unit: str = "") -> str:
    n = fmt_num(d)
    if unit == "%":
        return f"{n}%"
    if unit in ("$", "€", "£"):
        return f"{unit}{n}"
    return f"{n} {unit}".strip()


def round1(d) -> Decimal:
    return Decimal(d).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def norm_token(tok: str) -> str:
    try:
        return format(Decimal(tok.replace(",", "")).normalize(), "f")
    except InvalidOperation:
        return tok


def numbers_in(text: str) -> set:
    return {norm_token(t) for t in NUM_RE.findall(text or "")}
