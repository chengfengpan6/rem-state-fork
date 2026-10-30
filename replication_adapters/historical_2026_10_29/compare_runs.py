"""Side-by-side history-level contrasts for two targeted recordings on their common seeds.
Usage: python compare_runs.py <recording A (e.g. Luna)> <recording B (e.g. Claude)> [labelA] [labelB]"""
import sys, json, math, glob, os, statistics as st
A, B = sys.argv[1], sys.argv[2]
la = sys.argv[3] if len(sys.argv) > 3 else "A"; lb = sys.argv[4] if len(sys.argv) > 4 else "B"
ARMS = ["team_P", "team_E", "team_H", "team_R0", "team_R0rep"]

def load(root):
    out = {}
    for f in glob.glob(os.path.join(root, "histories", "*", "attempt_*", "summary.json")):
        s = json.load(open(f))
        if s.get("status") != "completed": continue
        d = {}
        for arm in ARMS:
            prs = s["branches"][arm]["profiles"]
            d[arm] = sum(p["cBR"] for p in prs) / len(prs)
            d[arm + ":Y100"] = next(p["probability"] for p in prs if p["profile_id"] == "Y100")
            d[arm + ":Y011"] = next(p["probability"] for p in prs if p["profile_id"] == "Y011")
        out[str(s["seed"])] = d
    return out

ra, rb = load(A), load(B)
common = sorted(set(ra) & set(rb), key=int)
print(f"{la}: {len(ra)} histories; {lb}: {len(rb)} histories; common: {len(common)}")

def summarize(rows, x, y):
    d = [r[x] - r[y] for r in rows]; n = len(d)
    if n < 2: return f"n={n} mean={d[0]:+.4f}" if d else "n=0"
    m, sd = st.mean(d), st.stdev(d); se = sd / math.sqrt(n)
    return f"n={n:2d} mean={m:+.4f} sd={sd:.4f} ci≈[{m-2.0*se:+.4f},{m+2.0*se:+.4f}] pos={sum(v>0 for v in d)} neg={sum(v<0 for v in d)}"

print("\nContrast            | " + la.ljust(70) + " | " + lb)
for x, y, name in [("team_P", "team_E", "P−E"), ("team_H", "team_E", "H−E"), ("team_H", "team_R0", "H−R0"),
                   ("team_E", "team_R0", "E−R0"), ("team_R0rep", "team_R0", "R0rep−R0")]:
    print(f"{name:19s} | {summarize([ra[s] for s in common], x, y):70s} | {summarize([rb[s] for s in common], x, y)}")
print("\nArm mean cBR        | " + " ".join(f"{a[5:]:>8s}" for a in ARMS))
for lab, r in ((la, ra), (lb, rb)):
    print(f"{lab:19s} | " + " ".join(f"{st.mean(r[s][a] for s in common):8.4f}" for a in ARMS))
print("\nMean team forecast Y100 / Y011")
for lab, r in ((la, ra), (lb, rb)):
    print(f"{lab:19s} | " + " ".join(f"{a[5:]}={st.mean(r[s][a+':Y100'] for s in common):.3f}/{st.mean(r[s][a+':Y011'] for s in common):.3f}" for a in ARMS))
print("\nPer-history P−E:", {s: (round(ra[s]['team_P']-ra[s]['team_E'],3), round(rb[s]['team_P']-rb[s]['team_E'],3)) for s in common})
