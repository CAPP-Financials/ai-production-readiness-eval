"""Turn AI-system evaluation module results into one verdict and report.

Rules live in ../09-aggregation-and-report.md; thresholds in ../01-intake-and-thresholds.md
(parsed directly, so that markdown stays the single source of truth).

Usage:
  python aggregate.py check    <profile.json>
  python aggregate.py report   <profile.json> <results_dir> <out.md>
  python aggregate.py lint
  python aggregate.py selftest
"""
import json
import math
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
# works both as repo layout (tools/ beside playbooks/) and as a flat folder (tools/ inside it)
DOCS = HERE.parent / "playbooks" if (HERE.parent / "playbooks").is_dir() else HERE.parent
REGISTRY = DOCS / "01-intake-and-thresholds.md"
MODULE_FILES = {"M1": "m1-output-quality.md", "M2": "m2-rag-pipeline.md", "M3": "m3-agentic-workflow.md",
                "M4": "m4-safety-and-trust.md", "M5": "m5-operations-and-production-resilience.md",
                "M6": "m6-drift-and-observability.md", "M7": "m7-business-value-and-requirements.md"}
TIERS = ["low", "standard", "high", "regulated"]
MODULES = {
    "M1": "Output quality", "M2": "RAG pipeline", "M3": "Agentic workflow",
    "M4": "Safety and trust", "M5": "Operations and production resilience",
    "M6": "Drift and observability", "M7": "Business value and requirements fit",
}
PREFIX = {"OQ": "M1", "RAG": "M2", "AGT": "M3", "SAF": "M4", "OPS": "M5", "DRF": "M6", "BIZ": "M7"}
MODULE_FLAG = {"M2": "has_rag", "M3": "is_agentic"}
GRADES = ["E0", "E1", "E2", "E3", "E4"]
POINTS = {"PASS": 100, "WARN": 60, "FAIL": 0, "NOT_TESTED": 0,
          "DESIGN_OK": 100, "DESIGN_PARTIAL": 50, "DESIGN_ABSENT": 0}
CRIT_W = {"blocker": 3, "major": 2, "minor": 1}
RANK = ["NOT READY", "PILOT-ONLY", "CONDITIONAL", "PRODUCTION-READY"]
Z = 1.96


def num(s):
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    if s.upper() in ("ASK", "PASS"):
        return s.upper()
    try:
        return float(s[:-1]) / 100 if s.endswith("%") else float(s)
    except ValueError:
        return s  # text params such as E3 or a list of regions


