#!/usr/bin/env python3
import sys
import os
import re
import io
import traceback
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

os.chdir(Path(__file__).parent)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SAFE_STR = re.compile(r'^[a-zA-Z0-9_ \-]+$')

def safe(s: str) -> str:
    s = str(s).strip()
    if not SAFE_STR.match(s):
        raise ValueError(f"Unsafe string: {s!r}")
    return s

def py_id(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '_', s.strip())

def generate_code(spec: dict) -> str:
    lines = [
        "from planet import *",
        "",
    ]

    var_map = {}  # id -> python name
    # Pass 1: regular ExperimentVariables
    for v in spec["variables"]:
        if v.get("type") == "multivar":
            continue
        vid = v["id"]
        name = safe(v["name"])
        options = [safe(o) for o in v["options"]]
        pname = f"var_{py_id(vid)}"
        var_map[vid] = pname
        opts = ", ".join(f'"{o}"' for o in options)
        lines.append(f'{pname} = ExperimentVariable("{name}", options=[{opts}])')
    lines.append("")
    # Pass 2: multifact variables (composed from regular vars)
    has_multivar = False
    for v in spec["variables"]:
        if v.get("type") != "multivar":
            continue
        vid = v["id"]
        pname = f"mv_{py_id(vid)}"
        var_map[vid] = pname
        component_names = [var_map[cid] for cid in v.get("var_ids", [])]
        lines.append(f'{pname} = multifact([{", ".join(component_names)}])')
        has_multivar = True
    if has_multivar:
        lines.append("")

    # Pre-validate: detect compositions of two purely between-subjects designs,
    # which PLanet cannot handle (would call .num_trials(1) internally).
    def is_bs_only(node_id, designs, compositions):
        for d in designs:
            if d["id"] == node_id:
                dvars = d.get("variables", [])
                return bool(dvars) and all(dv.get("subject_type", "within") == "between" for dv in dvars)
        for c in compositions:
            if c["id"] == node_id:
                a = c.get("outer") or c.get("a")
                b = c.get("inner") or c.get("b")
                return is_bs_only(a, designs, compositions) and is_bs_only(b, designs, compositions)
        return False

    for c in spec.get("compositions", []):
        op = c.get("type")
        a_id = c.get("outer") or c.get("a")
        b_id = c.get("inner") or c.get("b")
        if a_id and b_id and is_bs_only(a_id, spec.get("designs", []), spec.get("compositions", [])) \
                         and is_bs_only(b_id, spec.get("designs", []), spec.get("compositions", [])):
            raise ValueError(
                "Two between-subjects-only designs cannot be composed with nest or cross. "
                "Place all between-subjects variables into a single design instead."
            )

    design_map = {}  # id -> python name
    for d in spec["designs"]:
        did = d["id"]
        label = d.get("label", did)
        pname = f"des_{py_id(did)}"
        design_map[did] = pname

        chain = ["Design()"]

        for dv in d.get("variables", []):
            vp = var_map[dv["variable_id"]]
            annotation = dv.get("annotation", "randomized")

            subject_type = dv.get("subject_type", "within")
            if subject_type == "between":
                chain.append(f"    .between_subjects({vp})")
                if annotation == "counterbalance":
                    chain.append(f"    .counterbalance({vp})")
            else:
                chain.append(f"    .within_subjects({vp})")
                if annotation == "counterbalance":
                    chain.append(f"    .counterbalance({vp})")
                elif annotation == "order":
                    seq = dv.get("order_sequence") or []
                    if seq:
                        opts = ", ".join(f'"{safe(s)}"' for s in seq)
                        chain.append(f"    .order({vp}, [{opts}])")

        if d.get("limit_plans"):
            chain.append(f"    .limit_plans({int(d['limit_plans'])})")
        if d.get("num_trials") and int(d["num_trials"]) > 1:
            chain.append(f"    .num_trials({int(d['num_trials'])})")

        lines.append(f"{pname} = (")
        lines.append(f"    " + "\n    ".join(chain))
        lines.append(f")")
        lines.append("")

    # Composition nodes
    comp_map = {}  # id -> python name

    def build_expr(node_id: str) -> str:
        if node_id in design_map:
            return design_map[node_id]
        if node_id in comp_map:
            return comp_map[node_id]
        raise ValueError(f"Unknown node: {node_id}")

    for c in spec.get("compositions", []):
        cid = c["id"]
        pname = f"comp_{py_id(cid)}"
        comp_map[cid] = pname
        op = c["type"]
        if op == "nest":
            outer = build_expr(c["outer"])
            inner = build_expr(c["inner"])
            lines.append(f"{pname} = nest(outer={outer}, inner={inner})")
        elif op == "cross":
            a = build_expr(c["a"])
            b = build_expr(c["b"])
            lines.append(f"{pname} = cross({a}, {b})")
        lines.append("")

    root_id = spec.get("root")
    if root_id:
        root_expr = build_expr(root_id)
    elif spec.get("compositions"):
        last = spec["compositions"][-1]
        root_expr = comp_map[last["id"]]
    elif spec.get("designs"):
        root_expr = design_map[spec["designs"][-1]["id"]]
    else:
        raise ValueError("No designs defined")

    lines.append(f"_final = {root_expr}")
    units_n = max(1, int(spec.get("units", 12)))
    lines.append(f"_units = Units({units_n})")
    lines.append(f"_assignment = assign(_units, _final)")

    return "\n".join(lines)



