"""Run the spec.md section 12 validation cases against app.py's beam calculations.

Usage:  python validate.py
Each value is compared to the hand-calculated expected value at the number of
decimal places given in the spec. Exits with status 1 if any check fails.
"""

import sys

import numpy as np

import app

W12 = "W12 × 26"
rows = []


def raw(beam_type, span, points=(), uniforms=(), **over):
    r = dict(beam_type=beam_type, span=str(span), limit="L/360", material=app.STEEL,
             section=W12, sx="", ix="", e="", fb="24",
             point_loads=[(str(p), str(a)) for p, a in points],
             uniform_loads=[(str(w), str(s), str(e)) for w, s, e in uniforms])
    r.update(over)
    return r


def solve(*args, **kw):
    model, errors = app.validate_inputs(raw(*args, **kw))
    assert not errors, errors
    return app.analyze(model)


def check(case, qty, expected, actual, places):
    """Pass if actual rounds to expected at the spec's number of decimal places."""
    if isinstance(expected, str):
        ok = expected == actual
        rows.append((case, qty, expected, actual, ok))
        return
    ok = round(actual, places) == round(expected, places)
    rows.append((case, qty, f"{expected:.{places}f}", f"{actual:.{places}f}", ok))


def pf(b):
    return "PASS" if b else "FAIL"


