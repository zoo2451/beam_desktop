# Beam Designer (Desktop)

## 1. Purpose

A Python desktop app, built with Tkinter, that calculates reactions, shear, moment, bending stress, and elastic deflection for a single-span beam. It shows the beam and its loads, shear/moment/deflection diagrams, and pass/fail results for bending and deflection. It is for engineering students and engineers sizing a steel or lumber beam.

It is a port of the Beam Designer web app (`index.html`, kept in this folder as a reference for behavior). The app opens with a worked example beam already loaded and is started with `python app.py`.

## 2. Platform

- Python 3.10 or newer, using Tkinter (part of the standard library) for the window and controls.
- numpy for calculations; matplotlib, embedded in the window with `FigureCanvasTkAgg`, for the diagrams.
- Runs on Windows and macOS (use `python3` on Macs where `python` is not Python 3).
- A single source file, `app.py`. Calculation functions do not depend on Tkinter, so they can be tested without opening a window.
- Results recalculate automatically whenever any input changes; no internet connection is needed.

## 3. Supported beam types

- Simply supported beam: pin at x = 0 and roller at x = L.
- Cantilever beam: fixed support at x = 0, free at x = L.

No other support types or continuous beams.

## 4. Coordinate and sign conventions

- x is measured from the left end of the beam; positive x is to the right.
- Positive applied loads act downward; positive reactions act upward.
- Shear V is the sum of forces to the left of a section (upward positive).
- Positive moment M is sagging (top in compression, bottom in tension).
- Positive deflection is downward.
- Each diagram states its sign convention and units.

## 5. Units

| Quantity | Unit |
|---|---|
| Span, positions | ft |
| Point loads | kip |
| Distributed loads | kip/ft |
| Section modulus S<sub>x</sub> | in³ |
| Moment of inertia I<sub>x</sub> | in⁴ |
| E, stresses | ksi |
| Shear | kip |
| Moment | kip-ft (converted to kip-in for stress and deflection) |
| Deflection | in |

The app converts feet to inches for stress and deflection and never mixes units silently.

## 6. Inputs

| Input | Unit | Range / rule | Default | Control |
|---|---|---|---|---|
| Beam type | - | Simply supported or Cantilever | Simply supported | Dropdown |
| Span L | ft | 0 < L ≤ 100 | 20 | Entry |
| Material | - | Steel W-shape, Lumber, or Custom section | Steel W-shape | Dropdown |
| Section | - | From the built-in tables (section 7) | W12 × 26 | Dropdown |
| Allowable bending stress F<sub>b</sub> | ksi | > 0 | From the section table | Entry (editable) |
| Custom S<sub>x</sub>, I<sub>x</sub>, E | in³, in⁴, ksi | each > 0 | 33.4, 204, 29000 | Entries (enabled only for Custom section) |
| Deflection limit | - | L/180, L/240, L/360, L/480 | L/360 | Dropdown |
| Point loads | kip, ft | P > 0; 0 ≤ a ≤ L | One load: 5 kip at 12 ft | Table with Add / Remove and editable cells |
| Uniform loads | kip/ft, ft | w > 0; 0 ≤ start < end ≤ L | One load: 1 kip/ft from 0 to 20 ft | Table with Add / Remove and editable cells |

- At least one load is required.
- Overlapping uniform loads are allowed and are added together.
- Every field is checked before any result is calculated. An invalid field is highlighted, and a message explains the problem.

## 7. Materials and section properties

Section data is built into `app.py`, with its source noted.

- **Steel W-shapes** (AISC *Steel Construction Manual*, Table 1-1): W8×10, W10×12, W10×22, W12×26, W14×22, W14×30, W16×26, W18×35, W21×44, W24×55, with S<sub>x</sub>, I<sub>x</sub>, d, b<sub>f</sub>, and A. E = 29,000 ksi. The default F<sub>b</sub> = 24 ksi (≈ 0.66 F<sub>y</sub> for F<sub>y</sub> = 36 ksi, a simplified allowable-stress value that the user may edit).
- **Lumber:** 2×10, 2×12, and 4×12 Douglas Fir-Larch No. 2.
  - Properties use the actual dressed sizes (1.5 × 9.25, 1.5 × 11.25, and 3.5 × 11.25 in), with S = bd²/6 and I = bd³/12.
  - Reference values come from the NDS Supplement: F<sub>b</sub> = 0.900 ksi and E = 1,600 ksi, used directly with no adjustment factors.
  - Nominal sizes are never shown as actual dimensions.
  - *Correction from the web app:* its 4×12 entry had S and I that do not match 3.5 × 11.25 in, and its lumber F<sub>b</sub> of 1.5 ksi exceeds the NDS reference value.
