"""Item order within one placement, shared by the generators that render (conformance/README.md, Running a case).

Items go by id in UTF-16 code units (Ordering), except interaction.history, whose turns go in the order they were
said: by freshness, compared as instants at full precision, then by id (R-7).
"""
import calendar, re
from fractions import Fraction

U16 = lambda s: s.encode("utf-16-be")  # strings order by UTF-16 code units (conformance/README.md, Ordering)
INSTANT = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]+))?(?:[Zz]|([+-])([0-9]{2}):([0-9]{2}))")


def instant(text):
    """Seconds since the epoch as an exact fraction, so instants compare at full precision (R-2)."""
    y, mo, d, h, mi, sec, frac, sign, oh, om = INSTANT.fullmatch(text).groups()
    seconds = calendar.timegm((int(y), int(mo), int(d), int(h), int(mi), int(sec)))
    offset = (int(oh) * 3600 + int(om) * 60) * (1 if sign == "+" else -1) if sign else 0
    return seconds - offset + (Fraction(int(frac), 10 ** len(frac)) if frac else 0)


def placed(slot, entries, item=lambda entry: entry):
    """entries in the order a renderer places them within one placement of slot; item(entry) gives the entry's item."""
    if slot == "interaction.history":
        return sorted(entries, key=lambda e: (instant(item(e)["freshness"]), U16(item(e)["id"])))
    return sorted(entries, key=lambda e: U16(item(e)["id"]))
