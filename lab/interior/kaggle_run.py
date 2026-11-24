"""Build and push a self-contained Kaggle script kernel; poll it; download outputs.
The Kaggle credential is injected by the environment proxy. No key is read or stored here.
Usage:
  python kaggle_run.py push  SLUG ENTRY.py [FILE ...] [--env K=V ...]
  python kaggle_run.py status SLUG
  python kaggle_run.py fetch SLUG DEST_DIR
"""
import base64, gzip, json, os, sys, time, urllib.request

API = "https://api.kaggle.com/v1/kernels.KernelsApiService/"
USER = os.environ.get("KAGGLE_USER", "arielsivkov")

def call(method, body):
    req = urllib.request.Request(API + method, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read() or b"{}")

def build(entry, files, env):
    parts = ["import base64, gzip, os, subprocess, sys",
             "subprocess.run('pip uninstall -y torchao; pip install -q peft', shell=True)",
             "os.makedirs('/kaggle/working', exist_ok=True)"]
    for f in [entry] + files:
        blob = base64.b64encode(gzip.compress(open(f, "rb").read())).decode()
        parts.append(f"open('/kaggle/working/{os.path.basename(f)}','wb').write(gzip.decompress(base64.b64decode('{blob}')))")
    envs = " ".join(env)
    parts.append(f"r = subprocess.run('cd /kaggle/working && {envs} python {os.path.basename(entry)} 2>&1 | grep -v -i warning | tee run_log.txt', shell=True)")
    parts.append("sys.exit(r.returncode)")
    return "\n".join(parts) + "\n"

if __name__ == "__main__":
    cmd, slug = sys.argv[1], sys.argv[2]
    if cmd == "push":
        args = sys.argv[3:]
        env = [a.split("=", 1)[0] + "=" + a.split("=", 1)[1] for a in args[args.index("--env") + 1:]] if "--env" in args else []
        files = args[: args.index("--env")] if "--env" in args else args
        text = build(files[0], files[1:], env)
        body = {"slug": f"{USER}/{slug}", "newTitle": slug, "text": text, "language": "python",
                "kernelType": "script", "isPrivate": True, "enableGpu": True, "enableInternet": True,
                "machineShape": "NvidiaTeslaT4"}
        print(json.dumps(call("SaveKernel", body))[:800])
    elif cmd == "status":
        print(json.dumps(call("GetKernelSessionStatus", {"userName": USER, "kernelSlug": slug})))
    elif cmd == "fetch":
        dest = sys.argv[3]; os.makedirs(dest, exist_ok=True)
        out = call("ListKernelSessionOutput", {"userName": USER, "kernelSlug": slug, "pageSize": 200})
        for f in out.get("files", []):
            name = f.get("fileName") or f.get("name")
            path = os.path.join(dest, name); os.makedirs(os.path.dirname(path), exist_ok=True)
            urllib.request.urlretrieve(f["url"], path); print("got", name, os.path.getsize(path))
        if out.get("log"):
            open(os.path.join(dest, "kernel_log.json"), "w").write(out["log"] if isinstance(out["log"], str) else json.dumps(out["log"]))
        print("files:", len(out.get("files", [])), "nextPageToken:", out.get("nextPageToken"))
