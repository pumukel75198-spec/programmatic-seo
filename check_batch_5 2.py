import json
from pipeline.validator import validate_workflow

def check_first_n(n=5):
    with open("src/data/workflows.json", "r") as f:
        workflows = json.load(f)
    
    print(f"Checking first {n} workflows...")
    for i, wf in enumerate(workflows[:n]):
        slug = wf.get("slug")
        res = validate_workflow(wf)
        print(f"\n--- [{i+1}/{n}] Workflow: {slug} ---")
        if res.ok:
            print("Status: OK")
        else:
            print("Status: FAILED")
            for err in res.errors:
                print(f"  - Error: {err}")
        if res.warnings:
            for warn in res.warnings:
                print(f"  - Warning: {warn}")

if __name__ == "__main__":
    check_first_n(5)
