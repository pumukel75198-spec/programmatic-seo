import json
from pipeline.validator import validate_workflow

def check_all_in_batches(batch_size=5):
    with open("src/data/workflows.json", "r") as f:
        workflows = json.load(f)
    
    total = len(workflows)
    print(f"Total workflows to check: {total} in batches of {batch_size}")
    
    all_failures = []
    
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        print(f"\n==============================")
        print(f"Checking batch: Workflows {start+1} to {end}")
        print(f"==============================")
        
        for i in range(start, end):
            wf = workflows[i]
            slug = wf.get("slug")
            res = validate_workflow(wf)
            if res.ok:
                print(f"  [{i+1}/{total}] {slug} -> OK")
            else:
                print(f"  [{i+1}/{total}] {slug} -> FAILED")
                for err in res.errors:
                    print(f"    - Error: {err}")
                all_failures.append({"index": i+1, "slug": slug, "errors": res.errors})
                
    print(f"\nFinished checking all {total} workflows. Total failures found: {len(all_failures)}")
    if all_failures:
        with open("all_failures_report.json", "w") as f:
            json.dump(all_failures, f, indent=2)
        print("Failure report saved to all_failures_report.json")

if __name__ == "__main__":
    check_all_in_batches(5)
