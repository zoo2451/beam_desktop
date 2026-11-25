"""Beam Designer - Tkinter desktop app.

Run with:  python app.py
Requirements and validation cases are in spec.md.
"""

import json
import math
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Polygon, Rectangle, Circle
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

APP_TITLE = "Beam Designer"
SIMPLE, CANTILEVER = "Simply supported", "Cantilever"
STEEL, LUMBER, CUSTOM = "Steel W-shape", "Lumber", "Custom section"
LIMITS = {"L/180": 180, "L/240": 240, "L/360": 360, "L/480": 480}
MAX_SPAN_FT = 100.0
GRID_INTERVALS = 2000

# ------------------------------------------------------------ section data
# Steel: AISC Steel Construction Manual Table 1-1. sx in^3, ix in^4, d and bf in, area in^2.
STEEL_SHAPES = {
    "W8 × 10":  dict(sx=7.81, ix=30.8, d=7.89, bf=3.94, area=2.96),
    "W10 × 12": dict(sx=10.9, ix=53.8, d=9.87, bf=3.96, area=3.54),
    "W10 × 22": dict(sx=23.2, ix=118, d=10.2, bf=5.75, area=6.49),
    "W12 × 26": dict(sx=33.4, ix=204, d=12.2, bf=6.49, area=7.65),
    "W14 × 22": dict(sx=29.0, ix=199, d=13.7, bf=5.00, area=6.49),
    "W14 × 30": dict(sx=42.0, ix=291, d=13.8, bf=6.73, area=8.85),
    "W16 × 26": dict(sx=38.4, ix=301, d=15.7, bf=5.50, area=7.68),
    "W18 × 35": dict(sx=57.6, ix=510, d=17.7, bf=6.00, area=10.3),
    "W21 × 44": dict(sx=81.6, ix=843, d=20.7, bf=6.50, area=13.0),
    "W24 × 55": dict(sx=114, ix=1350, d=23.6, bf=7.01, area=16.2),
}
STEEL_E, STEEL_FB = 29000.0, 24.0  # ksi; Fb ~ 0.66 Fy for Fy = 36 ksi (editable)

# Lumber: actual dressed sizes (b x d, in); NDS Supplement reference values for
# Douglas Fir-Larch No. 2, used directly with no adjustment factors.
LUMBER_SIZES = {"2×10 DF-L No. 2": (1.5, 9.25), "2×12 DF-L No. 2": (1.5, 11.25),
                "4×12 DF-L No. 2": (3.5, 11.25)}
LUMBER_E, LUMBER_FB = 1600.0, 0.900  # ksi
LUMBER_SHAPES = {name: dict(b=b, d=d, sx=b * d * d / 6, ix=b * d ** 3 / 12, area=b * d)
                 for name, (b, d) in LUMBER_SIZES.items()}


def section_properties(material, name, custom=None):
    """Return sx (in^3), ix (in^4), e (ksi), default fb (ksi) for a section choice."""
    if material == STEEL:
        s = STEEL_SHAPES[name]
        return dict(sx=s["sx"], ix=s["ix"], e=STEEL_E, fb=STEEL_FB)
    if material == LUMBER:
        s = LUMBER_SHAPES[name]
        return dict(sx=s["sx"], ix=s["ix"], e=LUMBER_E, fb=LUMBER_FB)
    return dict(custom)


# ============================================================ calculations
def total_load(model):
    """W (kip) and M0 (kip-ft): total load and its moment about x = 0."""
    W = M0 = 0.0
    for P, a in model["point_loads"]:
        W += P
        M0 += P * a
    for w, s, e in model["uniform_loads"]:
        W += w * (e - s)
        M0 += w * (e - s) * (s + e) / 2
    return W, M0


def reactions(model):
    """Spec 8.1. Returns left (kip), right (kip), fixed-end moment (kip-ft)."""
    W, M0 = total_load(model)
    if model["beam_type"] == SIMPLE:
        right = M0 / model["span"]
        return dict(left=W - right, right=right, moment=0.0)
    return dict(left=W, right=0.0, moment=-M0)


def shear_at(model, R, x, side="right"):
    """V(x) in kip (spec 8.2). side='left' gives the value just left of a point load."""
    x = np.asarray(x, dtype=float)
    V = np.full_like(x, R["left"])
    for P, a in model["point_loads"]:
        V -= P * ((x >= a) if side == "right" else (x > a))
    for w, s, e in model["uniform_loads"]:
        V -= w * np.clip(np.minimum(x, e) - s, 0.0, None)
    return V


def moment_at(model, R, x):
    """M(x) in kip-ft, sagging positive: moment of all forces left of x (spec 8.2)."""
    x = np.asarray(x, dtype=float)
    M = R["left"] * x + R["moment"]  # fixed-end moment acts at x = 0 (zero for simple span)
    for P, a in model["point_loads"]:
        M -= P * np.clip(x - a, 0.0, None)
    for w, s, e in model["uniform_loads"]:
        end = np.minimum(x, e)
        length = np.clip(end - s, 0.0, None)
        M -= w * length * (x - (s + end) / 2)
    return M


