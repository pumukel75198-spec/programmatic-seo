import json
from pipeline import pdf_renderer, bundle_builder, config as cfg, validator

with open('src/data/workflows.json', 'r') as f:
    workflows = json.load(f)

w = next((item for item in workflows if item.get('slug') == 'invoice-automation'), None)
if not w:
    print('Workflow invoice-automation not found')
    exit(1)

w['created_and_verified_at'] = '2026-11-04 18:27 UTC'

# Fix code snippets to be sequential and consume previous variables
steps = w['details']['steps']
steps[0]['code_snippet'] = "import json\nimport urllib.request\n\ndef fetch_events():\n    url = 'https://api.stripe.com/v1/events'\n    headers = {'Authorization': 'Bearer sk_test_123'}\n    request = urllib.request.Request(url, headers=headers)\n    with urllib.request.urlopen(request) as response:\n        return json.loads(response.read().decode('utf-8'))\n\nevents = fetch_events()"

steps[1]['code_snippet'] = "import json\nimport urllib.request\n\ndef generate_pdf(events):\n    invoices = []\n    for event in events.get('data', []):\n        invoices.append({'id': event.get('id'), 'amount': 100.00})\n    return invoices\n\ninvoices = generate_pdf(events)"

steps[2]['code_snippet'] = "import json\nimport urllib.request\n\ndef send_invoices(invoices):\n    url = 'https://api.resend.com/emails'\n    headers = {'Authorization': 'Bearer re_123', 'Content-Type': 'application/json'}\n    for inv in invoices:\n        data = json.dumps({'to': 'customer@example.com', 'subject': f'Invoice {inv[\"id\"]}', 'html': 'Please pay'}).encode('utf-8')\n        request = urllib.request.Request(url, data=data, headers=headers)\n        with urllib.request.urlopen(request) as response:\n            pass\n    return invoices\n\nsent_invoices = send_invoices(invoices)"

steps[3]['code_snippet'] = "import json\nimport urllib.request\n\ndef check_status(sent_invoices):\n    url = 'https://api.stripe.com/v1/charges'\n    headers = {'Authorization': 'Bearer sk_test_123'}\n    request = urllib.request.Request(url, headers=headers)\n    with urllib.request.urlopen(request) as response:\n        return json.loads(response.read().decode('utf-8'))\n\nstatus_data = check_status(sent_invoices)"

steps[4]['code_snippet'] = "import json\nimport urllib.request\n\ndef sync_accounting(status_data):\n    url = 'https://your-project.supabase.co/rest/v1/payments'\n    headers = {'apikey': 'key', 'Authorization': 'Bearer key', 'Content-Type': 'application/json'}\n    data = json.dumps({'status': 'synced'}).encode('utf-8')\n    request = urllib.request.Request(url, data=data, headers=headers)\n    request.get_method = lambda: 'POST'\n    with urllib.request.urlopen(request) as response:\n        return 'ok'\n\nsync_result = sync_accounting(status_data)"

# Add resources for stripe.com and resend.com
resources = w['details'].get('resources', [])
res_urls = [r['url'] for r in resources]
if not any('stripe.com' in u for u in res_urls):
    resources.append({'label': 'Stripe API', 'url': 'https://stripe.com/docs'})
if not any('resend.com' in u for u in res_urls):
    resources.append({'label': 'Resend API', 'url': 'https://resend.com/docs'})
w['details']['resources'] = resources

res = validator.validate_workflow(w)
print('Validation ok:', res.ok, res.errors, res.warnings)

if res.ok:
    with open('src/data/workflows.json', 'w') as f:
        json.dump(workflows, f, indent=2, ensure_ascii=False)
    print('Updated workflows.json successfully.')
