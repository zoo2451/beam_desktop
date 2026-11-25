# Beam Designer (Desktop)

A Tkinter desktop app for single-span steel or lumber beams, either simply supported or cantilever. Enter the span, a section, and any mix of point and uniform loads. The app shows the reactions, the shear, moment, and deflection diagrams, and PASS/FAIL checks for bending stress and an L/n deflection limit.

The File menu can:
- save and open designs (`.beam` files)
- export x, V, M, and deflection along the beam to a CSV file that opens in Excel
- make a one-page PDF calculation sheet

## Install

You need Python 3.10 or newer. Tkinter is included with the python.org installer.

```
pip install numpy matplotlib
```

## Run

```
python app.py
```

On Macs where `python` isn't Python 3, use `pip3` and `python3`.

## Check the calculations

```
python validate.py
```

This runs the validation cases in [spec.md](spec.md) and prints a table of expected versus actual values.