def _cumtrapz(y, x):
    out = np.zeros_like(y)
    out[1:] = np.cumsum((y[1:] + y[:-1]) / 2 * np.diff(x))
    return out


def analyze(model):
    """Full analysis for a validated model (see validate_inputs). All spec 8 results."""
    L = model["span"]
    sec = model["section"]
    R = reactions(model)

    # grid: uniform points + every load position, load endpoint, and support
    breaks = [0.0, L] + [a for _, a in model["point_loads"]]
    breaks += [v for _, s, e in model["uniform_loads"] for v in (s, e)]
    x = np.unique(np.concatenate([np.linspace(0, L, GRID_INTERVALS + 1), breaks]))
    # add every point where V changes sign inside an interval (V is linear between grid points)
    vr, vl = shear_at(model, R, x[:-1], "right"), shear_at(model, R, x[1:], "left")
    cross = (vr * vl < 0)
    if cross.any():
        x0 = x[:-1][cross] + vr[cross] / (vr[cross] - vl[cross]) * np.diff(x)[cross]
        x = np.unique(np.concatenate([x, x0]))

    V_right, V_left = shear_at(model, R, x, "right"), shear_at(model, R, x, "left")
    M = moment_at(model, R, x)

    # deflection: EI v'' = -M, v downward (in); x and M converted to inches
    x_in = x * 12.0
    curvature = -(M * 12.0) / (sec["e"] * sec["ix"])
    slope = _cumtrapz(curvature, x_in)
    v = _cumtrapz(slope, x_in)
    if model["beam_type"] == SIMPLE:
        v -= v[-1] * x / L  # enforce v(L) = 0 (v(0) = 0 already)

    # shear diagram with both sides of each jump
    xs = np.repeat(x, 2)
    Vs = np.column_stack([V_left, V_right]).ravel()
    keep = np.ones_like(xs, dtype=bool)
    keep[0::2] = np.abs(V_left - V_right) > 1e-12  # only keep left values where V jumps
    keep[0] = False
    xs, Vs = xs[keep], Vs[keep]
    if model["beam_type"] == CANTILEVER:  # free end: shear returns to zero
        pass

    iV = int(np.argmax(np.abs(Vs)))
    iM = int(np.argmax(np.abs(M)))
    iv = int(np.argmax(np.abs(v)))
    W, _ = total_load(model)
    fb = abs(M[iM]) * 12.0 / sec["sx"]
    allow = L * 12.0 / model["limit_n"]
    return dict(
        model=model, reactions=R, total_load=W,
        equilibrium=R["left"] + R["right"] - W,
        x=x, M=M, v=v, xs=xs, Vs=Vs,
        max_shear=float(Vs[iV]), max_shear_x=float(xs[iV]),
        max_moment=float(M[iM]), max_moment_x=float(x[iM]),
        max_defl=float(abs(v[iv])), max_defl_x=float(x[iv]),
        fb=fb, Fb=sec["fb"], fb_ratio=fb / sec["fb"], bending_pass=fb <= sec["fb"],
        allow_defl=allow, defl_ratio=abs(v[iv]) / allow, defl_pass=abs(v[iv]) <= allow,
    )


# ============================================================== validation
def _num(raw, key, errors, label, positive=False, allow_zero=True):
    text = str(raw.get(key, "")).strip()
    if text == "":
        errors[key] = f"{label} is required."
        return None
    try:
        val = float(text)
    except ValueError:
        errors[key] = f"{label} must be a number."
        return None
    if not math.isfinite(val):
        errors[key] = f"{label} must be a finite number."
        return None
    if positive and val <= 0:
        errors[key] = f"{label} must be greater than zero."
        return None
    if not allow_zero and val < 0:
        errors[key] = f"{label} cannot be negative."
        return None
    return val