- **Custom section:** the user enters S<sub>x</sub>, I<sub>x</sub>, E, and F<sub>b</sub>. These are labeled "user-entered, unverified."

## 8. Calculations

### 8.1 Reactions (statics)

With W = ΣP<sub>i</sub> + Σw<sub>j</sub>(e<sub>j</sub> − s<sub>j</sub>) and M<sub>0</sub> = ΣP<sub>i</sub>a<sub>i</sub> + Σw<sub>j</sub>(e<sub>j</sub> − s<sub>j</sub>)(s<sub>j</sub> + e<sub>j</sub>)/2 (the moment of the loads about x = 0):

- **Simply supported:** R<sub>R</sub> = M<sub>0</sub>/L and R<sub>L</sub> = W − R<sub>R</sub>.
- **Cantilever:** R = W, and the fixed-end moment M<sub>fixed</sub> = −M<sub>0</sub> (hogging).
- The app shows the equilibrium check ΣF<sub>y</sub> = R − W = 0.

### 8.2 Shear and moment

- V(x) = R<sub>L</sub> − Σ<sub>a<sub>i</sub> ≤ x</sub> P<sub>i</sub> − Σ w<sub>j</sub> · (overlap of [s<sub>j</sub>, e<sub>j</sub>] with [0, x]).
- M(x) is the moment of all forces to the left of x, including the fixed-end moment for a cantilever.
- Values are computed on a grid of 2,000 intervals plus every load position, load endpoint, and support. Both sides of each point-load jump are included, and every point where V changes sign is added, so the maxima are exact.
- Report the maximum |V| and the maximum |M|, each with its location.

### 8.3 Deflection

- Euler-Bernoulli beam theory with constant EI: EI v″ = −M(x), where v is the downward deflection and M is in kip-in.
- Integrate twice numerically (trapezoid rule on the grid above).
  - **Simply supported:** v(0) = v(L) = 0.
  - **Cantilever:** v(0) = v′(0) = 0.
- Neglect shear deformation and self-weight (self-weight may be entered as a uniform load).
- Report the maximum |v| and its location.

### 8.4 Checks

- **Bending stress:** f<sub>b</sub> = |M<sub>max</sub>| × 12 / S<sub>x</sub> (ksi). PASS if f<sub>b</sub> ≤ F<sub>b</sub>. Report f<sub>b</sub>, F<sub>b</sub>, and the ratio f<sub>b</sub>/F<sub>b</sub>.
- **Deflection:** Δ<sub>allow</sub> = 12L / n for the chosen limit L/n (in). PASS if |v|<sub>max</sub> ≤ Δ<sub>allow</sub>. Report both values and the ratio.

## 9. Outputs

- **Results panel:**
  - reactions (and the fixed-end moment for a cantilever), with the ΣF<sub>y</sub> check
  - max shear and max moment
  - f<sub>b</sub>, max deflection, and Δ<sub>allow</sub>
  - separate PASS/FAIL labels for bending and deflection, shown in words and color, not color alone
- **Diagrams:** an embedded matplotlib figure with four stacked panels sharing the x axis (ft):
  1. **Beam and loads:** the beam line, support symbols (pin, roller, fixed), point-load arrows with values, and uniform-load blocks with values.
  2. **Shear V** (kip).
  3. **Moment M** (kip-ft).
  4. **Deflection** (in; downward is plotted down).

  Each panel has a zero line and labeled maximum values.
- **Invalid input:** the diagrams and results clear, and a banner says what to fix. Stale results are never shown.

## 10. Look and feel

- One resizable window, about 1280 × 800. Inputs are on the left in labeled groups (Beam, Section, Loads); the results and diagrams are on the right.
- Restrained engineering colors (navy and blue, with orange accents, on a light background); every field is labeled with its units.
- The window opens with the example beam already calculated: a 20 ft W12 × 26 with 1 kip/ft over the full span plus 5 kip at 12 ft.

