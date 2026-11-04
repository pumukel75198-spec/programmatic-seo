import json
from pipeline.validator import validate_workflow

def check_range(start=5, count=5):
    with open("src/data/workflows.json", "r") as f:
        workflows = json.load(f)
    
    subset = workflows[start:start+count]
    print(f"Checking workflows {start+1} to {start+len(subset)}...")
    for i, wf in enumerate(subset, start=start+1):
        slug = wf.get("slug")
        res = validate_workflow(wf)
        print(f"\n--- [{i}/{len(workflows)}] Workflow: {slug} ---")
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
    check_range(5, 5)
