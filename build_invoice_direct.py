import json
from pathlib import Path
from pipeline import pdf_renderer, bundle_builder, config as cfg

with open('src/data/workflows.json', 'r') as f:
    workflows = json.load(f)

w = next(item for item in workflows if item.get('slug') == 'invoice-automation')

out = cfg.DOWNLOADS_DIR / f"flowmatrix-{w['slug']}.pdf"
out.parent.mkdir(parents=True, exist_ok=True)
pdf_renderer.render_workflow_pdf(w, out)
print('PDF written:', out)

kit_path = bundle_builder.build_workflow_kit(w, out, cfg.KITS_DIR)
print('Kit built:', kit_path)