## 11. Error handling

- Highlight each invalid field and explain why; do not calculate while any input is invalid.
- Never display NaN or Infinity.
- Reject zero-length or reversed uniform-load ranges.
- For any unsupported configuration, show a clear error instead of a result that looks valid.

## 12. Validation

All cases use W12 × 26 (S<sub>x</sub> = 33.4 in³, I<sub>x</sub> = 204 in⁴, E = 29,000 ksi, F<sub>b</sub> = 24 ksi) and L/360 unless noted. Expected values were worked by hand from the standard beam formulas (AISC Manual, Table 3-23).

| # | Case | Expected |
|---|---|---|
| 1 | Simply supported, L = 20 ft, w = 1 kip/ft over the full span (required benchmark) | R<sub>L</sub> = R<sub>R</sub> = 10.00 kip; M<sub>max</sub> = wL²/8 = 50.00 kip-ft at 10.0 ft; Δ = 5wL⁴/384EI = 0.609 in; f<sub>b</sub> = 17.96 ksi; Δ<sub>allow</sub> = 0.667 in; bending PASS, deflection PASS |
| 2 | Simply supported, L = 20 ft, P = 10 kip at 10 ft | R = 5.00 kip each; M<sub>max</sub> = PL/4 = 50.00 kip-ft; Δ = PL³/48EI = 0.487 in at 10.0 ft |
| 3 | Simply supported, L = 20 ft, P = 10 kip at a = 5 ft (b = 15 ft) | R<sub>L</sub> = 7.50, R<sub>R</sub> = 2.50 kip; M<sub>max</sub> = Pab/L = 37.50 kip-ft at 5.0 ft; Δ = Pc(L² − c²)<sup>3/2</sup>/(9√3 L EI), with c the *shorter* distance (5 ft) = 0.340 in, at √((L² − c²)/3) = 11.18 ft from the right end = 8.82 ft from the left. *(Corrected; see 12.1.)* |
| 4 | Cantilever, L = 10 ft, P = 5 kip at 10 ft | R = 5.00 kip; M<sub>fixed</sub> = −50.00 kip-ft; Δ = PL³/3EI = 0.487 in at 10.0 ft |
| 5 | Cantilever, L = 10 ft, w = 1 kip/ft over the full span | R = 10.00 kip; M<sub>fixed</sub> = −50.00 kip-ft; Δ = wL⁴/8EI = 0.365 in at 10.0 ft |
| 6 | Superposition: the loads of cases 1 and 2 together | M<sub>max</sub> = 100.00 kip-ft; Δ = 0.609 + 0.487 = 1.095 in; f<sub>b</sub> = 35.93 ksi; bending FAIL, deflection FAIL |
| 7 | Simply supported, L = 20 ft, w = 2 kip/ft from 0 to 10 ft (unladen segment) | R<sub>L</sub> = 15.00, R<sub>R</sub> = 5.00 kip; M<sub>max</sub> = R<sub>L</sub>²/2w = 56.25 kip-ft at 7.5 ft |
| 8 | Property check: symmetry and proportionality | Case 1 gives R<sub>L</sub> = R<sub>R</sub> and v(x) = v(L − x); doubling every load in case 3 doubles every reaction, M<sub>max</sub>, and Δ (ratio 2.000) |
| 9 | Span limits | L = 100 ft calculates; L = 0 and L = 101 are rejected |
| 10 | Invalid inputs | No loads; a point load at 25 ft on a 20 ft span; uniform start ≥ end; custom I<sub>x</sub> ≤ 0; a non-numeric span. Each is rejected with a message, and no results are shown |

### 12.1 Validation results

The agent ran `python validate.py` on 2026-11-24; it checks the app's calculation functions (the same ones the window uses) against the expected values above, at the number of decimal places given.

**Case 3 correction.** The first run disagreed with the spec: the app gave 0.340 in at 8.82 ft, but the spec expected 0.325 in at 7.64 ft. Checking the work showed the *expected value* was wrong. The formula Δ<sub>max</sub> = Pc(L² − c²)<sup>3/2</sup>/(9√3 L EI) requires c to be the *shorter* of the two distances from the load to the supports, and the spec had used b = 15 ft instead of 5 ft. Redone with c = 5 ft = 60 in, L = 240 in, EI = 29,000 × 204 = 5,916,000 kip-in²:

