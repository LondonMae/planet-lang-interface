"""planet_ui — PLanet scripting with local GUI output.

Usage in your .py script:

    from planet_ui import *

    interface = ExperimentVariable("interface", options=["A", "B"])
    task      = ExperimentVariable("task",      options=["search", "browse"])

    design = (
        Design()
        .within_subjects(interface)
        .counterbalance(interface)
        .within_subjects(task)
    )

    # Show a design (analysis + plans + assignment):
    show(design)
    show(design, units=24, label="Within-Subjects")

    # Show an assignment result:
    a = assign(Units(12), design)
    show(a)

    # Show a side-by-side comparison:
    compare(design_a, design_b)          # uses 12 units by default
    compare(design_a, design_b, units=24, label1="WS", label2="BS")

Run:  python3 mydesign.py
"""

from planet import *
from planet import assign as _planet_assign
import atexit, io, sys

_last_op = None


# ── Overrides ─────────────────────────────────────────────────────────────────

def assign(units_obj, design):
    """planet.assign(), but records itself as the last operation."""
    global _last_op
    result = _planet_assign(units_obj, design)
    _last_op = {"type": "assignment", "result": result, "design": design}
    return result


def show(obj, units=12, label=None):
    """Show a Design or Assignment result in the GUI.

    show(design)                        # analysis + plans + assignment
    show(design, units=24, label="WS")  # same with custom participant count/label
    show(assignment_result)             # plans + assignment from an existing assign() call

    In a Jupyter notebook the GUI opens immediately and blocks the cell
    until the window is closed.  In a .py script it opens on exit.
    """
    global _last_op
    from planet.design import Design
    from planet.assignment import Assignment

    if isinstance(obj, Design):
        _last_op = {
            "type": "show",
            "design": obj,
            "units": units,
            "label": label or "Design",
        }
    elif isinstance(obj, Assignment):
        _last_op = {
            "type": "show_assignment",
            "result": obj,
            "label": label or "Assignment",
        }
    else:
        raise TypeError(f"show() expects a Design or Assignment, got {type(obj).__name__}")

    if _in_notebook():
        _show()


def compare(d1, d2, label1="Design 1", label2="Design 2", units=12):
    """Show a side-by-side comparison of two designs.

    In a Jupyter notebook the GUI opens immediately and blocks the cell
    until the window is closed.  In a .py script it opens on exit.
    """
    global _last_op
    _last_op = {
        "type": "compare",
        "d1": d1, "d2": d2,
        "label1": label1, "label2": label2,
        "units": units,
    }

    if _in_notebook():
        _show()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(design, units):
    result = _planet_assign(Units(units), design)
    plans = result.computed_plans
    plan_data = [
        {"plan_id": i + 1, "trials": [str(c) for c in plan]}
        for i, plan in enumerate(plans)
    ]
    df = result.format_assignment()
    assign_data = df[df["pid"] != -1].to_dict(orient="records")
    return {"success": True, "plans": plan_data, "assignment": assign_data}


def _adict(a):
    return {
        "main_effects":       [str(v) for v in sorted(a.main_effects,       key=str)],
        "interaction_effects":[str(v) for v in sorted(a.interaction_effects, key=str)],
        "time_varying_effects":[str(v) for v in sorted(a.time_varying_effects,key=str)],
        "ws_comparisons":     [str(v) for v in sorted(a.ws_comparisons,     key=str)],
    }


# ── Notebook detection + GUI launch ───────────────────────────────────────────

def _in_notebook():
    try:
        return get_ipython().__class__.__name__ == "ZMQInteractiveShell"
    except NameError:
        return False

def _show():
    global _last_op
    if _last_op is None:
        return

    try:
        op = _last_op

        if op["type"] == "show":
            from planet.analysis import Analysis
            design = op["design"]
            units  = op.get("units", 12)
            label  = op.get("label", "Design")
            buf, old = io.StringIO(), sys.stdout
            sys.stdout = buf
            try:
                analysis = Analysis(design)
            finally:
                sys.stdout = old
            run_result = _run(design, units)
            payload = {
                "type":       "show",
                "label":      label,
                "analysis":   _adict(analysis),
                "plans":      run_result["plans"],
                "assignment": run_result["assignment"],
            }

        elif op["type"] == "show_assignment":
            result = op["result"]
            plans  = result.computed_plans
            plan_data = [
                {"plan_id": i + 1, "trials": [str(c) for c in plan]}
                for i, plan in enumerate(plans)
            ]
            df = result.format_assignment()
            assign_data = df[df["pid"] != -1].to_dict(orient="records")
            payload = {
                "type":       "show",
                "label":      op.get("label", "Assignment"),
                "analysis":   None,
                "plans":      plan_data,
                "assignment": assign_data,
            }

        elif op["type"] == "assignment":
            result = op["result"]
            plans  = result.computed_plans
            plan_data = [
                {"plan_id": i + 1, "trials": [str(c) for c in plan]}
                for i, plan in enumerate(plans)
            ]
            df = result.format_assignment()
            assign_data = df[df["pid"] != -1].to_dict(orient="records")
            payload = {
                "type": "assignment",
                "plans": plan_data,
                "assignment": assign_data,
            }

        elif op["type"] == "compare":
            from planet.analysis import Analysis
            d1, d2 = op["d1"], op["d2"]
            units  = op.get("units", 12)
            buf, old = io.StringIO(), sys.stdout
            sys.stdout = buf
            try:
                a1 = Analysis(d1)
                a2 = Analysis(d2)
            finally:
                sys.stdout = old

            payload = {
                "type":        "compare",
                "label1":      op["label1"],
                "label2":      op["label2"],
                "analysis_d1": _adict(a1),
                "analysis_d2": _adict(a2),
                "run1":        _run(d1, units),
                "run2":        _run(d2, units),
            }

        else:
            return

        from gui import show_results
        show_results(payload)

    except Exception as exc:
        import traceback
        print(f"[planet_ui] GUI launch failed: {exc}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)


atexit.register(_show)