def validate_inputs(raw):
    """Check every input (spec 6 and 11). Returns (model or None, {field key: message})."""
    errors = {}
    beam_type = raw.get("beam_type")
    if beam_type not in (SIMPLE, CANTILEVER):
        errors["beam_type"] = "Select a beam type."
    span = _num(raw, "span", errors, "Span", positive=True)
    if span is not None and span > MAX_SPAN_FT:
        errors["span"] = f"Span must not exceed {MAX_SPAN_FT:g} ft."
        span = None

    material = raw.get("material")
    if material == CUSTOM:
        custom = {}
        for key, label in (("sx", "Section modulus Sx"), ("ix", "Moment of inertia Ix"),
                           ("e", "Modulus of elasticity E")):
            custom[key] = _num(raw, key, errors, label, positive=True)
        props = custom
    elif material in (STEEL, LUMBER):
        table = STEEL_SHAPES if material == STEEL else LUMBER_SHAPES
        if raw.get("section") not in table:
            errors["section"] = "Select a section."
            props = {}
        else:
            props = section_properties(material, raw["section"])
    else:
        errors["material"] = "Select a material."
        props = {}
    fb = _num(raw, "fb", errors, "Allowable bending stress Fb", positive=True)

    limit = raw.get("limit")
    if limit not in LIMITS:
        errors["limit"] = "Select a deflection limit."

    points, uniforms = [], []
    for i, (p_txt, a_txt) in enumerate(raw.get("point_loads", [])):
        r = {f"P{i}": p_txt, f"a{i}": a_txt}
        P = _num(r, f"P{i}", errors, f"Point load {i + 1} magnitude", positive=True)
        a = _num(r, f"a{i}", errors, f"Point load {i + 1} position")
        if a is not None and span is not None and not (0 <= a <= span):
            errors[f"a{i}"] = f"Point load {i + 1} position must be between 0 and {span:g} ft."
            a = None
        if P is not None and a is not None:
            points.append((P, a))
    for i, (w_txt, s_txt, e_txt) in enumerate(raw.get("uniform_loads", [])):
        r = {f"w{i}": w_txt, f"s{i}": s_txt, f"e{i}": e_txt}
        w = _num(r, f"w{i}", errors, f"Uniform load {i + 1} magnitude", positive=True)
        s = _num(r, f"s{i}", errors, f"Uniform load {i + 1} start")
        e = _num(r, f"e{i}", errors, f"Uniform load {i + 1} end")
        for key, val, lab in ((f"s{i}", s, "start"), (f"e{i}", e, "end")):
            if val is not None and span is not None and not (0 <= val <= span):
                errors[key] = f"Uniform load {i + 1} {lab} must be between 0 and {span:g} ft."
        if s is not None and e is not None and s >= e and f"e{i}" not in errors:
            errors[f"e{i}"] = f"Uniform load {i + 1} end must be greater than its start."
        if w is not None and s is not None and e is not None and not (
                {f"s{i}", f"e{i}"} & errors.keys()):
            uniforms.append((w, s, e))
    if not raw.get("point_loads") and not raw.get("uniform_loads"):
        errors["loads"] = "Add at least one load."

    if errors:
        return None, errors
    section = dict(props, fb=fb, material=material,
                   name=raw.get("section") if material != CUSTOM else "Custom section")
    return dict(beam_type=beam_type, span=span, point_loads=points, uniform_loads=uniforms,
                section=section, limit=limit, limit_n=LIMITS[limit]), {}


# ================================================================= drawing
NAVY, BLUE, ORANGE, GRAY = "#1d3557", "#2f73bd", "#c66a20", "#69758a"


def draw_diagrams(fig, res):
    """Draw the beam/loads, shear, moment, and deflection panels into fig (spec 9)."""
    fig.clear()
    axes = fig.subplots(4, 1, sharex=True, gridspec_kw=dict(height_ratios=[1.1, 1, 1, 1]))
    model = res["model"]
    L = model["span"]
    fig._beam_span = L
    _draw_beam(axes[0], model, res)

    ax = axes[1]
    ax.fill_between(res["xs"], res["Vs"], color=BLUE, alpha=0.18, lw=0)
    ax.plot(res["xs"], res["Vs"], color=BLUE, lw=1.6)
    _mark(ax, res["max_shear_x"], res["max_shear"], f"{res['max_shear']:.2f} kip")
    ax.set_ylabel("V (kip)")
    ax.set_title("Shear  (positive = net upward force left of section)", fontsize=9, loc="left")

    ax = axes[2]
    ax.fill_between(res["x"], res["M"], color=ORANGE, alpha=0.18, lw=0)
    ax.plot(res["x"], res["M"], color=ORANGE, lw=1.6)
    _mark(ax, res["max_moment_x"], res["max_moment"], f"{res['max_moment']:.2f} kip-ft")
    ax.set_ylabel("M (kip-ft)")
    ax.set_title("Moment  (positive = sagging)", fontsize=9, loc="left")

    ax = axes[3]
    ax.plot(res["x"], -res["v"], color=NAVY, lw=1.8)  # downward deflection plotted down
    ax.axhline(-res["allow_defl"], color=GRAY, ls=":", lw=1)
    ax.text(L, -res["allow_defl"], f"  limit {model['limit']} = {res['allow_defl']:.3f} in",
            fontsize=7, color=GRAY, va="bottom", ha="right")
    i = int(np.argmax(np.abs(res["v"])))
    _mark(ax, res["x"][i], -res["v"][i], f"{res['max_defl']:.3f} in")
    ax.set_ylabel("Deflection (in)")
    ax.set_title("Deflection  (downward plotted down)", fontsize=9, loc="left")
    ax.set_xlabel("x from left end (ft)")
    for a in axes[1:]:
        a.axhline(0, color="#333", lw=0.8)
        a.grid(alpha=0.25)
        a.margins(y=0.25)
        a.tick_params(labelsize=8)
    axes[3].set_xlim(-0.04 * L, 1.04 * L)
    fig.tight_layout(h_pad=0.6)
    return axes