- Δ<sub>max</sub> = 10 × 60 × (240² − 60²)<sup>1.5</sup> / (9√3 × 240 × 5,916,000) = 600 × 54,000<sup>1.5</sup> / 2.2133 × 10<sup>10</sup> = **0.340 in**.
- Location: √((240² − 60²)/3) = 134.2 in = 11.18 ft from the right support, so x = **8.82 ft**.
- Cross-check with AISC Table 3-23 case 8 (a > b form, mirrored): Pab(a + 2b)√(3a(a + 2b)) / (27 EI L) = 0.340 in. The app was right, and the spec was corrected.

| Case | Quantity | Expected | Actual | Result |
|---|---|---|---|---|
| 1 | R_L (kip) | 10.00 | 10.00 | PASS |
| 1 | R_R (kip) | 10.00 | 10.00 | PASS |
| 1 | M_max (kip-ft) | 50.00 | 50.00 | PASS |
| 1 | M_max location (ft) | 10.0 | 10.0 | PASS |
| 1 | Δ_max (in) | 0.609 | 0.609 | PASS |
| 1 | f_b (ksi) | 17.96 | 17.96 | PASS |
| 1 | Δ_allow L/360 (in) | 0.667 | 0.667 | PASS |
| 1 | Bending check | PASS | PASS | PASS |
| 1 | Deflection check | PASS | PASS | PASS |
| 2 | R_L = R_R (kip) | 5.00 | 5.00 | PASS |
| 2 | M_max (kip-ft) | 50.00 | 50.00 | PASS |
| 2 | Δ_max (in) | 0.487 | 0.487 | PASS |
| 2 | Δ_max location (ft) | 10.0 | 10.0 | PASS |
| 3 | R_L (kip) | 7.50 | 7.50 | PASS |
| 3 | R_R (kip) | 2.50 | 2.50 | PASS |
| 3 | M_max (kip-ft) | 37.50 | 37.50 | PASS |
| 3 | M_max location (ft) | 5.0 | 5.0 | PASS |
| 3 | Δ_max (in) | 0.340 | 0.340 | PASS |
| 3 | Δ_max location (ft) | 8.82 | 8.82 | PASS |
| 4 | R (kip) | 5.00 | 5.00 | PASS |
| 4 | M_fixed (kip-ft) | -50.00 | -50.00 | PASS |
| 4 | Δ_max (in) | 0.487 | 0.487 | PASS |
| 4 | Δ_max location (ft) | 10.0 | 10.0 | PASS |
| 5 | R (kip) | 10.00 | 10.00 | PASS |
| 5 | M_fixed (kip-ft) | -50.00 | -50.00 | PASS |
| 5 | Δ_max (in) | 0.365 | 0.365 | PASS |
| 5 | Δ_max location (ft) | 10.0 | 10.0 | PASS |
| 6 | M_max (kip-ft) | 100.00 | 100.00 | PASS |
| 6 | Δ_max (in) | 1.095 | 1.095 | PASS |
| 6 | f_b (ksi) | 35.93 | 35.93 | PASS |
| 6 | Bending check | FAIL | FAIL | PASS |
| 6 | Deflection check | FAIL | FAIL | PASS |
| 7 | R_L (kip) | 15.00 | 15.00 | PASS |
| 7 | R_R (kip) | 5.00 | 5.00 | PASS |
| 7 | M_max (kip-ft) | 56.25 | 56.25 | PASS |
| 7 | M_max location (ft) | 7.5 | 7.5 | PASS |
| 8 | Symmetry: R_L − R_R, case 1 (kip) | 0.000 | 0.000 | PASS |
| 8 | Symmetry: largest difference v(x) − v(L−x), case 1 (in) | 0.000 | 0.000 | PASS |
| 8 | Proportionality: R_L(2P) / R_L(P), case 3 | 2.000 | 2.000 | PASS |
| 8 | Proportionality: R_R(2P) / R_R(P), case 3 | 2.000 | 2.000 | PASS |
| 8 | Proportionality: M_max(2P) / M_max(P), case 3 | 2.000 | 2.000 | PASS |
| 8 | Proportionality: Δ_max(2P) / Δ_max(P), case 3 | 2.000 | 2.000 | PASS |
| 9 | L = 100 ft calculates | calculates | calculates | PASS |
| 9 | L = 0 ft rejected | rejected | rejected: Span must be greater than zero. | PASS |
| 9 | L = 101 ft rejected | rejected | rejected: Span must not exceed 100 ft. | PASS |
| 10 | No loads | rejected with message | rejected: Add at least one load. | PASS |
| 10 | Point load at 25 ft on 20 ft span | rejected with message | rejected: Point load 1 position must be between 0 and 20 ft. | PASS |
| 10 | Uniform start ≥ end | rejected with message | rejected: Uniform load 1 end must be greater than its start. | PASS |
| 10 | Custom Ix ≤ 0 | rejected with message | rejected: Moment of inertia Ix must be greater than zero. | PASS |
| 10 | Non-numeric span | rejected with message | rejected: Span must be a number. | PASS |