def parse_registry(path=REGISTRY):
    metrics, params = {}, {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        key = cells[0]
        if re.fullmatch(r"[A-Z]+-\d\d", key) and len(cells) == 9:
            th = {}
            for tier, cell in zip(TIERS, cells[5:9]):
                a, b = (cell.split("/") + [cell])[:2]
                th[tier] = (num(a), num(b))
            metrics[key] = dict(name=cells[1], dir=cells[2], crit=cells[3], applies=cells[4], th=th,
                                 pct=any("%" in c for c in cells[5:9]))
        elif re.fullmatch(r"[A-Z]+_[A-Z0-9_]+", key) and len(cells) == 7:
            params[key] = dict(meaning=cells[1], used=cells[2], th=dict(zip(TIERS, cells[3:7])))
    return metrics, params


def wilson(k, n):
    p = k / n
    d = 1 + Z * Z / n
    c = p + Z * Z / (2 * n)
    m = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    return max(0.0, (c - m) / d), min(1.0, (c + m) / d)


def resolve(profile, metrics, params):
    tier = profile["risk_tier"]
    flags, ov = profile.get("flags", {}), profile.get("overrides", {})
    P = {k: num(profile.get("params", {}).get(k, v["th"][tier])) for k, v in params.items()}
    M = {}
    for mid, m in metrics.items():
        mod = PREFIX[mid.split("-")[0]]
        on = flags.get(MODULE_FLAG[mod], False) if mod in MODULE_FLAG else True
        applies = m["applies"] == "always" or flags.get(m["applies"], False)
        t, f = m["th"][tier]
        o = ov.get(mid, {})
        M[mid] = dict(m, id=mid, module=mod, applicable=bool(on and applies and not o.get("na")),
                      target=num(o.get("target", t)), floor=num(o.get("floor", f)),
                      crit=o.get("criticality", m["crit"]))
    return P, M


def missing_placeholders(profile, metrics, params):
    P, M = resolve(profile, metrics, params)
    active = {m["module"] for m in M.values() if m["applicable"]}
    out = [k for k, m in M.items() if m["applicable"] and "ASK" in (m["target"], m["floor"])]
    out += [k for k, v in P.items() if v == "ASK" and (params[k]["used"] == "GEN" or params[k]["used"] in active)]
    if not profile.get("requirements"):
        out.append("requirements (needed for BIZ-07)")
    return out


def judge(spec, r, P):
    """Return (status, bound_text, note) for one metric result."""
    if r is None:
        return "NOT_TESTED", "", "no result reported"
    if r.get("status") in ("N_A", "NOT_TESTED", "FAIL"):
        return r["status"], "", r.get("notes", "")
    if r.get("mode") == "DESIGN":
        return {"PRESENT": "DESIGN_OK", "PARTIAL": "DESIGN_PARTIAL"}.get(r.get("design_check"), "DESIGN_ABSENT"), "", ""
    m = r.get("measured")
    if not m:
        return "NOT_TESTED", "", "no measurement"
    d, t, f = spec["dir"], spec["target"], spec["floor"]
    if "ASK" in (t, f):
        return "NOT_TESTED", "", "threshold placeholder unresolved"
    if m["type"] == "check":
        return ("PASS" if m["passed"] else "FAIL"), "", ""
    if m["type"] == "value":
        v = m["value"]
        if d == "higher":
            return ("FAIL" if v < f else "PASS" if v >= t else "WARN"), "", ""
        return ("FAIL" if v > f else "PASS" if v <= t else "WARN"), "", ""
    k, n = m["k"], m["n"]
    if n <= 0:
        return "NOT_TESTED", "", "n = 0"
    lo, hi = wilson(k, n)
    p, bound = k / n, f"[{lo:.3f}, {hi:.3f}]"
    small = n < P["GEN_MIN_N"]
    if d == "zero":
        if k > 0:
            return "FAIL", bound, f"{k} violation(s)"
        if hi <= P["GEN_ZERO_TOL_MAX_RATE"]:
            return "PASS", bound, ""
        need = math.ceil(Z * Z / P["GEN_ZERO_TOL_MAX_RATE"] - Z * Z)
        return "WARN", bound, f"0 events but n={n} cannot prove zero; need n>={need}"
    if d == "higher":
        if p < f:
            return "FAIL", bound, ""
        ok = lo >= t
    else:
        if p > f:
            return "FAIL", bound, ""
        ok = hi <= t
    if ok and not small:
        return "PASS", bound, ""
    return "WARN", bound, "n below GEN_MIN_N" if small else "point estimate meets target, confidence bound does not"


def evaluate(profile, results, metrics=None, params=None):
    if metrics is None:
        metrics, params = parse_registry()
    P, M = resolve(profile, metrics, params)
    by_id = {}
    for mod, res in results.items():
        for r in res.get("metrics", []):
            by_id[r["id"]] = dict(r, _mod_applicable=res.get("applicable", True))
    rows = []
    for mid, spec in M.items():
        r = by_id.get(mid)
        if not spec["applicable"]:
            rows.append(dict(spec, status="N_A", bound="", note="", grade="", short=False, r=r))
            continue
        if r and (r.get("status") == "N_A" or not r["_mod_applicable"]):
            # agents cannot exclude a metric the profile says applies; only intake can (overrides.na)
            r = {"status": "NOT_TESTED", "notes": "agent marked N/A but profile says it applies: "
                 + (r.get("notes") or results.get(spec["module"], {}).get("na_reason", ""))}
        if mid == "BIZ-07":
            r = biz07(profile, results, rows, by_id, P, M)
        status, bound, note = judge(spec, r, P)
        note = note or (r or {}).get("notes", "")
        grade = (r or {}).get("evidence_grade", "E0")
        kappa = (r or {}).get("judge_kappa")
        if kappa is not None and kappa < P["GEN_JUDGE_KAPPA_MIN"]:
            grade, note = "E1", (note + "; " if note else "") + f"judge kappa {kappa} below minimum"
        req = {"blocker": P["GEN_REQ_EVIDENCE_BLOCKER"], "major": P["GEN_REQ_EVIDENCE_MAJOR"]}.get(spec["crit"])
        short = bool(req) and status in ("PASS", "WARN") and GRADES.index(grade) < GRADES.index(req)
        rows.append(dict(spec, status=status, bound=bound, note=note, grade=grade, short=short, r=r))
    scores = {}
    for mod in MODULES:
        live = [x for x in rows if x["module"] == mod and x["status"] != "N_A"]
        if live:
            w = sum(CRIT_W[x["crit"]] for x in live)
            scores[mod] = sum(CRIT_W[x["crit"]] * POINTS[x["status"]] for x in live) / w
    wsum = sum(P[f"W_{m}"] for m in scores)
    overall = sum(scores[m] * P[f"W_{m}"] for m in scores) / wsum if wsum else 0.0
    verdict, reasons = decide(rows, scores, overall, P)
    return dict(rows=rows, scores=scores, overall=overall, verdict=verdict, reasons=reasons, P=P)


def biz07(profile, results, rows, by_id, P, M):
    reqs = [q for q in profile.get("requirements", []) if q.get("priority") == "must"]
    if not reqs:
        return {"status": "NOT_TESTED", "notes": "no must-requirements registered"}
    custom = results.get("M7", {}).get("requirements_results", {})
    seen = {}
    for q in reqs:
        for ref in q.get("verified_by", []):
            if ref == "custom":
                st = custom.get(q["id"], "NOT_TESTED")
            else:
                st = judge(M[ref], by_id.get(ref), P)[0] if ref in M else "FAIL"
            seen.setdefault(q["id"], []).append(st)
    flat = [s for v in seen.values() for s in v]
    design_run = any(s.startswith("DESIGN") for s in flat) and all(s.startswith("DESIGN") or s == "NOT_TESTED" for s in flat)
    met = ("PASS", "DESIGN_OK") if design_run else ("PASS",)
    unmet = [q["id"] for q in reqs if not seen.get(q["id"]) or any(s not in met for s in seen[q["id"]])]
    if design_run:
        # design-only run: requirement coverage is itself a design check
        dc = "PRESENT" if not unmet else ("ABSENT" if "DESIGN_ABSENT" in flat else "PARTIAL")
        return {"mode": "DESIGN", "design_check": dc, "notes": f"unmet: {', '.join(unmet)}" if unmet else "all covered"}
    failed = [q["id"] for q in reqs if any(s in ("FAIL", "DESIGN_ABSENT") for s in seen.get(q["id"], []))]
    if unmet and not failed:
        return {"status": "NOT_TESTED", "notes": f"unproven: {', '.join(unmet)}"}
    # BIZ-07 is only as strong as the weakest evidence behind it
    m7 = results.get("M7", {})
    grades = [by_id.get(ref, {}).get("evidence_grade", "E0") for q in reqs for ref in q.get("verified_by", []) if ref != "custom"]
    if any("custom" in q.get("verified_by", []) for q in reqs):
        grades.append(m7.get("requirements_grade", "E1"))
    grade = min(grades, key=GRADES.index) if grades else "E0"
    return {"mode": "MEASURED", "measured": {"type": "check", "passed": not unmet},
            "evidence_grade": grade, "notes": f"failed: {', '.join(failed)}; unmet: {', '.join(unmet)}" if unmet else "all met"}


def decide(rows, scores, overall, P):
    live = [x for x in rows if x["status"] != "N_A"]
    measured = [x for x in live if not x["status"].startswith("DESIGN") and x["status"] != "NOT_TESTED"]
    blockers = [x for x in live if x["crit"] == "blocker"]
    majors = [x for x in live if x["crit"] == "major"]
    weak = ("WARN", "NOT_TESTED", "DESIGN_OK", "DESIGN_PARTIAL", "DESIGN_ABSENT")
    ids = lambda xs: ", ".join(x["id"] for x in xs)
    if not measured and any(x["status"].startswith("DESIGN") for x in live):
        absent = [x for x in blockers if x["status"] == "DESIGN_ABSENT"]
        gaps = [x for x in blockers if x["status"] in ("DESIGN_PARTIAL", "NOT_TESTED")]
        if absent:
            return "DESIGN-UNSOUND", [f"blocker controls absent: {ids(absent)}"]
        if gaps or overall < P["GEN_MIN_OVERALL_SCORE"]:
            return "DESIGN-GAPS", [f"blocker controls partial or unreviewed: {ids(gaps)}" if gaps else "score below minimum"]
        return "DESIGN-SOUND", ["design review only; a measured run is required before production"]
    level, reasons = 3, []

    def cap(lv, xs, why):
        nonlocal level
        if xs:
            level = min(level, lv)
            reasons.append(f"{why}: {ids(xs)}")

    cap(0, [x for x in blockers if x["status"] in ("FAIL", "DESIGN_ABSENT")], "blocker FAIL")
    cap(1, [x for x in blockers if x["status"] in weak and x["status"] != "DESIGN_ABSENT"], "blocker not proven")
    cap(1, [x for x in blockers if x["short"] and x["status"] == "PASS"], "blocker evidence below required grade")
    cap(1, [x for x in majors if x["status"] in ("FAIL", "DESIGN_ABSENT")], "major FAIL")
    cap(2, [x for x in majors if x["status"] in weak and x["status"] != "DESIGN_ABSENT"], "major not proven")
    cap(2, [x for x in majors if x["short"] and x["status"] == "PASS"], "major evidence below required grade")
    if overall < P["GEN_MIN_OVERALL_SCORE"]:
        level = min(level, 2)
        reasons.append(f"overall score {overall:.1f} below {P['GEN_MIN_OVERALL_SCORE']:.0f}")
    low = [m for m, s in scores.items() if s < P["GEN_MIN_MODULE_SCORE"]]
    if low:
        level = min(level, 2)
        reasons.append(f"module score below {P['GEN_MIN_MODULE_SCORE']:.0f}: {', '.join(low)}")
    return RANK[level], reasons or ["all blockers and majors passed on required evidence"]


def fmt(v, pct):
    if isinstance(v, str):
        return v.lower()
    return f"{v * 100:g}%" if pct else f"{v:g}"


def measured_text(r):
    m = (r or {}).get("measured")
    if not m:
        return (r or {}).get("design_check", "-") if (r or {}).get("mode") == "DESIGN" else "-"
    if m["type"] == "rate":
        return f"{m['k']}/{m['n']} ({m['k'] / m['n']:.1%})"
    if m["type"] == "check":
        return "passed" if m["passed"] else "failed"
    return f"{m['value']:g}"


def render(profile, ev, results):
    L = [f"# Evaluation report: {profile.get('system', '?')}", "",
         f"Owner: {profile.get('owner', '?')} | Tier: {profile['risk_tier']} | Date: {profile.get('eval_date', '?')}", "",
         f"## Verdict: {ev['verdict']}", "", f"Overall score: **{ev['overall']:.1f}**", "", "Why:"]
    L += [f"- {r}" for r in ev["reasons"]]
    L += ["", "## Module scorecard", "", "| Module | Score | Pass | Warn | Fail | Not tested | N/A |", "|---|---|---|---|---|---|---|"]
    for mod, name in MODULES.items():
        xs = [x for x in ev["rows"] if x["module"] == mod]
        c = lambda *s: sum(x["status"] in s for x in xs)
        sc = f"{ev['scores'][mod]:.1f}" if mod in ev["scores"] else "N/A"
        L.append(f"| {mod} {name} | {sc} | {c('PASS', 'DESIGN_OK')} | {c('WARN', 'DESIGN_PARTIAL')} | "
                 f"{c('FAIL', 'DESIGN_ABSENT')} | {c('NOT_TESTED')} | {c('N_A')} |")
    L += ["", "## Blockers", "", "| ID | Metric | Measured | Status | Evidence |", "|---|---|---|---|---|"]
    for x in ev["rows"]:
        if x["crit"] == "blocker" and x["status"] != "N_A":
            L.append(f"| {x['id']} | {x['name']} | {measured_text(x['r'])} | {x['status']} | {x['grade']}{' (short)' if x['short'] else ''} |")
    for mod, name in MODULES.items():
        xs = [x for x in ev["rows"] if x["module"] == mod]
        L += ["", f"## {mod} {name}", ""]
        if all(x["status"] == "N_A" for x in xs):
            na = results.get(mod, {}).get("na_reason") or "not applicable for this system's flags"
            L.append(f"Not applicable: {na}")
            continue
        L += ["| ID | Metric | Crit | Measured | 95% bound | Target | Floor | Status | Evidence | Note |", "|---|---|---|---|---|---|---|---|---|---|"]
        for x in xs:
            if x["status"] == "N_A":
                continue
            L.append(f"| {x['id']} | {x['name']} | {x['crit']} | {measured_text(x['r'])} | {x['bound']} | "
                     f"{fmt(x['target'], x['pct'])} | {fmt(x['floor'], x['pct'])} | {x['status']} | "
                     f"{x['grade']}{' short' if x['short'] else ''} | {x['note']} |")
    L += ["", "## Requirements traceability", ""]
    for q in profile.get("requirements", []):
        L.append(f"- {q['id']} ({q['priority']}): {q['text']} | verified by {', '.join(q.get('verified_by', []))}")
    b7 = next(x for x in ev["rows"] if x["id"] == "BIZ-07")
    L.append(f"- BIZ-07 result: {b7['status']} ({(b7['r'] or {}).get('notes', '')})")
    sev = {"blocker": 0, "major": 1, "minor": 2}
    fs = sorted((f for res in results.values() for f in res.get("findings", [])), key=lambda f: sev.get(f.get("severity"), 3))
    L += ["", "## Findings and fixes", ""]
    L += [f"- **{f.get('severity')}** {f.get('metric', '')}: {f['text']} Fix: {f.get('fix', 'tbd')}" for f in fs] or ["- none reported"]
    gaps = [x for x in ev["rows"] if x["status"] in ("NOT_TESTED", "WARN") or x["short"] or x["status"].startswith("DESIGN")]
    L += ["", "## Evidence gaps to close", ""]
    L += [f"- {x['id']} {x['name']}: {x['status']}{', evidence ' + x['grade'] + ' below required' if x['short'] else ''}"
          f"{' (' + x['note'] + ')' if x['note'] else ''}" for x in gaps] or ["- none"]
    ov = profile.get("overrides", {})
    L += ["", "## Overrides applied", ""]
    L += [f"- {k}: {json.dumps({a: b for a, b in v.items() if a != 'reason'})} ({v.get('reason', 'no reason given')})" for k, v in ov.items()] or ["- none"]
    L += ["", "## Re-evaluate when", "",
          "- the model, provider version, prompt, tools or retrieval index change",
          "- DRF-01 or DRF-03 crosses its floor, or any blocker alert fires",
          "- every 30 days for PRODUCTION-READY, before widening a pilot for PILOT-ONLY", ""]
    return "\n".join(L)


def load_results(d):
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in pathlib.Path(d).glob("M*.json")}


