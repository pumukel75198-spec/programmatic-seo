import json
from pipeline.validator import validate_workflow

def test_single_workflow_pipeline_check(slug="invoice-automation"):
    path = "src/data/workflows.json"
    with open(path, "r") as f:
        workflows = json.load(f)
    
    wf = next((w for w in workflows if w.get("slug") == slug), None)
    if not wf:
        print(f"Workflow {slug} not found.")
        return
        
    print(f"Validating {slug} with validator.py rules...")
    res = validate_workflow(wf)
    print(f"OK: {res.ok}")
    if res.errors:
        print("Errors:")
        for err in res.errors:
            print(f"  - {err}")
    if res.warnings:
        print("Warnings:")
        for warn in res.warnings:
            print(f"  - {warn}")

if __name__ == "__main__":
    test_single_workflow_pipeline_check()
