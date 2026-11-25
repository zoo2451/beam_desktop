# Beam Designer

## 1. Purpose

Create a clean, professional single-page beam-design tool that calculates reactions, shear,
moment, bending stress, and elastic deflection for a beam. The app shall show the beam
and loads, shear/moment/deflection diagrams, and pass/fail results for bending and
deflection.

The app shall open with a worked example beam already loaded.

## 2. Supported beam types

- Simply supported beam: one pinned support and one roller support.
- Cantilever beam: one fixed support at the left end.

No other support types or continuous beams are supported.

## 3. Coordinate and sign conventions

- All horizontal coordinates originate at the left end of the beam.
- Positive x is to the right.
- Positive vertical loads act downward.
- Positive reactions act upward.
- Shear is defined as the sum of forces to the left of a section.
- Positive moment is sagging (top in compression and bottom in tension).
- Positive deflection is downward.
- Diagram plots shall state the sign convention and display units.

## 4. Units

- Span and coordinate positions: feet (ft).
- Point loads: kips (kip).
- Distributed loads: kips per foot (kip/ft).
- Section properties: inches (in), and section modulus \(S_x\) in \(in^3\).
- Stress: ksi.
- Modulus of elasticity: ksi.
- Deflections: inches (in).
- Internal moments: kip-ft for display.
- Internal shear: kips.

The app shall perform calculations internally using consistent units and shall convert
feet to inches for deflection calculations. It shall not silently mix units.

## 5. Inputs

### 5.1 Beam geometry

- Beam type.
- Total span in feet.
- Span shall be greater than zero and at most 100 ft.
- Coordinate values shall be within \(0 <= x <= L\).

### 5.2 Loads

The app shall allow point loads and uniform distributed loads.

Point-load inputs shall include:

- Magnitude in kips.
- Horizontal position in feet from the left end.
- A downward load is entered as a positive magnitude.

Uniform-load inputs shall include:

- Magnitude in kip/ft.
- Start position.
- End position.

For uniform loads:

- Start shall be less than end.
- Start and end shall be inside the beam span.
- Overlapping uniform-load segments are allowed and shall be combined for calculations.
- A downward uniform load is entered as a positive magnitude.

At least one load shall be present. Supports, coordinate points, and load endpoints shall
be validated before any result is calculated.

## 6. Materials and section properties

The app shall include a built-in section database with a source column or source metadata.
The database may be stored in `01_data/` and loaded by `index.html`.

### 6.1 Steel

- Provide W-shapes and their `Sx`, `Ix`, and modulus of elasticity.
- Include a clearly labeled allowable bending stress or a documented method for deriving it.
- Default to E = 29,000 ksi for the supplied W-shape examples.
- Permit the user to select a built-in W-shape.

### 6.2 Lumber

- Provide common nominal lumber sizes and their actual bending-section properties.
- Record `b`, `d`, `Sx`, `Ix`, `E`, and allowable bending stress for each entry.
- Define whether allowable values are supplied directly or adjusted for design conditions.
- Permit the user to select a built-in lumber size and species/grade preset.
- Do not present nominal dimensions as actual section dimensions.

### 6.3 Custom section option

- Optional custom inputs shall include `Sx`, `Ix`, `E`, and allowable bending stress.
- Every custom value shall be positive.
- Custom values shall be treated as unverified and clearly labeled as user-entered.

## 7. Calculations

### 7.1 Statics

- Calculate reactions using static equilibrium.
- Verify \(\sum F_y = 0\) and \(\sum M = 0\).
- The app shall be numerically stable for small spans and arbitrarily placed valid loads.

### 7.2 Shear and moment

- Determine shear and moment at load discontinuities, support reactions, load endpoints,
  and critical points.
- Include the beam's absolute maximum shear and moment.
- For each diagram, plot values at enough points to show every linear or piecewise-linear
  segment exactly where practicable.
- Include the local maximum moment locations for sagging and hogging regions where
  applicable.

### 7.3 Deflection

- Use the Euler-Bernoulli beam equation:
  - \(EI y'' = M\), with a constant \(E I\).
- Neglect self-weight unless it is entered explicitly by the user.
- Neglect shear deformation.
- Apply support conditions for simply supported and cantilever beams.
- Report maximum absolute deflection and its position.
- Deflection calculations shall support point loads and uniform-load segments.
- Mixed loads shall be combined for the deflection solution.
- Plot the deflected shape relative to the undeformed beam centerline.