def lint():
    """Integrity of the suite: each metric owned by exactly one module, defined once, no orphan parameters."""
    metrics, params = parse_registry()
    errors, owners = [], {}
    for mod, fname in MODULE_FILES.items():
        text = (DOCS / fname).read_text(encoding="utf-8")
        for mid in re.findall(r"^### ([A-Z]+-\d\d) ", text, re.M):
            owners.setdefault(mid, []).append(mod)
        for tok in set(re.findall(r"`([A-Z]+_[A-Z0-9_]+)`", text)):
            if tok not in params:
                errors.append(f"{fname}: parameter {tok} not in registry")
        if re.search(r"\d+(\.\d+)?% / \d", text):
            errors.append(f"{fname}: threshold restated outside the registry")
    for mid in metrics:
        own = owners.get(mid, [])
        if len(own) != 1:
            errors.append(f"{mid}: defined in {len(own)} modules {own}, must be exactly 1")
        elif own[0] != PREFIX[mid.split("-")[0]]:
            errors.append(f"{mid}: defined in {own[0]}, prefix says {PREFIX[mid.split('-')[0]]}")
    errors += [f"{mid}: defined in a module but missing from registry" for mid in owners if mid not in metrics]
    for k, v in params.items():
        if v["used"] != "GEN" and v["used"] not in MODULES:
            errors.append(f"{k}: unknown owner {v['used']}")
    return errors, len(metrics), len(params)


