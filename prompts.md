# Prompt Log

## 2026-11-24

- **Asked:** Set up the beam_desktop project: copy spec.md and index.html from the web Beam Designer (beam_app), and create AGENTS.md with the prompt-log and commit-after-each-request lines.
- **Changed:** Initialized a Git repository, copied `spec.md` and `index.html` from `beam_app/`, and created `AGENTS.md` and this `prompts.md`. Checked that numpy 2.3.2 and matplotlib 3.11.0 are installed and Tkinter 8.6 imports.
- **Result:** Succeeded.

- **Asked:** Update spec.md to describe a Python desktop app using Tkinter. Don't build anything.
- **Changed:** Rewrote `spec.md` for a Tkinter + numpy + matplotlib desktop app started with `python app.py`: added a Platform section and an inputs table (adding a deflection-limit dropdown, L/180-L/480), and put the statics, shear/moment, deflection (EI v″ = −M), and check equations in writing. Replaced the web-only items (SVG, GitHub Pages, numbered folders, responsive layout) with desktop equivalents. Wrote 10 validation cases with expected values worked by hand from the AISC Table 3-23 formulas. Corrected the lumber data: the web app's 4×12 S and I did not match 3.5 × 11.25 in, and its F<sub>b</sub> = 1.5 ksi exceeded the NDS DF-L No. 2 value of 0.900 ksi. "Saving designs" stays in Out of scope for now.
- **Result:** Succeeded. No code written.
