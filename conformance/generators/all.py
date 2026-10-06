"""Regenerates every generated case, then the rejections and the registry, which read some of those cases.

    python3 conformance/generators/all.py

Each generator writes its own cases; run alone, one regenerates only those. Standard library only, like the generators.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# The case generators first, in any order; rejections.py reads fixture-three-slot, messages-render and blocks-render,
# and registry.py reads four cases' route policies and the examples.
CASES = ["admission-reasons", "capability-kind", "conflicts", "dedupe", "diversity", "doubles", "fitting", "history", "messages", "route-slots", "supersede"]
ORDER = CASES + ["rejections", "registry"]

if __name__ == "__main__":
    for name in ORDER:
        subprocess.run([sys.executable, "-B", os.path.join(HERE, f"{name}.py")], check=True, stdout=subprocess.DEVNULL)
    print(f"regenerated {len(ORDER)} generators' output")