### 7.4 Bending stress

- Calculate maximum bending stress as:
  - \(f_b = |M_{max}| / S_x\).
- Compare the maximum bending stress with the selected allowable bending stress:
  - Pass when \(f_b <= F_b\).
  - Fail when \(f_b > F_b\).
- Report \(f_b\), \(F_b\), and the utilization ratio \(f_b / F_b\).

### 7.5 Deflection limit

- Compare maximum absolute deflection with \(L / 360\), using L in inches.
- Pass when \(|delta_max| <= L / 360\).
- Fail when \(|delta_max| > L / 360\).
- Report maximum deflection, its position, the allowable deflection, and the utilization
  ratio.

## 8. Validation

### 8.1 Required benchmark

For a 20 ft simply supported beam with a uniform load of 1 kip/ft:

- W12x26 properties shall be Sx = 33.4 in3, Ix = 204 in4, E = 29,000 ksi.
- Maximum moment shall be 50.0 kip-ft.
- Maximum deflection shall be approximately 0.609 in.
- Bending stress shall be approximately 17.96 ksi.
- Deflection limit shall be 0.667 in.
- The result shall pass both bending and deflection checks.

### 8.2 Additional test cases

The app shall be checked against or include visible hand-calculation test cases for:

- A simply supported beam with one centered point load.
- A simply supported beam with an off-center point load.
- A cantilever with an end point load.
- A cantilever with a uniformly distributed load over the full length.
- Superposition of one point load and one uniform-load segment.
- A simply supported beam with an unladen segment.
- Minimum and maximum allowed span values.
- Invalid support, load, coordinate, section, and material inputs.

For each test case, record assumptions, equations, expected values, and actual app output
in `02_validation/`.

## 9. Outputs

### 9.1 Beam and loading diagram

- Draw the beam as a horizontal member.
- Show support symbols for pinned, roller, and fixed supports.
- Display point loads with arrows and magnitudes.
- Display uniform loads with endpoints and magnitudes.
- Scale the diagram to the beam span.
- Label dimensions and units.

### 9.2 Diagrams

- Display shear, moment, and deflection diagrams with a stable, responsive SVG or canvas.
- Label axes and units.
- Mark key values and critical locations.
- Plot positive directions consistently with the sign conventions.
- Keep the zero line visible.

### 9.3 Summary

- Display reactions, maximum shear, maximum moment, maximum bending stress, maximum
  deflection, allowable bending stress, and allowable deflection.
- Display separate pass/fail indicators for bending and deflection.
- Display a missing/invalid input state instead of stale or contradictory results.

## 10. Look and feel

- Clean, modern, and professional.
- Responsive from desktop through mobile widths.
- Use clear typography and restrained engineering colors.
- Use a neutral or light application background.
- Use accessible color contrast and do not communicate pass/fail by color alone.
- Add accessible labels to inputs and diagrams.
- Include text alternatives or values for plotted critical results.

## 11. Error handling

- Highlight invalid fields and provide a concise explanation next to each invalid field.
- Do not calculate or draw results while required inputs are invalid.
- Prevent NaN, Infinity, stale values, and overlapping zero-length ranges.
- For cantilever equilibrium, verify the fixed reaction and reaction moment.
- For unsupported configurations or failed convergence, display a clear error instead of
  a success-shaped fallback.

## 12. Project organization

- `index.html` is the complete app and GitHub Pages entry point.
- `spec.md` documents the product and engineering requirements.
- `prompts.md` records request history.
- `00_planning/` contains notes and sketches.
- `01_data/` contains section and material data.
- `02_validation/` contains hand calculations and test cases.
- `03_output/` contains screenshots and exported results.
- Supporting app files are not created; the implementation shall remain in `index.html`.

## 13. Out of scope

- Continuous beams.
- Buckling and lateral-torsional stability.
- Shear strength and shear stress checks.
- Torsion.
- Beam self-weight unless explicitly entered as a uniform load.
- Deflection due to support settlement.
- Dynamic, fatigue, creep, or nonlinear material behavior.
- Axial loading.
- Live-load redistribution or load-duration adjustments.