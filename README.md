# PLanet Composer

A web-based interface for composing and analyzing within-subjects, between-subjects, and mixed HCI experiments using the [PLanet DSL](https://pypi.org/project/planet-dsl/). PLanet Composer lets you interactively build experimental designs, inspect their statistical properties, compare tradeoffs between designs, and generate counterbalancing plans and participant assignments — without writing any code.

![Interface overview](docs/images/overview.png)
*The PLanet Composer interface. Left panel: Variables → Designs → Composition → Run. Right panel: Analysis and Results.*

---

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

```bash
git clone <repo-url>
cd experiment-interface
./run.sh
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

On first run, `run.sh` automatically creates a `.venv` virtual environment and installs all dependencies (`planet-dsl`, `fastapi`, `uvicorn`, `pandas`). Subsequent runs skip this step and start the server immediately.

---

## Interface Overview

The interface has two panels:

- **Left panel** — Build your experiment top-to-bottom: define variables, create designs, and compose them. The **Participants** count, **Analyze**, **Compare**, and **Run ▶** buttons sit at the bottom.
- **Right panel** — View results: analysis, plans, participant assignments, and generated code.

Work flows left-to-right and top-to-bottom: variables → designs → composition → run.

---

## Step 1 — Variables

Variables are the independent variables in your experiment. Each has a **name** and a list of **conditions** (levels).

The interface starts with one blank variable. Type a name, then type each condition and press **Enter** or **Tab** to add it. Click **+ variable** to add more.

### Multifactor variables

Click **+ multifact** to create a variable that jointly represents the combinations of two or more existing variables. Select the component variables from the dropdown. Multifactor variables are useful when you want to counterbalance the *joint ordering* of multiple factors as a single unit rather than independently.

> **Example:** A multifactor of `interface` (2 levels) × `task` (3 levels) creates 6 combined conditions: `baseline-creation`, `baseline-editing`, etc.

---

## Step 2 — Designs

A design specifies *how* variables are assigned to participants. Click **+ design**, then **+ add variable** inside the design card to assign variables to it.

### Within vs. between subjects

Each variable in a design is toggled as:

- **W (Within)** — every participant sees every condition
- **B (Between)** — each participant sees only one condition

### Annotations

For within-subjects variables, select how conditions are ordered:

| Annotation | Meaning |
|---|---|
| **Randomized** | Conditions randomly ordered per participant (no counterbalancing) |
| **Counterbalance** | Conditions systematically counterbalanced using Latin square-style plans |
| **Fixed order** | All participants see conditions in a fixed sequence you specify by dragging |

### limit_plans

`limit_plans` caps the number of counterbalancing plans generated. By default, PLanet generates the full set required for complete counterbalancing. Restricting this — for example, to the number of conditions of one variable — approximates a Latin square.

Each variable in the design has a **pill button** showing its condition count. Click it to set `limit_plans` to that value automatically.

### num_trials

`num_trials` sets the number of trials per participant. Defaults to the number of conditions.

---

## Step 3 — Composition

Compositions combine two designs into a single experiment structure. Click **+ composition** and select a type:

| Type | Meaning |
|---|---|
| **Nest** | The inner design repeats within each block of the outer design. The outer variable is a between-block factor. |
| **Cross** | Both designs are run fully for every participant — all combinations of the two designs are realized. |

The **outer** and **inner** dropdowns accept any defined design or prior composition, so arbitrarily complex structures can be built up as a tree.

> **Tip:** The last composition in the list is used as the root of the experiment unless you click a specific design or composition card to select it as the target.

---

## Running a Design

Set the **Participants** count at the bottom of the left panel, then click **Run ▶**.

PLanet generates all counterbalancing plans and assigns participants to them. For large designs (many conditions or a large plan space), this can take time. The button turns red and shows **Cancel** while running — click it again to abort immediately. The backend process is killed on cancel, so no computation continues in the background.

If the design requires more plans than participants (e.g., 8 plans but only 6 participants), an error is shown with the minimum participant count needed.

---

## Results

After a successful run, the right panel shows three tabs:

**Plans** — Each counterbalancing plan is a row; trials are columns. Conditions are color-coded consistently throughout the interface.

**Assignment** — Shows each participant's ID and which plan they are assigned to.

**Code** — The generated PLanet Python code for the current design. Copy it into a script for programmatic use or to reproduce the design exactly.

---

## Analysis

Click **Analyze** to inspect the statistical properties of your design without generating plans. Analysis is fast even for large designs.

The analysis card shows four categories:

| Category | Meaning |
|---|---|
| **Main Effects** | Variables whose main effect is estimable |
| **Interaction Effects** | Variable combinations whose interaction is estimable |
| **Time-Varying Effects** | Effects whose carryover component is separately estimable |
| **Within-Subjects Comparisons** | Variables for which every participant sees every condition |

### Assumption warnings

A **⚠** icon appears on a main or interaction effect when estimating it requires an assumption. Hover over the icon to read the assumption.

This occurs when a confounding effect (time-varying or interaction) exists but cannot be estimated separately — for example, when too few counterbalancing plans are used to disentangle carryover from the main effect. A design that *can* estimate the time-varying effect does not require this assumption and will not show the warning.

---

## Comparing Designs

When two or more designs are defined, a **Compare** button appears. Select two designs from the dropdowns and click **Compare**.

The comparison view shows a table of all estimable effects grouped into three sections — **Main Effects**, **Interaction Effects**, and **Time-Varying Effects** — with a column for each design. Each row shows whether the effect is estimable (✓) or not (—) in each design.

- **Blue rows** — effects estimable only in Design 1
- **Orange rows** — effects estimable only in Design 2
- **⚠ on a ✓** — the effect is estimable in this design, but only under an assumption that the other design does not require (e.g., the other design can estimate the time-varying effect of that variable, but this one cannot)

Below the table, a **Power Advantage** summary indicates which design has stronger statistical power for each effect, ranked as: within-subjects comparison > estimable > not estimable.

---

## Exporting

After running a design, two export buttons appear:

- **CSV** — Downloads a merged table of participant assignments and trial sequences. Each row is a participant; columns include their plan, trial order, and condition per variable.
- **LaTeX** — Downloads a formatted LaTeX table of the counterbalancing plans, suitable for inclusion in a paper.

---

## Advanced: Repeat Blocks

To have participants complete **multiple repetitions** of a design, use an empty design nested around your main design:

1. Create a new design with **no variables** assigned
2. Set its `num_trials` to the desired number of repetitions
3. Create a **Nest** composition with the empty design as **outer** and your real design as **inner**

Because the outer design has no variables, it contributes no conditions of its own — it acts purely as a repetition counter, causing the inner design to repeat for each of its trials.

> **Example:** An empty design with `num_trials = 3` nested around a counterbalanced `interface` design produces 3 full repetitions of the interface conditions per participant, with counterbalancing applied within each repetition.

This is the compositional idiom for repetition in PLanet. There is no separate "repeat" primitive — repetition emerges naturally from nesting an empty design.

---

## Local GUI (no browser)

PLanet Composer also runs as a standalone desktop application using [pywebview](https://pywebview.flowrl.com/), with no browser or server required:

```bash
python gui.py
```

The local GUI is functionally identical to the web app.

### Launching from a Python script

Pre-populate the GUI with results computed in a Python script using `show_results()` from `gui.py`:

```python
from gui import show_results
from planet import *

interface = ExperimentVariable("interface", options=["baseline", "VR"])
design = Design().within_subjects(interface).counterbalance(interface)
assignment = assign(Units(8), design)

plans = assignment.computed_plans
plan_data = [{"plan_id": i+1, "trials": [str(c) for c in plan]}
             for i, plan in enumerate(plans)]

show_results({
    "plans": plan_data,
    "variables": [v.name for v in design.variables],
    "assignment": assignment.format_assignment().to_dict(orient="records"),
    "code": "# your generated code here",
})
```

This opens a window with the results pre-loaded, bypassing the interactive design step entirely.

---

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
  images/
    overview.png # Single annotated screenshot of the full interface
```
