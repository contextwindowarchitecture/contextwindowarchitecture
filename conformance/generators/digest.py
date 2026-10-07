"""context.snapshot_digest as conformance/README.md, Snapshot digest defines it: normalize, then
take the SHA-256 of the RFC 8785 serialization. Imported by the generators; run directly, it
prints the digest of each case's snapshot.json."""
import copy, decimal, hashlib, json, math, os, re, sys

NONBLANK = re.compile(r"[^\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]")
U16 = lambda s: s.encode("utf-16-be")


def es_number(value):
    """ECMAScript Number::toString, which RFC 8785 uses: repr gives the shortest round-trip digits,
    and ECMAScript decides where the point goes. It writes 0.00001 where repr writes 1e-05."""
    sign, raw, exponent = decimal.Decimal(repr(value)).as_tuple()
    n = exponent + len(raw)  # value = 0.digits × 10^n
    digits = "".join(map(str, raw)).rstrip("0")
    k = len(digits)
    text = (digits + "0" * (n - k) if k <= n <= 21
            else digits[:n] + "." + digits[n:] if 0 < n <= 21
            else "0." + "0" * -n + digits if -6 < n <= 0
            else (digits[0] + ("." + digits[1:] if k > 1 else "") + f"e{'+' if n > 1 else '-'}{abs(n - 1)}"))
    return ("-" if sign else "") + text


def jcs(value):
    """RFC 8785 for the JSON a snapshot can hold."""
    if value is None or isinstance(value, bool):
        return json.dumps(value)
    if isinstance(value, int):
        if abs(value) <= 2 ** 53:
            return str(value)
        value = float(value)  # RFC 8785 numbers are doubles; beyond 2^53 an integer rounds as JavaScript rounds it
    if isinstance(value, float):
        assert math.isfinite(value)
        # Up to 2^53 a whole double's exact value is its shortest digits. Beyond, ECMAScript writes the shortest
        # round-trip digits and pads with zeros: 12345678901234567168.0 is 12345678901234567000.
        if value == int(value) and abs(value) <= 2 ** 53:
            return str(int(value))
        return es_number(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(jcs(v) for v in value) + "]"
    return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + jcs(value[k]) for k in sorted(value, key=U16)) + "}"


def usable(item):
    return isinstance(item, dict) and isinstance(item.get("id"), str) and bool(NONBLANK.search(item["id"]))


def normalize(snapshot):
    s = copy.deepcopy(snapshot)
    for batch in s["batches"]:
        named = sorted((i for i in batch["items"] if usable(i)), key=lambda i: (U16(i["id"]), jcs(i).encode()))
        batch["items"] = named + [i for i in batch["items"] if not usable(i)]
        batch["excluded"].sort(key=lambda r: (U16(r["item_id"]), jcs(r).encode()))
    s["batches"].sort(key=lambda b: U16(b["producer"]["id"]))
    s["conflicts"].sort(key=lambda g: U16(g["id"]))
    for group in s["conflicts"]:
        group["items"].sort(key=U16)
    return s


def snapshot_digest(snapshot):
    return hashlib.sha256(jcs(normalize(snapshot)).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    web = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    cases = os.path.join(web, "conformance/cases")
    for name in sorted(os.listdir(cases)):
        print(name, snapshot_digest(json.load(open(os.path.join(cases, name, "snapshot.json")))))