@app.post("/api/run")
async def run_design(spec: dict):
    try:
        code = generate_code(spec)
        ns = {}
        exec(code, ns)
        assignment = ns["_assignment"]
        final = ns["_final"]

        plans = assignment.computed_plans
        num_plans = len(plans)
        units_n = max(1, int(spec.get("units", 12)))
        if num_plans > units_n:
            import math
            lcm = num_plans  # minimum valid count is num_plans itself
            suggested = math.ceil(units_n / lcm) * lcm
            return {
                "success": False,
                "error": (
                    f"This design requires {num_plans} counterbalancing plans, "
                    f"but only {units_n} participants were specified. "
                    f"Please use at least {suggested} participants (a multiple of {num_plans})."
                ),
            }
        plan_data = [{"plan_id": i + 1, "trials": [str(c) for c in plan]} for i, plan in enumerate(plans)]
        variables = [v.name for v in final.variables]
        assign_df = assignment.format_assignment()
        assign_data = assign_df[assign_df["pid"] != -1].to_dict(orient="records")

        return {
            "success": True,
            "plans": plan_data,
            "variables": variables,
            "assignment": assign_data,
            "code": code,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


@app.post("/api/analyze")
async def analyze_designs(spec: dict):
    try:
        from planet.analysis import Analysis

        code = generate_code(spec)
        ns = {}
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            exec(code, ns)
        finally:
            sys.stdout = old_stdout

        target = spec.get("analyze_target", "root")
        if target == "root":
            design_obj = ns.get("_final")
        elif any(d["id"] == target for d in spec.get("designs", [])):
            design_obj = ns.get(f"des_{py_id(target)}")
        elif any(c["id"] == target for c in spec.get("compositions", [])):
            design_obj = ns.get(f"comp_{py_id(target)}")
        else:
            design_obj = ns.get("_final")

        if design_obj is None:
            return {"success": False, "error": "Target design not found"}

        sys.stdout = io.StringIO()
        try:
            analysis = Analysis(design_obj)
        finally:
            sys.stdout = old_stdout

        return {
            "success": True,
            "analysis": {
                "main_effects": [str(v) for v in analysis.main_effects],
                "interaction_effects": [str(v) for v in analysis.interaction_effects],
                "time_varying_effects": [str(v) for v in analysis.time_varying_effects],
                "ws_comparisons": [str(v) for v in analysis.ws_comparisons],
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


@app.post("/api/compare")
async def compare_designs_endpoint(spec: dict):
    try:
        from planet.analysis import Analysis

        code = generate_code(spec)
        ns = {}
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            exec(code, ns)
        finally:
            sys.stdout = old_stdout

        def resolve(target_id):
            if target_id == "root":
                return ns.get("_final")
            if any(d["id"] == target_id for d in spec.get("designs", [])):
                return ns.get(f"des_{py_id(target_id)}")
            if any(c["id"] == target_id for c in spec.get("compositions", [])):
                return ns.get(f"comp_{py_id(target_id)}")
            return ns.get("_final")

        d1 = resolve(spec.get("compare_target_1"))
        d2 = resolve(spec.get("compare_target_2"))
        if d1 is None or d2 is None:
            return {"success": False, "error": "One or both target designs not found"}

        sys.stdout = io.StringIO()
        try:
            a1 = Analysis(d1)
            a2 = Analysis(d2)
        finally:
            sys.stdout = old_stdout

        def analysis_dict(a):
            return {
                "main_effects": [str(v) for v in sorted(a.main_effects, key=str)],
                "interaction_effects": [str(v) for v in sorted(a.interaction_effects, key=str)],
                "time_varying_effects": [str(v) for v in sorted(a.time_varying_effects, key=str)],
                "ws_comparisons": [str(v) for v in sorted(a.ws_comparisons, key=str)],
            }

        return {
            "success": True,
            "analysis_d1": analysis_dict(a1),
            "analysis_d2": analysis_dict(a2),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


@app.post("/api/export/csv")
async def export_csv(spec: dict):
    try:
        code = generate_code(spec)
        ns = {}
        exec(code, ns)
        assignment = ns["_assignment"]

        plans = assignment.computed_plans
        import pandas as pd
        trials_cols = [f"trial{i+1}" for i in range(len(plans[0]))]
        plans_df = pd.DataFrame(plans, columns=trials_cols).reset_index().rename(columns={"index": "row_number"})
        units_df = assignment.format_assignment()
        units_df = units_df[units_df["pid"] != -1]
        merged = units_df.merge(plans_df, how="inner", left_on="plan", right_on="row_number").drop("row_number", axis=1)

        return PlainTextResponse(merged.to_csv(index=False), media_type="text/csv")
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.post("/api/export/latex")
async def export_latex(spec: dict):
    try:
        code = generate_code(spec)
        ns = {}
        exec(code, ns)
        assignment = ns["_assignment"]

        from planet.formatter import LatexExport
        formatter = LatexExport(assignment.computed_plans)
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        formatter.to_latex()
        sys.stdout = old_stdout

        # Read from outputs/design.tex if written there
        tex_path = Path("outputs") / "design.tex"
        if tex_path.exists():
            content = tex_path.read_text()
        else:
            content = buf.getvalue()

        return PlainTextResponse(content, media_type="text/plain")
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.get("/", response_class=HTMLResponse)
async def index():
    return (Path(__file__).parent / "index.html").read_text()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
