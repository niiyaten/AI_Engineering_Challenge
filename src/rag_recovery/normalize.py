from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

_CORP = re.compile(r"株式会社|医療法人社団|合同会社|有限会社")
_SPACE = re.compile(r"[\s_\-・･/\\（）()【】\[\]「」『』:：]+")


def nfkc(text: object) -> str:
    return unicodedata.normalize("NFKC", str(text or ""))


def norm(text: object) -> str:
    value = nfkc(text).lower()
    value = _CORP.sub("", value)
    return _SPACE.sub("", value)


def tokens(text: object, *, min_len: int = 2) -> list[str]:
    value = nfkc(text).lower()
    parts = re.findall(r"[a-z][a-z0-9_.-]*|\d+(?:\.\d+)?|[一-龥ぁ-んァ-ヶー]+", value)
    out: list[str] = []
    for part in parts:
        if len(part) >= min_len and part not in out:
            out.append(part)
    return out


def overlap_score(a: object, b: object) -> float:
    aa, bb = set(tokens(a)), set(tokens(b))
    if not aa or not bb:
        na, nb = norm(a), norm(b)
        return 1.0 if na and (na in nb or nb in na) else 0.0
    return len(aa & bb) / len(aa | bb)


def unique_nonempty(values: Iterable[object]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = nfkc(value).strip()
        key = norm(text)
        if text and key not in seen:
            seen.add(key)
            out.append(text)
    return out
