# PLanet 
The PLanet web interface for specifying and analyzing assignment procedures in
the design of experiments using the [PLanet
DSL](https://pypi.org/project/planet-dsl/). PLanet lets you
interactively build experimental designs, inspect their statistical properties,
and compare tradeoffs between designs. The PLanet DSL serves as the basis for
the graphical interface. View PLanet DSL's source code and more information at
https://anonymous.4open.science/r/PLanet-BFD0.

Play with the interface at https://experiment-interface-589760482620.us-central1.run.app.


## Table of Contents

1. [Installation](#installation)
2. [Interface Overview](#interface-overview)
3. [Step 1 — Variables](#step-1--variables)
4. [Step 2 — Designs](#step-2--designs)
5. [Step 3 — Composition](#step-3--composition)
6. [Running a Design](#running-a-design)
7. [Results](#results)
8. [Analysis](#analysis)
9. [Comparing Designs](#comparing-designs)
10. [Exporting](#exporting)
11. [Advanced: Repeat Blocks](#advanced-repeat-blocks)
12. [Local GUI (no browser)](#local-gui-no-browser)

---

## Installation

**Requirements:** Python 3.9+

### 1. Clone the repository

```bash
git clone <repo-url>
cd experiment-interface
```

### 2. Start the server

```bash
./run.sh
```

On first run, `run.sh` automatically:
1. Creates a `.venv` virtual environment
2. Installs all dependencies (`planet-dsl`, `fastapi`, `uvicorn`, `pandas`)
3. Starts the server at [http://127.0.0.1:8000](http://127.0.0.1:8000)

Subsequent runs skip setup and start the server immediately.

### 3. Open the interface

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

To stop the server, press `Ctrl+C` in the terminal.

> **Note:** If `./run.sh` is not executable, run `chmod +x run.sh` first.

---

## Interface Overview

The interface has two panels:

- **Left panel** — Build your experiment top-to-bottom: define variables, create designs, and compose them. The **Units** count, **Analyze**, **Compare**, and **Run ▶** buttons sit at the bottom.
- **Right panel** — View results: analysis, plans, participant assignments, and generated code.

---

## Variables

Variables are the independent variables in your experiment. Each has a **name** and a list of **conditions** (levels).

The interface starts with one blank variable. Type a name, then type each condition and press **Enter** or **Tab** to add it. Click **+ variable** to add more.

### Multifactor variables

Click **+ multifact** to create a variable that jointly represents the combinations of two or more existing variables. Select the component variables from the dropdown. Multifactor variables are useful when you want to counterbalance the *joint ordering* of multiple factors as a single unit rather than independently.

> **Example:** A multifactor of `interface` (2 levels) × `task` (3 levels) creates 6 combined conditions: `baseline-creation`, `baseline-editing`, etc.

---

## Designs

A design specifies *how* variables are assigned to participants. Click **+ design**, then **+ add variable** inside the design card to assign variables to it.

### Within vs. between subjects

Each variable in a design is toggled as:

- **WS (Within-subjects)**: every participant two or more conditions
- **BS (Between-subjects)**: each participant sees only one condition

### Annotations

For within-subjects variables, select how conditions are ordered:

| Annotation | Meaning |
|---|---|
| **Randomized** | Conditions are randomly assigned without counterbalancing |
| **Counterbalance** | Conditions are counterbalanced, ensuring each condition appears an equal number of times in each position  |
| **Fixed order** | All participants see conditions in a fixed sequence |

### limit_plans

`limit_plans` caps the number of counterbalancing plans generated. By default,
PLanet generates the full set required for complete counterbalancing.
Restricting this to the number of conditions of one variable reslts in a Latin
square.


### num_trials

`num_trials` sets the number of trials per participant. Defaults to the number of conditions.

---

## Composition

Compositions combine two designs into a single experiment structure. Click **+ composition** and select a type:

| Type | Meaning |
|---|---|
| **Nest** | Conditions in each row of the inner design repeat within each block of the outer design. |
| **Cross** | Both designs are superimposed.  |

Nesting and crossing returns a design object, so they can be arbitrarily
composed to create complex designs.


## Run

Set the **Participants** count at the bottom of the left panel, then click **Run ▶**.

PLanet generates plans and assigns participants to them.
For large designs (many conditions or a large plan space), this can take time.
The button turns red and shows **Cancel** while running. Click the button to
cancel the run. If the design requires more plans than participants (e.g., 8
plans but only 6 participants), an error is shown with the minimum participant
count needed.

---

## Results

After a successful run, the right panel shows three tabs:

**Plans** — Each counterbalancing plan is a row and trials are columns. Conditions are color-coded consistently throughout the interface.

**Assignment** — Shows each participant's ID and which plan they are assigned to.

**Code** — The generated PLanet Python code for the current design. Copy it into a script for programmatic use or to reproduce the design exactly.

---

## Analysis

Click **Analyze** to inspect the statistical properties of your design without generating plans. Analysis is fast even for large designs.

The analysis card shows four categories:

| Category | Meaning |
|---|---|
| **Main Effects** | Variables whose main effect is testable |
| **Interaction Effects** | Variable combinations whose interaction effect is testable |
| **Time-based Effects** | Variables whose time-based effect is estimable |
| **Within-Subjects Comparisons** | Variables for which every participant sees every testable |

### Assumption warnings

A **⚠** icon appears on a main or interaction effect when estimating it requires an assumption. Hover over the icon to read the assumption.

This occurs when a confounding effect (time-varying or interaction) may exist
but the design cannot account for them. 

---

## Comparing Designs

When two or more designs are defined, a **Compare** button appears. Select two
designs from the dropdowns and click **Compare**.

The comparison view shows a table of all testable effects grouped into **Main
Effects**, **Interaction Effects**, and **Time-Varying Effects**. Each row shows whether the effect is
estimable (✓) or not (—) in each design.

Below the table, a **Power Advantage** summary indicates which design is more
efficient (e.g., requires fewer participants) to test each effect.

## Advanced: Repeat Blocks
To have participants complete **multiple repetitions** of a design, use an empty design nested around your main design:

1. Create a new design with **no variables** assigned
2. Set its `num_trials` to the desired number of repetitions
3. Create a **Nest** composition with the empty design as **outer** and your real design as **inner**

---

## Local GUI (no browser)

PLanet Composer also runs as a standalone desktop application using
[pywebview](https://pywebview.flowrl.com/), with no browser or server required:

```bash
python gui.py
```

The local GUI is functionally identical to the web app.

## Project Structure

```
app.py           # FastAPI backend — generates and executes PLanet code
index.html       # Web app frontend (vanilla JS, no build step)
gui.py           # Local desktop GUI (pywebview)
gui.html         # GUI frontend (mirrors index.html)
run.sh           # Web app start script (sets up venv on first run)
run_gui.sh       # Local GUI start script
requirements.txt
docs/
```
