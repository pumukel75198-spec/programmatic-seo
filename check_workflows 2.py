import json
import os
import sys
from pipeline.validator import validate_workflow

def check_all_workflows():
    data_path = "src/data/workflows.json"
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found")
        return

    with open(data_path, "r") as f:
        workflows = json.load(f)

    total = len(workflows)
    invalid_count = 0
    results = []

    print(f"Checking {total} workflows...")

    for wf in workflows:
        res = validate_workflow(wf)
        if not res.ok:
            invalid_count += 1
            results.append({
                "slug": wf.get("slug"),
                "errors": res.errors,
                "warnings": res.warnings
            })
            print(f"FAILED: {wf.get('slug')}")
            for err in res.errors:
                print(f"  - Error: {err}")
        else:
            if res.warnings:
                 print(f"OK (with warnings): {wf.get('slug')}")
                 for warn in res.warnings:
                     print(f"  - Warning: {warn}")
            # else:
            #    print(f"OK: {wf.get('slug')}")

    print("\nSummary:")
    print(f"Total: {total}")
    print(f"Invalid: {invalid_count}")
    
    if results:
        with open("workflow_validation_report.json", "w") as f:
            json.dump(results, f, indent=2)
        print("Report saved to workflow_validation_report.json")

if __name__ == "__main__":
    check_all_workflows()
