import json
import os
from pipeline.validator import validate_workflow

def check_workflows_fast():
    data_path = "src/data/workflows.json"
    with open(data_path, "r") as f:
        workflows = json.load(f)

    print(f"Total workflows: {len(workflows)}")
    invalid = 0
    report = []

    for idx, wf in enumerate(workflows):
        slug = wf.get("slug")
        print(f"[{idx+1}/{len(workflows)}] Checking {slug}...", flush=True)
        res = validate_workflow(wf)
        if not res.ok:
            invalid += 1
            print(f"  -> FAILED: {res.errors}")
            report.append({"slug": slug, "errors": res.errors, "warnings": res.warnings})
        else:
            if res.warnings:
                print(f"  -> OK with warnings: {res.warnings}")
            else:
                print("  -> OK")

    with open("workflow_validation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"Done! Invalid workflows: {invalid}. Report saved.")

if __name__ == "__main__":
    check_workflows_fast()