def _mark(ax, x, y, text):
    """Dot and label at a maximum; label kept inside the plot near either end."""
    ax.plot([x], [y], "o", color="#222", ms=4)
    span = ax.figure._beam_span
    right_side = x > 0.75 * span
    ax.annotate(text, (x, y), xytext=(-6 if right_side else 6, 6 if y >= 0 else -12),
                textcoords="offset points", ha="right" if right_side else "left",
                fontsize=8, fontweight="bold")


def _draw_beam(ax, model, res):
    L = model["span"]
    h = 0.06 * L  # symbol size, scaled to the span
    ax.set_title(f"{model['beam_type']} beam, L = {L:g} ft, {model['section']['name']}",
                 fontsize=9, loc="left")
    ax.plot([0, L], [0, 0], color=NAVY, lw=5, solid_capstyle="butt", zorder=3)
    if model["beam_type"] == SIMPLE:
        ax.add_patch(Polygon([[0, 0], [-h / 2, -h], [h / 2, -h]], color=GRAY))      # pin
        ax.add_patch(Polygon([[L, 0], [L - h / 2, -0.8 * h], [L + h / 2, -0.8 * h]], color=GRAY))
        ax.add_patch(Circle((L, -0.9 * h), 0.1 * h, color=GRAY))                     # roller
        ax.text(0, -1.5 * h, f"R = {res['reactions']['left']:.2f} kip", ha="center", fontsize=7)
        ax.text(L, -1.5 * h, f"R = {res['reactions']['right']:.2f} kip", ha="center", fontsize=7)
    else:
        ax.add_patch(Rectangle((-0.3 * h, -h), 0.3 * h, 2 * h, color=GRAY, hatch="////",
                               fill=False))
        ax.plot([0, 0], [-h, h], color=GRAY, lw=2)
        ax.text(0.02 * L, -1.5 * h, f"R = {res['reactions']['left']:.2f} kip, "
                f"M = {res['reactions']['moment']:.2f} kip-ft", fontsize=7)
    # uniform loads: stacked blocks
    level = 0.15 * h
    for w, s, e in model["uniform_loads"]:
        ax.add_patch(Rectangle((s, level), e - s, 0.6 * h, color=BLUE, alpha=0.25, lw=0))
        for xa in np.linspace(s, e, max(2, int((e - s) / L * 16) + 1)):
            ax.annotate("", (xa, level), (xa, level + 0.6 * h),
                        arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=0.8, mutation_scale=6))
        ax.text((s + e) / 2, level + 0.68 * h, f"{w:g} kip/ft", ha="center", fontsize=7,
                color=BLUE)
        level += 0.95 * h
    for P, a in model["point_loads"]:
        top = level + 0.9 * h
        ax.annotate("", (a, 0.08 * h), (a, top),
                    arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=1.6, mutation_scale=10))
        ax.text(a, top + 0.08 * h, f"{P:g} kip", ha="center", fontsize=7, color=ORANGE)
    ax.set_ylim(-2.0 * h, level + 1.4 * h)
    ax.set_aspect("auto")
    ax.axis("off")


