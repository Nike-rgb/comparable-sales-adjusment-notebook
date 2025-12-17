from __future__ import annotations
from typing import Optional

Q_MAP = {
    'custom': 3, 'luxury': 2, 'high': 3, 'average': 5, 'typical': 5, 'economy': 6,
    'standard': 5, 'builder grade': 5, 'basic': 6, 'existing': 5, 'updated': 4, 'excellent': 2
}
C_MAP = {
    'new': 2, 'like new': 2, 'renovated': 3, 'updated': 3, 'average': 4, 'typical': 4,
    'outdated': 5, 'fair': 5, 'poor': 6, 'as-is': 6, 'unknown': 4, 'existing': 4
}

def parse_q_int(text: Optional[str]) -> Optional[int]:
    if text is None:
        return None
    s = str(text).strip().upper()
    if s.startswith('Q') and s[1:].isdigit():
        return int(s[1:])
    s2 = s.lower()
    for k,v in Q_MAP.items():
        if k in s2:
            return v
    return None

def parse_c_int(text: Optional[str]) -> Optional[int]:
    if text is None:
        return None
    s = str(text).strip().upper()
    if s.startswith('C') and s[1:].isdigit():
        return int(s[1:])
    s2 = s.lower()
    for k,v in C_MAP.items():
        if k in s2:
            return v
    return None
