"""Query OEIS JSON search; log every query + result to ../out/oeis_queries.jsonl. Read-only (no submission)."""
import sys, json, urllib.request, urllib.parse, time, datetime
LOG = '../out/oeis_queries.jsonl'
def q(query):
    url = 'https://oeis.org/search?' + urllib.parse.urlencode({'q': query, 'fmt': 'json'})
    import subprocess
    data = {'error': 'no attempt'}
    for t in range(3):
        p = subprocess.run(['curl', '-sS', '-m', '40', '-w', '\\n%{http_code}', url], capture_output=True, text=True)
        body, _, code = p.stdout.rpartition('\n')
        if code == '200':
            data = json.loads(body); break
        data = {'error': f'http {code} {p.stderr.strip()[:100]}'}; time.sleep(3)
    hits = []
    if isinstance(data, list):
        hits = [('A%06d' % d['number'], d['name'][:110]) for d in data]
    elif isinstance(data, dict) and 'results' in data:  # older format
        hits = [('A%06d' % d['number'], d['name'][:110]) for d in (data['results'] or [])]
    rec = {'error': data['error']} if isinstance(data, dict) and 'error' in data else {}
    rec |= {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), 'query': query,
           'raw_null': data is None, 'hits': hits}
    with open(LOG, 'a') as f: f.write(json.dumps(rec) + '\n')
    return rec
if __name__ == '__main__':
    for line in sys.stdin:
        line = line.strip()
        if not line or line.startswith('#'): continue
        r = q(line)
        tag = 'null' if r['raw_null'] else (r['error'] if 'error' in r else len(r['hits']))
        print(f"{line!r:60} -> {tag} {r['hits'][:4]}", flush=True)
        time.sleep(1.5)