# ===================================================================== app
class BeamApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1280x820")
        self.minsize(1050, 680)
        self.configure(bg="#f4f7fb")
        self.fields = {}       # error key -> tk.Entry for highlighting
        self.point_rows = []   # list of (P var, a var)
        self.uniform_rows = []  # list of (w var, s var, e var)
        self._pending = None
        self.result = None
        self.path = None        # file the design was opened from / saved to
        self.dirty = False      # unsaved changes?
        self._loading = False
        style = ttk.Style(self)
        style.configure("Group.TLabelframe.Label", font=("Segoe UI", 10, "bold"), foreground=NAVY)
        self._build_menu()
        self._build_inputs()
        self._build_outputs()
        self.load_state(default_state())
        self.protocol("WM_DELETE_WINDOW", self.quit_app)

    # ------------------------------------------------- file menu (14.1)
    def _build_menu(self):
        bar = tk.Menu(self)
        m = tk.Menu(bar, tearoff=False)
        m.add_command(label="New", accelerator="Ctrl+N", command=self.new_design)
        m.add_command(label="Open…", accelerator="Ctrl+O", command=self.open_design)
        m.add_command(label="Save", accelerator="Ctrl+S", command=self.save_design)
        m.add_command(label="Save As…", accelerator="Ctrl+Shift+S", command=self.save_design_as)
        m.add_separator()
        m.add_command(label="Quit", command=self.quit_app)
        bar.add_cascade(label="File", menu=m)
        self.file_menu = m
        self.config(menu=bar)
        self.bind_all("<Control-n>", lambda e: self.new_design())
        self.bind_all("<Control-o>", lambda e: self.open_design())
        self.bind_all("<Control-s>", lambda e: self.save_design())
        self.bind_all("<Control-S>", lambda e: self.save_design_as())

    def update_title(self):
        name = os.path.basename(self.path) if self.path else "Untitled"
        self.title(f"{'*' if self.dirty else ''}{name} - {APP_TITLE}")

    def confirm_discard(self):
        if not self.dirty:
            return True
        ans = messagebox.askyesnocancel(APP_TITLE, "Save changes to this design first?")
        if ans is None:
            return False
        return self.save_design() if ans else True

    def new_design(self):
        if self.confirm_discard():
            self.path = None
            self.load_state(default_state())

    def open_design(self):
        if not self.confirm_discard():
            return
        path = filedialog.askopenfilename(title="Open beam design", filetypes=BEAM_FILETYPES)
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as fh:
                state = design_from_json(json.load(fh))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            messagebox.showerror(APP_TITLE, f"Could not open this file; the current design "
                                 f"is unchanged.\n\n{exc}")
            return
        self.path = path
        self.load_state(state)

    def save_design(self):
        if not self.path:
            return self.save_design_as()
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(design_to_json(self.collect_raw()), fh, indent=2, ensure_ascii=False)
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Could not save the design:\n{exc}")
            return False
        self.dirty = False
        self.update_title()
        return True

    def save_design_as(self):
        path = filedialog.asksaveasfilename(
            title="Save beam design", defaultextension=".beam", filetypes=BEAM_FILETYPES,
            initialfile=os.path.basename(self.path) if self.path else "beam_design.beam")
        if not path:
            return False
        self.path = path
        return self.save_design()

    def quit_app(self):
        if self.confirm_discard():
            self.destroy()

    # ----------------------------------------------------------- inputs
    def _entry(self, parent, var, width=9):
        e = tk.Entry(parent, textvariable=var, width=width, relief="solid", bd=1,
                     highlightthickness=0)
        var.trace_add("write", lambda *_: self.schedule())
        return e

    def _build_inputs(self):
        left = ttk.Frame(self, padding=10)
        left.pack(side="left", fill="y")
        ttk.Label(left, text=APP_TITLE, font=("Segoe UI", 15, "bold"),
                  foreground=NAVY).pack(anchor="w", pady=(0, 8))

        g = ttk.LabelFrame(left, text="Beam", padding=8, style="Group.TLabelframe")
        g.pack(fill="x")
        self.beam_type = tk.StringVar()
        self.span = tk.StringVar()
        self.limit = tk.StringVar()
        ttk.Label(g, text="Beam type").grid(row=0, column=0, sticky="w")
        cb = ttk.Combobox(g, textvariable=self.beam_type, values=[SIMPLE, CANTILEVER],
                          state="readonly", width=18)
        cb.grid(row=0, column=1, sticky="w", pady=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self.schedule())
        ttk.Label(g, text="Span L (ft)").grid(row=1, column=0, sticky="w")
        self.fields["span"] = self._entry(g, self.span)
        self.fields["span"].grid(row=1, column=1, sticky="w", pady=2)
        ttk.Label(g, text="Deflection limit").grid(row=2, column=0, sticky="w")
        cb = ttk.Combobox(g, textvariable=self.limit, values=list(LIMITS), state="readonly",
                          width=8)
        cb.grid(row=2, column=1, sticky="w", pady=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self.schedule())
        g.columnconfigure(0, minsize=150)

        g = ttk.LabelFrame(left, text="Section", padding=8, style="Group.TLabelframe")
        g.pack(fill="x", pady=(8, 0))
        g.columnconfigure(0, minsize=150)
        self.material = tk.StringVar()
        self.section = tk.StringVar()
        ttk.Label(g, text="Material").grid(row=0, column=0, sticky="w")
        cb = ttk.Combobox(g, textvariable=self.material, values=[STEEL, LUMBER, CUSTOM],
                          state="readonly", width=18)
        cb.grid(row=0, column=1, sticky="w", pady=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self.on_material())
        ttk.Label(g, text="Section").grid(row=1, column=0, sticky="w")
        self.section_cb = ttk.Combobox(g, textvariable=self.section, state="readonly", width=18)
        self.section_cb.grid(row=1, column=1, sticky="w", pady=2)
        self.section_cb.bind("<<ComboboxSelected>>", lambda e: self.on_section())
        self.sx, self.ix, self.e, self.fb = (tk.StringVar() for _ in range(4))
        for r, (key, var, label) in enumerate((("sx", self.sx, "Sx (in³)"),
                                               ("ix", self.ix, "Ix (in⁴)"),
                                               ("e", self.e, "E (ksi)"),
                                               ("fb", self.fb, "Allowable Fb (ksi)")), start=2):
            ttk.Label(g, text=label).grid(row=r, column=0, sticky="w")
            self.fields[key] = self._entry(g, var)
            self.fields[key].grid(row=r, column=1, sticky="w", pady=2)
        self.section_note = ttk.Label(g, text="", foreground=GRAY, wraplength=290)
        self.section_note.grid(row=6, column=0, columnspan=2, sticky="w", pady=(4, 0))

        g = ttk.LabelFrame(left, text="Point loads (downward +)", padding=8,
                           style="Group.TLabelframe")
        g.pack(fill="x", pady=(8, 0))
        self.point_frame = ttk.Frame(g)
        self.point_frame.pack(fill="x")
        ttk.Button(g, text="+ Add point load", command=self.add_point).pack(anchor="w", pady=(4, 0))

        g = ttk.LabelFrame(left, text="Uniform loads (downward +)", padding=8,
                           style="Group.TLabelframe")
        g.pack(fill="x", pady=(8, 0))
        self.uniform_frame = ttk.Frame(g)
        self.uniform_frame.pack(fill="x")
        ttk.Button(g, text="+ Add uniform load", command=self.add_uniform).pack(anchor="w",
                                                                              pady=(4, 0))

    def _render_loads(self):
        for f in (self.point_frame, self.uniform_frame):
            for w in f.winfo_children():
                w.destroy()
        for k in [k for k in self.fields if k[0] in "Pawse" and k[1:].isdigit()]:
            del self.fields[k]
        if self.point_rows:
            for c, t in enumerate(("#", "P (kip)", "a (ft)")):
                ttk.Label(self.point_frame, text=t, foreground=GRAY).grid(row=0, column=c, sticky="w")
        else:
            ttk.Label(self.point_frame, text="No point loads.", foreground=GRAY).grid(row=0, column=0)
        for i, (pv, av) in enumerate(self.point_rows):
            ttk.Label(self.point_frame, text=str(i + 1)).grid(row=i + 1, column=0, padx=(0, 6))
            for c, (key, var) in enumerate(((f"P{i}", pv), (f"a{i}", av)), start=1):
                self.fields[key] = self._entry(self.point_frame, var, 8)
                self.fields[key].grid(row=i + 1, column=c, padx=2, pady=1)
            ttk.Button(self.point_frame, text="✕", width=3,
                       command=lambda i=i: self.remove_point(i)).grid(row=i + 1, column=3, padx=4)
        if self.uniform_rows:
            for c, t in enumerate(("#", "w (kip/ft)", "start (ft)", "end (ft)")):
                ttk.Label(self.uniform_frame, text=t, foreground=GRAY).grid(row=0, column=c, sticky="w")
        else:
            ttk.Label(self.uniform_frame, text="No uniform loads.", foreground=GRAY).grid(row=0, column=0)
        for i, (wv, sv, ev) in enumerate(self.uniform_rows):
            ttk.Label(self.uniform_frame, text=str(i + 1)).grid(row=i + 1, column=0, padx=(0, 6))
            for c, (key, var) in enumerate(((f"w{i}", wv), (f"s{i}", sv), (f"e{i}", ev)), start=1):
                self.fields[key] = self._entry(self.uniform_frame, var, 8)
                self.fields[key].grid(row=i + 1, column=c, padx=2, pady=1)
            ttk.Button(self.uniform_frame, text="✕", width=3,
                       command=lambda i=i: self.remove_uniform(i)).grid(row=i + 1, column=4, padx=4)
        self.schedule()

    def add_point(self):
        span = _safe_float(self.span.get(), 20.0)
        self.point_rows.append((tk.StringVar(value="1"), tk.StringVar(value=f"{span / 2:g}")))
        self._render_loads()

    def add_uniform(self):
        span = _safe_float(self.span.get(), 20.0)
        self.uniform_rows.append((tk.StringVar(value="0.5"), tk.StringVar(value="0"),
                                  tk.StringVar(value=f"{span:g}")))
        self._render_loads()

    def remove_point(self, i):
        del self.point_rows[i]
        self._render_loads()

    def remove_uniform(self, i):
        del self.uniform_rows[i]
        self._render_loads()

    def on_material(self, keep_values=False):
        m = self.material.get()
        names = list(STEEL_SHAPES) if m == STEEL else list(LUMBER_SHAPES) if m == LUMBER else []
        self.section_cb.configure(values=names, state="readonly" if names else "disabled")
        if names and self.section.get() not in names:
            self.section.set("W12 × 26" if m == STEEL else names[0])
        if not names:
            self.section.set("")
        custom = m == CUSTOM
        for key in ("sx", "ix", "e"):
            self.fields[key].configure(state="normal" if custom else "readonly",
                                       readonlybackground="#eef1f5")
        self.section_note.configure(
            text="Custom section: values are user-entered and unverified." if custom
            else "AISC Manual Table 1-1. Fb = 24 ksi (≈0.66 Fy, Fy = 36 ksi); edit if needed."
            if m == STEEL else "Actual dressed size; NDS reference values, no adjustment factors.")
        if not keep_values:
            self.on_section()
        self.schedule()

    def on_section(self):
        m = self.material.get()
        if m in (STEEL, LUMBER) and self.section.get():
            p = section_properties(m, self.section.get())
            for key, var in (("sx", self.sx), ("ix", self.ix), ("e", self.e)):
                self.fields[key].configure(state="normal")
                var.set(f"{round(p[key], 3):g}")
                self.fields[key].configure(state="readonly")
            self.fb.set(f"{p['fb']:g}")
        self.schedule()

    # ---------------------------------------------------------- outputs
    def _build_outputs(self):
        right = ttk.Frame(self, padding=(4, 10, 10, 6))
        right.pack(side="left", fill="both", expand=True)
        self.banner = tk.Label(right, text="", bg="#fdecea", fg="#8a1c1c", anchor="w",
                               justify="left", padx=8, pady=4, font=("Segoe UI", 9))
        res = ttk.Frame(right)
        res.pack(fill="x")
        self.out = {}
        cards = [("react", "Reactions"), ("shear", "Max shear"), ("moment", "Max moment"),
                 ("bend", "Bending check"), ("defl", "Deflection check")]
        for c, (key, title) in enumerate(cards):
            f = tk.Frame(res, bg="white", highlightbackground="#dce3ed", highlightthickness=1,
                         padx=8, pady=6)
            f.grid(row=0, column=c, sticky="nsew", padx=3)
            res.columnconfigure(c, weight=1, uniform="cards")  # equal widths
            f.pack_propagate(True)
            tk.Label(f, text=title, bg="white", fg=GRAY, font=("Segoe UI", 9)).pack(anchor="w")
            big = tk.Label(f, text="—", bg="white", fg=NAVY, font=("Segoe UI", 12, "bold"),
                           anchor="w")
            big.pack(fill="x")
            small = tk.Label(f, text="", bg="white", fg="#333", font=("Segoe UI", 8),
                             justify="left", anchor="w", wraplength=150)
            small.pack(fill="x")
            f.bind("<Configure>", lambda e, s=small: s.configure(wraplength=max(80, e.width - 18)))
            self.out[key] = (big, small)
        self.banner_anchor = res
        plot = ttk.Frame(right)
        plot.pack(fill="both", expand=True, pady=(8, 0))
        self.fig = Figure(figsize=(7, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot)
        self.toolbar = NavigationToolbar2Tk(self.canvas, plot, pack_toolbar=False)
        self.toolbar.pack(side="bottom", fill="x")
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # ------------------------------------------------------ recalculation
    def schedule(self):
        if not self._loading and not self.dirty:
            self.dirty = True
            self.update_title()
        if self._pending:
            self.after_cancel(self._pending)
        self._pending = self.after(150, self.recalculate)

    def collect_raw(self):
        return dict(
            beam_type=self.beam_type.get(), span=self.span.get(), limit=self.limit.get(),
            material=self.material.get(), section=self.section.get(),
            sx=self.sx.get(), ix=self.ix.get(), e=self.e.get(), fb=self.fb.get(),
            point_loads=[(p.get(), a.get()) for p, a in self.point_rows],
            uniform_loads=[(w.get(), s.get(), e.get()) for w, s, e in self.uniform_rows])

    def recalculate(self):
        self._pending = None
        model, errors = validate_inputs(self.collect_raw())
        for key, widget in self.fields.items():
            widget.configure(bg="#ffd9d6" if key in errors else "white")
        if errors:
            self.result = None
            self.banner.configure(text="Results hidden until these inputs are fixed:\n• "
                                  + "\n• ".join(errors.values()))
            self.banner.pack(fill="x", pady=(0, 6), before=self.banner_anchor)
            for big, small in self.out.values():
                big.configure(text="—", fg=NAVY)
                small.configure(text="")
            self.fig.clear()
            self.canvas.draw_idle()
            return
        self.banner.pack_forget()
        self.result = res = analyze(model)
        self.show_results(res)
        draw_diagrams(self.fig, res)
        self.canvas.draw_idle()
        self.toolbar.update()

    def show_results(self, r):
        R = r["reactions"]
        if r["model"]["beam_type"] == SIMPLE:
            react = (f"{R['left']:.2f} / {R['right']:.2f} kip",
                     f"Left at x = 0, right at x = {r['model']['span']:g} ft\n"
                     f"ΣFy = {r['equilibrium']:.3f} kip")
        else:
            react = (f"{R['left']:.2f} kip",
                     f"Fixed-end moment {R['moment']:.2f} kip-ft\nΣFy = {r['equilibrium']:.3f} kip")
        self.out["react"][0].configure(text=react[0])
        self.out["react"][1].configure(text=react[1])
        self.out["shear"][0].configure(text=f"{r['max_shear']:.2f} kip")
        self.out["shear"][1].configure(text=f"at x = {r['max_shear_x']:.2f} ft")
        self.out["moment"][0].configure(text=f"{r['max_moment']:.2f} kip-ft")
        self.out["moment"][1].configure(text=f"at x = {r['max_moment_x']:.2f} ft")
        for key, ok, txt in (
                ("bend", r["bending_pass"],
                 f"fb = {r['fb']:.2f} ksi {'≤' if r['bending_pass'] else '>'} "
                 f"Fb = {r['Fb']:.2f} ksi\n{r['fb_ratio'] * 100:.1f}% used"),
                ("defl", r["defl_pass"],
                 f"Δ = {r['max_defl']:.3f} in {'≤' if r['defl_pass'] else '>'} "
                 f"{r['model']['limit']} = {r['allow_defl']:.3f} in\n"
                 f"at x = {r['max_defl_x']:.2f} ft, {r['defl_ratio'] * 100:.1f}% used")):
            self.out[key][0].configure(text="✔ PASS" if ok else "✘ FAIL",
                                       fg="#17795a" if ok else "#b42318")
            self.out[key][1].configure(text=txt)

    # ------------------------------------------------------------- state
    def load_state(self, st):
        """Put a design (dict of input strings, as from collect_raw) into the window."""
        self._loading = True
        try:
            self._load_state(st)
        finally:
            self._loading = False
        self.dirty = False
        self.update_title()

    def _load_state(self, st):
        self.beam_type.set(st["beam_type"])
        self.span.set(st["span"])
        self.limit.set(st["limit"])
        self.material.set(st["material"])
        self.section.set(st.get("section", ""))
        self.on_material(keep_values=True)
        if st["material"] == CUSTOM:
            for key, var in (("sx", self.sx), ("ix", self.ix), ("e", self.e)):
                var.set(st[key])
        else:
            self.on_section()
        self.fb.set(st["fb"])
        self.point_rows = [(tk.StringVar(value=str(p)), tk.StringVar(value=str(a)))
                           for p, a in st["point_loads"]]
        self.uniform_rows = [(tk.StringVar(value=str(w)), tk.StringVar(value=str(s)),
                              tk.StringVar(value=str(e))) for w, s, e in st["uniform_loads"]]
        self._render_loads()


def default_state():
    """The worked example the app opens with (spec 10)."""
    return dict(beam_type=SIMPLE, span="20", limit="L/360", material=STEEL, section="W12 × 26",
                sx="", ix="", e="", fb="24", point_loads=[("5", "12")],
                uniform_loads=[("1", "0", "20")])


# ------------------------------------------------- .beam files (spec 14.1)
BEAM_FILETYPES = [("Beam design", "*.beam"), ("All files", "*.*")]
FILE_VERSION = 1
STATE_KEYS = ("beam_type", "span", "limit", "material", "section", "sx", "ix", "e", "fb")


def design_to_json(raw):
    """Inputs exactly as entered (strings), plus a header identifying the file."""
    return {"app": APP_TITLE, "version": FILE_VERSION,
            **{k: str(raw.get(k, "")) for k in STATE_KEYS},
            "point_loads": [{"P_kip": p, "a_ft": a} for p, a in raw["point_loads"]],
            "uniform_loads": [{"w_kip_per_ft": w, "start_ft": s, "end_ft": e}
                              for w, s, e in raw["uniform_loads"]]}


def design_from_json(d):
    """Inverse of design_to_json; raises ValueError/KeyError/TypeError for a bad file."""
    if not isinstance(d, dict) or d.get("app") != APP_TITLE:
        raise ValueError("This is not a Beam Designer file.")
    if d.get("version") != FILE_VERSION:
        raise ValueError(f"Unsupported file version: {d.get('version')!r}.")
    st = {k: str(d[k]) for k in STATE_KEYS}
    if st["beam_type"] not in (SIMPLE, CANTILEVER):
        raise ValueError(f"Unknown beam type {st['beam_type']!r}.")
    if st["material"] not in (STEEL, LUMBER, CUSTOM):
        raise ValueError(f"Unknown material {st['material']!r}.")
    if st["limit"] not in LIMITS:
        raise ValueError(f"Unknown deflection limit {st['limit']!r}.")
    table = STEEL_SHAPES if st["material"] == STEEL else LUMBER_SHAPES
    if st["material"] != CUSTOM and st["section"] not in table:
        raise ValueError(f"Unknown section {st['section']!r}.")
    st["point_loads"] = [(str(p["P_kip"]), str(p["a_ft"])) for p in d["point_loads"]]
    st["uniform_loads"] = [(str(u["w_kip_per_ft"]), str(u["start_ft"]), str(u["end_ft"]))
                           for u in d["uniform_loads"]]
    return st


def _safe_float(text, default):
    try:
        v = float(text)
        return v if math.isfinite(v) and v > 0 else default
    except ValueError:
        return default


if __name__ == "__main__":
    BeamApp().mainloop()