50/50 checks passed

**My check in the app:** I entered case 1 (simply supported, 20 ft, W12 × 26, 1 kip/ft from 0 to 20 ft, no point load) and saw: R = ____ / ____ kip, M<sub>max</sub> = ____ kip-ft, f<sub>b</sub> = ____ ksi, Δ = ____ in, bending ____, deflection ____. *(fill in)*

## 13. Out of scope

- Continuous beams and other support types.
- Buckling and lateral-torsional stability.
- Shear strength and shear stress checks.
- Torsion and axial load.
- Self-weight unless it is entered as a uniform load.
- Support settlement.
- Dynamic, fatigue, creep, or nonlinear material behavior.
- Load combinations and lumber adjustment factors.

## 14. Desktop features

### 14.1 Save and Open
- A **File** menu with New (reset to the example beam), Open…, Save, Save As…, and Quit. Keyboard shortcuts: Ctrl+N, Ctrl+O, Ctrl+S, Ctrl+Shift+S.
- A design is saved as a `.beam` file: JSON text holding the app name, a file-format version, and every input exactly as entered:
  - support type, span, and deflection limit
  - material and section, with S<sub>x</sub>, I<sub>x</sub>, E, and F<sub>b</sub>
  - point loads (P, a) and uniform loads (w, start, end)
- Opening a file restores every input and recalculates. A design with invalid inputs can still be saved and reopened, so work in progress is not lost.
- The window title shows the file name, with `*` when there are unsaved changes. New, Open, and Quit ask before discarding unsaved changes.
- A file that is not a valid `.beam` file shows an error, and the current design is kept.

### 14.2 Export results
- An **Export results (CSV)…** button (also in the File menu) saves a table along the beam to a `.csv` file that opens directly in Excel (UTF-8 with BOM, so the units show correctly).
- Columns: `x (ft)`, `V (kip)`, `M (kip-ft)`, and `deflection (in, down +)`.
- Rows:
  - every 1/200 of the span
  - every load position, load endpoint, and support
  - every point where V = 0
- At a point load, x appears twice: first with V just left of the load, then just right of it, so the shear jump is visible.
- V and M are exact at each x; the deflection is interpolated from the 2,000-interval solution.
- The button is disabled, and the menu item shows a message, while inputs are invalid.

### 14.3 Calculation sheet (PDF)
- A **Calculation sheet (PDF)…** button (also in the File menu) saves a one-page, letter-size (8.5 × 11 in) PDF that is ready to hand in with a design. It is made with matplotlib's PDF backend; no extra packages are needed.
- **Header:** title, design file name, date, and blank "Project", "By", and "Checked" lines.
- **Inputs at the top:** beam type, span, section and its source, S<sub>x</sub>, I<sub>x</sub>, E, F<sub>b</sub>, the deflection limit, and tables of the point and uniform loads.
- **Results and checks:**
  - reactions (and fixed-end moment) with ΣF<sub>y</sub>
  - max V and max M with their locations
  - the bending check, written out as f<sub>b</sub> = |M<sub>max</sub>|·12/S<sub>x</sub>, and the deflection check against L/n, each with its numbers, ratio, and a boxed PASS/FAIL
- **Diagrams:** the same beam/loads, shear, moment, and deflection panels as the app.
- **Footer:** sign conventions, method (Euler-Bernoulli, constant EI), and the out-of-scope items (no shear, buckling, or self-weight unless entered).
- Disabled while inputs are invalid.
