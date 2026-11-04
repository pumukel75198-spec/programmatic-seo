import json

def filter_valid_workflows():
    path = "src/data/workflows.json"
    with open(path, "r") as f:
        workflows = json.load(f)
    
    valid = []
    for wf in workflows:
        steps = wf.get("details", {}).get("steps", [])
        # Check if steps have code snippets and descriptions
        if len(steps) >= 3 and all(s.get("code_snippet") and s.get("description") for s in steps):
            valid.append(wf)
            
    print(f"Original workflows: {len(workflows)}")
    print(f"Valid workflows keeping: {len(valid)}")
    
    with open(path, "w") as f:
        json.dump(valid, f, indent=2)
    print("Cleaned workflows.json to only retain fully valid/complete workflows.")

if __name__ == "__main__":
    filter_valid_workflows()
