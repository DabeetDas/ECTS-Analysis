import json
from pathlib import Path
r0 = json.loads(Path('corpus_gpu_split_sf5vcx7g/gpu0_result.json').read_text())
r1 = json.loads(Path('corpus_gpu_split_sf5vcx7g/gpu1_result.json').read_text())
merged = {
    'parameters': r0.get('parameters', {}),
    'documents': r0.get('documents', []) + r1.get('documents', []),
    'observations': r0.get('observations', []) + r1.get('observations', []),
    'ontology': {**r0.get('ontology', {}), 'nodes': list({n['topic_id']: n for n in r0.get('ontology', {}).get('nodes', []) + r1.get('ontology', {}).get('nodes', [])}.values())},
}
Path('outputs/psb_corpus_analysis.json').write_text(json.dumps(merged, indent=2))
print(f'Merged {len(merged["observations"])} observations')