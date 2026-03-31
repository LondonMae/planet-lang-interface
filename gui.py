#!/usr/bin/env python3
"""
PLanet Experimental Design Composer — local GUI (no server required).
Uses pywebview to render the UI and calls Python directly from JS.
"""
import sys
import os
import io
import subprocess
import traceback
from pathlib import Path

os.chdir(Path(__file__).parent)

# Reuse code-generation and helper from app.py
from app import generate_code, py_id


class Api:
    """Python methods exposed to JS as window.pywebview.api.*"""

    def get_results(self):
        """Return precomputed results for script mode; None in interactive mode."""
        return None

    def run_design(self, spec):
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
                suggested = math.ceil(units_n / num_plans) * num_plans
                return {
                    "success": False,
                    "error": (
                        f"This design requires {num_plans} counterbalancing plans, "
                        f"but only {units_n} participants were specified. "
                        f"Please use at least {suggested} participants "
                        f"(a multiple of {num_plans})."
                    ),
                }

            plan_data = [
                {"plan_id": i + 1, "trials": [str(c) for c in plan]}
                for i, plan in enumerate(plans)
            ]
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

    def analyze(self, spec):
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
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

    def compare(self, spec):
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

    def export_csv(self, spec):
        try:
            import pandas as pd
            code = generate_code(spec)
            ns = {}
            exec(code, ns)
            assignment = ns["_assignment"]

            plans = assignment.computed_plans
            trials_cols = [f"trial{i+1}" for i in range(len(plans[0]))]
            plans_df = (
                pd.DataFrame(plans, columns=trials_cols)
                .reset_index()
                .rename(columns={"index": "row_number"})
            )
            units_df = assignment.format_assignment()
            units_df = units_df[units_df["pid"] != -1]
            merged = (
                units_df.merge(plans_df, how="inner", left_on="plan", right_on="row_number")
                .drop("row_number", axis=1)
            )
            content = merged.to_csv(index=False)

            downloads = Path.home() / "Downloads"
            path = downloads / "planet_assignment.csv"
            path.write_text(content)
            subprocess.run(["open", "-R", str(path)])
            return {"success": True, "path": str(path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def export_latex(self, spec):
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

            tex_path = Path("outputs") / "design.tex"
            content = tex_path.read_text() if tex_path.exists() else buf.getvalue()

            downloads = Path.home() / "Downloads"
            path = downloads / "planet_design.tex"
            path.write_text(content)
            subprocess.run(["open", "-R", str(path)])
            return {"success": True, "path": str(path)}
        except Exception as e:
            return {"success": False, "error": str(e)}


class ScriptApi(Api):
    """Api variant used when launching from a user script (e.g. mydesign.py)."""

    def __init__(self, payload):
        self._payload = payload

    def get_results(self):
        return self._payload


def show_results(payload):
    """Open a GUI window showing a precomputed result from a script.

    Writes a temporary HTML file with the payload embedded so it's available
    synchronously at page load — no pywebview API or evaluate_js timing issues.
    """
    import webview
    import json
    import tempfile
    import os

    html_path = Path(__file__).parent / "gui.html"
    html = html_path.read_text()

    # Inject payload as a global before any other scripts run
    payload_json = json.dumps(payload)
    injection = f"<script>window._scriptPayload = {payload_json};</script>"
    html = html.replace("<head>", f"<head>\n{injection}", 1)

    # Write alongside gui.html so relative paths and base URL are correct
    tmp_path = html_path.parent / "_planet_results_tmp.html"
    tmp_path.write_text(html)

    try:
        webview.create_window(
            "PLanet — Results",
            url=tmp_path.as_uri(),
            width=1100,
            height=750,
            min_size=(800, 500),
        )
        webview.start(debug=False)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def main():
    import webview

    api = Api()
    html_path = Path(__file__).parent / "gui.html"

    webview.create_window(
        "PLanet — Experimental Design Composer",
        url=html_path.as_uri(),
        js_api=api,
        width=1440,
        height=900,
        min_size=(900, 620),
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
