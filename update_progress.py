import json

with open('pipeline/workflow_migration_progress.json', 'r') as f:
    prog = json.load(f)

prog['invoice-automation'] = {
    "status": "done",
    "updated_at": "2026-11-04 18:35 UTC"
}

with open('pipeline/workflow_migration_progress.json', 'w') as f:
    json.dump(prog, f, indent=2)

print('Updated workflow_migration_progress.json')

# Calculate progress stats
total = len(prog)
done = sum(1 for v in prog.values() if (v.get('status') if isinstance(v, dict) else v) == 'done')
pending = total - done
print(f'Progress: {done} of {total} workflows done ({pending} still pending)')

next_pending = next((k for k, v in prog.items() if (v.get('status') if isinstance(v, dict) else v) == 'pending'), None)
print(f'Next pending: {next_pending}')