def main():
    r = solve(app.SIMPLE, 20, uniforms=[(1, 0, 20)])
    check(1, "R_L (kip)", 10.00, r["reactions"]["left"], 2)
    check(1, "R_R (kip)", 10.00, r["reactions"]["right"], 2)
    check(1, "M_max (kip-ft)", 50.00, r["max_moment"], 2)
    check(1, "M_max location (ft)", 10.0, r["max_moment_x"], 1)
    check(1, "Δ_max (in)", 0.609, r["max_defl"], 3)
    check(1, "f_b (ksi)", 17.96, r["fb"], 2)
    check(1, "Δ_allow L/360 (in)", 0.667, r["allow_defl"], 3)
    check(1, "Bending check", "PASS", pf(r["bending_pass"]), 0)
    check(1, "Deflection check", "PASS", pf(r["defl_pass"]), 0)
    case1 = r

    r = solve(app.SIMPLE, 20, points=[(10, 10)])
    check(2, "R_L = R_R (kip)", 5.00, r["reactions"]["left"], 2)
    check(2, "M_max (kip-ft)", 50.00, r["max_moment"], 2)
    check(2, "Δ_max (in)", 0.487, r["max_defl"], 3)
    check(2, "Δ_max location (ft)", 10.0, r["max_defl_x"], 1)

    r = solve(app.SIMPLE, 20, points=[(10, 5)])
    check(3, "R_L (kip)", 7.50, r["reactions"]["left"], 2)
    check(3, "R_R (kip)", 2.50, r["reactions"]["right"], 2)
    check(3, "M_max (kip-ft)", 37.50, r["max_moment"], 2)
    check(3, "M_max location (ft)", 5.0, r["max_moment_x"], 1)
    check(3, "Δ_max (in)", 0.340, r["max_defl"], 3)
    check(3, "Δ_max location (ft)", 8.82, r["max_defl_x"], 2)
    case3 = r

    r = solve(app.CANTILEVER, 10, points=[(5, 10)])
    check(4, "R (kip)", 5.00, r["reactions"]["left"], 2)
    check(4, "M_fixed (kip-ft)", -50.00, r["reactions"]["moment"], 2)
    check(4, "Δ_max (in)", 0.487, r["max_defl"], 3)
    check(4, "Δ_max location (ft)", 10.0, r["max_defl_x"], 1)

    r = solve(app.CANTILEVER, 10, uniforms=[(1, 0, 10)])
    check(5, "R (kip)", 10.00, r["reactions"]["left"], 2)
    check(5, "M_fixed (kip-ft)", -50.00, r["reactions"]["moment"], 2)
    check(5, "Δ_max (in)", 0.365, r["max_defl"], 3)
    check(5, "Δ_max location (ft)", 10.0, r["max_defl_x"], 1)

    r = solve(app.SIMPLE, 20, points=[(10, 10)], uniforms=[(1, 0, 20)])
    check(6, "M_max (kip-ft)", 100.00, r["max_moment"], 2)
    check(6, "Δ_max (in)", 1.095, r["max_defl"], 3)
    check(6, "f_b (ksi)", 35.93, r["fb"], 2)
    check(6, "Bending check", "FAIL", pf(r["bending_pass"]), 0)
    check(6, "Deflection check", "FAIL", pf(r["defl_pass"]), 0)

    r = solve(app.SIMPLE, 20, uniforms=[(2, 0, 10)])
    check(7, "R_L (kip)", 15.00, r["reactions"]["left"], 2)
    check(7, "R_R (kip)", 5.00, r["reactions"]["right"], 2)
    check(7, "M_max (kip-ft)", 56.25, r["max_moment"], 2)
    check(7, "M_max location (ft)", 7.5, r["max_moment_x"], 1)

    # 8: property checks
    check(8, "Symmetry: R_L − R_R, case 1 (kip)", 0.000,
          case1["reactions"]["left"] - case1["reactions"]["right"], 3)
    v = np.interp(case1["x"], case1["x"], case1["v"])
    v_mirror = np.interp(20 - case1["x"], case1["x"], case1["v"])
    check(8, "Symmetry: largest difference v(x) − v(L−x), case 1 (in)", 0.000, float(np.max(np.abs(v - v_mirror))), 3)
    r2 = solve(app.SIMPLE, 20, points=[(20, 5)])
    for qty, a, b in (("R_L", r2["reactions"]["left"], case3["reactions"]["left"]),
                      ("R_R", r2["reactions"]["right"], case3["reactions"]["right"]),
                      ("M_max", r2["max_moment"], case3["max_moment"]),
                      ("Δ_max", r2["max_defl"], case3["max_defl"])):
        check(8, f"Proportionality: {qty}(2P) / {qty}(P), case 3", 2.000, a / b, 3)

    # 9: span limits
    m, err = app.validate_inputs(raw(app.SIMPLE, 100, uniforms=[(1, 0, 100)]))
    check(9, "L = 100 ft calculates", "calculates", "calculates" if m else "rejected", 0)
    for L in ("0", "101"):
        m, err = app.validate_inputs(raw(app.SIMPLE, L, points=[(1, 0)]))
        check(9, f"L = {L} ft rejected", "rejected", f"rejected: {err.get('span')}" if not m and "span" in err
              else "calculates", 0)
        rows[-1] = rows[-1][:3] + (rows[-1][3],) + (rows[-1][3].startswith("rejected"),)

    # 10: invalid inputs
    bad = {
        "No loads": raw(app.SIMPLE, 20),
        "Point load at 25 ft on 20 ft span": raw(app.SIMPLE, 20, points=[(5, 25)]),
        "Uniform start ≥ end": raw(app.SIMPLE, 20, uniforms=[(1, 12, 12)]),
        "Custom Ix ≤ 0": raw(app.SIMPLE, 20, uniforms=[(1, 0, 20)], material=app.CUSTOM,
                             section="", sx="33.4", ix="0", e="29000"),
        "Non-numeric span": raw(app.SIMPLE, "twenty", points=[(5, 10)]),
    }
    for name, rr in bad.items():
        m, err = app.validate_inputs(rr)
        msg = "; ".join(err.values())
        rows.append((10, name, "rejected with message", f"rejected: {msg}" if m is None else "calculates",
                     m is None and bool(msg)))

    print("| Case | Quantity | Expected | Actual | Result |")
    print("|---|---|---|---|---|")
    for c, q, e, a, ok in rows:
        print(f"| {c} | {q} | {e} | {a} | {'PASS' if ok else '**FAIL**'} |")
    n_ok = sum(r[4] for r in rows)
    print(f"\n{n_ok}/{len(rows)} checks passed")
    return 0 if n_ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