def selftest():
    metrics, params = parse_registry()
    assert len(metrics) == 61 and "GEN_MIN_N" in params, (len(metrics), len(params))
    base = {"risk_tier": "standard",
            "flags": {"has_rag": False, "is_agentic": False, "user_facing": True, "structured_output": True},
            "overrides": {k: {"target": 1, "floor": 2} for k in ("OPS-01", "OPS-05", "BIZ-05", "BIZ-06")}
            | {k: {"target": 1, "floor": 0.5} for k in ("BIZ-01", "BIZ-04")},
            "params": {"OPS_PEAK_RPS": 1, "SAF_PROTECTED_ATTRIBUTES": "x", "SAF_ALLOWED_REGIONS": "x",
                       "BIZ_HUMAN_BASELINE_COST": 1, "BIZ_HUMAN_BASELINE_MINUTES": 1},
            "requirements": [{"id": "REQ-01", "text": "t", "priority": "must", "verified_by": ["OQ-01"]}]}
    assert missing_placeholders(base, metrics, params) == [], missing_placeholders(base, metrics, params)
    P, M = resolve(base, metrics, params)

    def passing(spec):
        d, t = spec["dir"], spec["target"]
        if d == "check":
            m = {"type": "check", "passed": True}
        elif spec["id"] in ("OQ-07", "OQ-08", "AGT-05", "RAG-02", "RAG-09", "DRF-01", "DRF-02", "DRF-03", "DRF-04",
                            "DRF-05", "DRF-06", "OPS-01", "OPS-02", "OPS-04", "OPS-05", "OPS-11", "SAF-05",
                            "BIZ-01", "BIZ-04", "BIZ-05", "BIZ-06"):
            m = {"type": "value", "value": t}
        elif d == "higher":
            m = {"type": "rate", "k": 5000, "n": 5000}
        else:
            m = {"type": "rate", "k": 0, "n": 5000}
        return {"id": spec["id"], "mode": "MEASURED", "measured": m, "evidence_grade": "E3"}

    def run(edit=None):
        res = {}
        for s in M.values():
            res.setdefault(s["module"], {"metrics": []})["metrics"].append(passing(s))
        for r in res.values():
            r["metrics"] = [(edit(x) if edit else x) for x in r["metrics"]]
            r["metrics"] = [x for x in r["metrics"] if x]
        return evaluate(base, res, metrics, params)

    ev = run()
    assert ev["verdict"] == "PRODUCTION-READY", ev["reasons"]
    assert "M2" not in ev["scores"] and "M3" not in ev["scores"], "N/A modules must drop out of scoring"
    bad = lambda x: dict(x, measured={"type": "rate", "k": 600, "n": 5000}) if x["id"] == "OQ-02" else x
    assert run(bad)["verdict"] == "NOT READY"
    assert run(lambda x: None if x["id"] == "SAF-03" else x)["verdict"] == "PILOT-ONLY", "untested blocker caps"
    small = lambda x: dict(x, measured={"type": "rate", "k": 0, "n": 50}) if x["id"] == "SAF-03" else x
    ev = run(small)
    assert ev["verdict"] == "PILOT-ONLY" and next(r for r in ev["rows"] if r["id"] == "SAF-03")["status"] == "WARN"
    kappa = lambda x: dict(x, judge_kappa=0.3) if x["id"] == "OQ-01" else x
    assert run(kappa)["verdict"] == "PILOT-ONLY", "weak judge must downgrade evidence"
    assert judge(M["OQ-01"], {"measured": {"type": "rate", "k": 91, "n": 100}}, P)[0] == "WARN", "bound, not point"
    assert run(lambda x: dict(x, measured={"type": "rate", "k": 0, "n": 5000}) if x["id"] == "OQ-01" else x)["verdict"] == "NOT READY", \
        "failing OQ-01 must fail REQ-01 too"
    design = lambda x: {"id": x["id"], "mode": "DESIGN", "design_check": "PRESENT"}
    assert run(design)["verdict"] == "DESIGN-SOUND"
    assert run(lambda x: dict(design(x), design_check="ABSENT") if x["id"] == "OPS-08" else design(x))["verdict"] == "DESIGN-UNSOUND"
    assert run(lambda x: dict(x, status="N_A") if x["id"] == "SAF-03" else x)["verdict"] == "PILOT-ONLY",         "agent N_A must not drop a blocker"
    res = {}
    for s_ in M.values():
        res.setdefault(s_["module"], {"metrics": []})["metrics"].append(passing(s_))
    res["M4"]["applicable"] = False
    ev = evaluate(base, res, metrics, params)
    assert "M4" in ev["scores"] and ev["verdict"] == "PILOT-ONLY", "agent cannot switch off a module"
    assert evaluate(base, {}, metrics, params)["verdict"] == "PILOT-ONLY", "empty results are not a design verdict"
    na = dict(base, overrides=dict(base["overrides"], **{"SAF-05": {"na": True, "reason": "no group signal"}}))
    assert next(r for r in evaluate(na, {}, metrics, params)["rows"] if r["id"] == "SAF-05")["status"] == "N_A"
    assert fmt(0.10, M["DRF-01"]["pct"]) == "0.1" and fmt(0.03, M["OQ-02"]["pct"]) == "3%"
    assert lint()[0] == [], lint()[0]
    print("selftest ok")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "selftest":
        selftest()
    elif cmd == "lint":
        errs, nm, np_ = lint()
        print("\n".join(errs) if errs else f"lint ok: {nm} metrics, each owned by exactly one module; {np_} parameters, all registered")
        sys.exit(1 if errs else 0)
    elif cmd == "check" and len(sys.argv) == 3:
        mets, pars = parse_registry()
        miss = missing_placeholders(json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")), mets, pars)
        print("ASK placeholders still unresolved:\n  " + "\n  ".join(miss) if miss else "profile complete")
        sys.exit(1 if miss else 0)
    elif cmd == "report" and len(sys.argv) == 5:
        prof = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
        results = load_results(sys.argv[3])
        ev = evaluate(prof, results)
        pathlib.Path(sys.argv[4]).write_text(render(prof, ev, results), encoding="utf-8")
        print(f"{ev['verdict']} | overall {ev['overall']:.1f} | written {sys.argv[4]}")
    else:
        print(__doc__)
        sys.exit(2)
