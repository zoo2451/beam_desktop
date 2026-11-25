# Prompt Log

## 2026-11-24

- **Asked:** Set up the beam_desktop project: copy spec.md and index.html from the web Beam Designer (beam_app), and create AGENTS.md with the prompt-log and commit-after-each-request lines.
- **Changed:** Initialized a Git repository, copied `spec.md` and `index.html` from `beam_app/`, and created `AGENTS.md` and this `prompts.md`. Checked that numpy 2.3.2 and matplotlib 3.11.0 are installed and Tkinter 8.6 imports.
- **Result:** Succeeded.

- **Asked:** Update spec.md to describe a Python desktop app using Tkinter. Don't build anything.
- **Changed:** Rewrote `spec.md` for a Tkinter + numpy + matplotlib desktop app started with `python app.py`: added a Platform section and an inputs table (adding a deflection-limit dropdown, L/180-L/480), and put the statics, shear/moment, deflection (EI v″ = −M), and check equations in writing. Replaced the web-only items (SVG, GitHub Pages, numbered folders, responsive layout) with desktop equivalents. Wrote 10 validation cases with expected values worked by hand from the AISC Table 3-23 formulas. Corrected the lumber data: the web app's 4×12 S and I did not match 3.5 × 11.25 in, and its F<sub>b</sub> = 1.5 ksi exceeded the NDS DF-L No. 2 value of 0.900 ksi. "Saving designs" stays in Out of scope for now.
- **Result:** Succeeded. No code written.

- **Asked:** Read spec.md and build the desktop app it describes, using index.html as a reference for how the app should behave.
- **Changed:** Created `app.py`:
  - Tkinter inputs on the left: beam type, span, deflection limit, material/section with S<sub>x</sub>/I<sub>x</sub>/E/F<sub>b</sub>, and point and uniform load rows with add/remove.
  - Five result cards: reactions, max shear, max moment, and PASS/FAIL for bending and deflection.
  - An embedded matplotlib figure with beam/loads, shear, moment, and deflection panels, plus the navigation toolbar.
  - Calculations are Tk-free functions (`validate_inputs`, `reactions`, `shear_at`, `moment_at`, `analyze`) on a 2,000-interval grid plus load breakpoints and V = 0 crossings; deflection comes from double trapezoid integration of −M/EI.
  - Invalid fields turn red, a banner lists each problem, and results and diagrams are hidden.
  - While porting, three web-app steel entries failed the S<sub>x</sub> ≈ 2I<sub>x</sub>/d check (W10×12 S<sub>x</sub> 12.6 → 10.9, W10×22 26.0 → 23.2, W14×30 42.7/290 → 42.0/291) and were corrected to AISC values.
  - First screenshots showed E as "2.9e+04", clipped text in the result cards, the max-shear label cut off at the right edge, and "≤ …?" wording on a failing check. All fixed.
- **Result:** Works. The example beam, a cantilever with lumber, and an invalid-input state were all checked with screenshots. A quick run of the validation inputs matched every hand value except case 3 deflection (app 0.340 in at 8.82 ft vs. spec 0.325 in at 7.64 ft), which is investigated in the validation step.

- **Asked:** Run all of the validation cases in spec.md against the app's beam calculations and report a table of expected versus actual values.
- **Changed:** Added `validate.py`, which runs cases 1-10 through the app's own calculation functions and prints an expected-vs-actual table at the spec's decimal places. Case 3 deflection disagreed (app 0.340 in at 8.82 ft vs. spec 0.325 in at 7.64 ft). Investigated and showed the work: the spec's hand calculation was wrong, because it used b = 15 ft in Δ = Pc(L² − c²)<sup>3/2</sup>/(9√3 L EI) where c must be the shorter distance (5 ft). Redone, and cross-checked with the AISC Table 3-23 a > b form, it gives 0.340 in at 8.82 ft, so the app was right. Corrected case 3 in `spec.md` and added section 12.1 Validation results with the work and the full table, plus a blank line for the student's own in-app check of case 1.
- **Result:** 50/50 checks pass.

- **Asked:** Add Save and Open: a File menu that saves the beam (support type, span, section, deflection limit, loads) to a file and opens it again. Remove "Saving designs" from Out of scope first. Then rerun the validation cases.
- **Changed:** Removed "Saving designs" from Out of scope and added spec section 14.1. Added a File menu (New, Open…, Save, Save As…, Quit, with Ctrl shortcuts). Designs are `.beam` JSON files holding every input exactly as typed, with an app/version header (`design_to_json` / `design_from_json`). The window title shows the file name and `*` for unsaved changes, and New/Open/Quit ask before discarding them. Bad files show an error and keep the current design.
- **Result:** Works. Saved a cantilever with a custom section and two point loads, used New, and reopened it: every input was identical, and the fixed-end moment (−158.44 kip-ft) matched a hand check. A design with an invalid span ("abc") saved and reopened with results hidden. A non-Beam-Designer file was rejected. Validation reran: 50/50 pass.

- **Asked:** Add an Export results button that saves a table of x, V, M, and deflection along the beam to a CSV file that opens in Excel. Then rerun the validation cases.
- **Changed:** Added spec section 14.2. Added an Output group with an "Export results (CSV)…" button, also in the File menu. `results_table` evaluates V and M exactly at every 1/200 of the span, every load position, load endpoint, and support, and every V = 0 point, with two rows at each point load (V just left and just right). Deflection is interpolated from the 2,000-interval solution. Written UTF-8 with BOM so Excel reads the units. The button disables while inputs are invalid.
- **Result:** Works. For the example beam the CSV has 202 rows; its largest M is 72.00 kip-ft at 12 ft, matching the app, and the shear jump at the 5 kip load shows as 0.00 → −5.00 kip. Validation reran: 50/50 pass.
