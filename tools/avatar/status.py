"""Read-only deployment inventory; size checks are not SHA256 verification."""
from pathlib import Path
import json
root=Path(__file__).resolve().parent
rows=json.loads((root/'model-manifest.json').read_text('utf-8'))
total=sum(x['size'] for x in rows)
present=[x for x in rows if (p:=root/'Wan2GP'/(x['target'] if x.get('target') else 'ckpts/'+x['file'])).is_file() and p.stat().st_size==x['size']]
partial=sum(p.stat().st_size for p in (root/'cache'/'parts').rglob('*') if p.is_file())
done=sum(x['size'] for x in present)
print(json.dumps({'expected_files':len(rows),'size_complete_files':len(present),'expected_GiB':round(total/2**30,2),'size_complete_GiB':round(done/2**30,2),'partial_GiB':round(partial/2**30,2),'note':'See download log for SHA256 VERIFIED lines; partial data may be retried.'},ensure_ascii=False,indent=2))
