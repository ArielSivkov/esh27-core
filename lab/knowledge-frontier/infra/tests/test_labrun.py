"""End-to-end tests for labrun against a local bare repository standing in for GitHub.

Each test clones the bare "remote" into a fresh directory, isolated from the machine's git config,
so pushes, rejections, rebases and hooks run exactly as they would against the real remote.
Run: python3 -I lab/knowledge-frontier/infra/tests/test_labrun.py   (from anywhere inside the repo)
"""
import json
import os
import random
import shutil
import signal
import string
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_REPO = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE, capture_output=True, text=True).stdout.strip()
LAB_REL = "lab/knowledge-frontier"
FAKE = "".join(["gh", "p_"] + [random.Random(3).choice(string.ascii_letters) for _ in range(36)])  # built at runtime


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.gitcfg = os.path.join(cls.tmp.name, "gitconfig")
        with open(cls.gitcfg, "w") as f:
            f.write("[user]\n\tname = lab-test\n\temail = lab-test@localhost\n[init]\n\tdefaultBranch = main\n")
        cls.env = {"PATH": os.environ["PATH"], "HOME": cls.tmp.name, "GIT_CONFIG_GLOBAL": cls.gitcfg,
                   "GIT_CONFIG_SYSTEM": os.devnull, "LANG": "C.UTF-8"}
        cls.remote = os.path.join(cls.tmp.name, "remote.git")
        # the bare remote gets the current working tree (uncommitted infra included) as branch "lab-base"
        stage = os.path.join(cls.tmp.name, "stage")
        cls.sh(["git", "clone", "-q", "--no-hardlinks", SRC_REPO, stage])
        lab_stage = os.path.join(stage, LAB_REL)
        shutil.rmtree(lab_stage)  # inside our own temporary clone
        shutil.copytree(os.path.join(SRC_REPO, LAB_REL), lab_stage,
                        ignore=shutil.ignore_patterns(".venv", "runs", "JOURNAL.md", "__pycache__", "data"))
        cls.sh(["git", "checkout", "-q", "-B", "lab-base"], cwd=stage)
        cls.sh(["git", "add", "-A"], cwd=stage)
        cls.sh(["git", "commit", "-q", "-m", "test base", "--allow-empty"], cwd=stage)
        cls.sh(["git", "clone", "-q", "--bare", stage, cls.remote])
        cls.sh(["git", "update-ref", "-d", "refs/heads/main"], cwd=cls.remote, check=False)
        cls.n = 0

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def sh(cls, cmd, cwd=None, check=True, env=None, **kw):
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env={**cls.env, **(env or {})}, **kw)
        if check and p.returncode != 0:
            raise AssertionError(f"{cmd} failed rc={p.returncode}\n{p.stdout}\n{p.stderr}")
        return p

    def clone(self, branch="lab-base"):
        type(self).n += 1
        d = os.path.join(self.tmp.name, f"work{self.n}")
        self.sh(["git", "clone", "-q", "-b", branch, "file://" + self.remote, d])
        self.sh(["git", "config", "core.hooksPath", f"{LAB_REL}/infra/hooks"], cwd=d)
        return d

    def labrun(self, work, *args, env=None, check=False, **kw):
        return self.sh([sys.executable, "-I", f"{LAB_REL}/infra/labrun.py", *args], cwd=work, check=check, env=env, **kw)

    def remote_log(self, branch):
        # only what the test itself added on top of the base branch
        return self.sh(["git", "log", "--format=%s", f"lab-base..{branch}"], cwd=self.remote).stdout.splitlines()

    def manifest(self, work, rid=None):
        runs = os.path.join(work, LAB_REL, "runs")
        rid = rid or sorted(os.listdir(runs))[-1]
        with open(os.path.join(runs, rid, "manifest.json"), encoding="utf-8") as f:
            return json.load(f)


class TestRun(Base):
    def test_success_is_preregistered_recorded_and_pushed(self):
        w = self.clone()
        p = self.labrun(w, "run", "--name", "ok case", "--hypothesis", "prints hi", "--success", "exit 0",
                        "--success-expr", "rc == 0 and s.get('x') == 1", "--", sys.executable, "-c",
                        "import os,json;print('hi');json.dump({'x':1,'headline':'x is 1'},open(os.environ['LAB_RUN_OUT']+'/summary.json','w'))",
                        env={"LAB_BRANCH": "t-ok"})
        self.assertEqual(p.returncode, 0, p.stderr)
        m = self.manifest(w)
        self.assertEqual((m["status"], m["exit_code"], m["verdict"]), ("ok", 0, "pass"))
        self.assertTrue(m["preregistration"]["committed"] and m["preregistration"]["pushed"])
        log = self.remote_log("t-ok")
        self.assertTrue(log[0].endswith("s)") and "ok" in log[0] and log[1].endswith("registered"), log[:2])
        with open(os.path.join(w, LAB_REL, "JOURNAL.md"), encoding="utf-8") as f:
            self.assertIn("x is 1", f.read())
        self.assertTrue(any(o["path"] == "outputs/summary.json" for o in m["outputs"]))

    def test_failure_is_recorded_like_success(self):
        w = self.clone()
        p = self.labrun(w, "run", "--name", "fails", "--", sys.executable, "-c", "import sys; print('boom'); sys.exit(3)",
                        env={"LAB_BRANCH": "t-fail"})
        self.assertEqual(p.returncode, 3)
        m = self.manifest(w)
        self.assertEqual((m["status"], m["exit_code"]), ("failed", 3))
        self.assertIn("failed", self.remote_log("t-fail")[0])

    def test_secret_in_output_never_reaches_git(self):
        w = self.clone()
        self.labrun(w, "run", "--name", "leaky", "--hypothesis", "x", "--", sys.executable, "-c",
                    f"import os;print('token {FAKE[:3]}' + '{FAKE[3:]}');open(os.environ['LAB_RUN_OUT']+'/o.txt','w').write('{FAKE[:3]}'+'{FAKE[3:]}')",
                    env={"LAB_BRANCH": "t-secret"})
        m = self.manifest(w)
        self.assertGreaterEqual(len(m["redactions"]), 2)
        history = self.sh(["git", "log", "-p", "--all"], cwd=self.remote).stdout
        self.assertNotIn(FAKE, history)
        self.assertIn("[REDACTED:github-token]", history)

    def test_secret_in_command_line_is_scrubbed_from_manifest(self):
        w = self.clone()
        self.labrun(w, "run", "--name", "argv", "--", sys.executable, "-c", "pass", f"--token={FAKE}",
                    env={"LAB_BRANCH": "t-argv"})
        self.assertNotIn(FAKE, self.sh(["git", "log", "-p", "--all"], cwd=self.remote).stdout)

    def test_main_is_refused(self):
        w = self.clone()
        p = self.labrun(w, "run", "--name", "to main", "--", sys.executable, "-c", "pass", env={"LAB_BRANCH": "main"})
        self.assertIn("refusing to push to protected branch", p.stderr)
        self.assertEqual(self.sh(["git", "branch", "--list", "main"], cwd=self.remote).stdout.strip(), "")
        st = json.loads(self.labrun(w, "status", env={"LAB_BRANCH": "main"}).stdout)
        self.assertIsNotNone(st["pending_push"])

    def test_two_sessions_push_to_the_same_branch(self):
        a, b = self.clone(), self.clone()
        self.labrun(a, "run", "--name", "first", "--", sys.executable, "-c", "pass", env={"LAB_BRANCH": "t-race"}, check=True)
        p = self.labrun(b, "run", "--name", "second", "--", sys.executable, "-c", "pass", env={"LAB_BRANCH": "t-race"})
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("pushed", p.stdout)
        log = self.remote_log("t-race")
        self.assertEqual(sum("registered" in s for s in log), 2, log)
        journal = self.sh(["git", "show", f"t-race:{LAB_REL}/JOURNAL.md"], cwd=self.remote).stdout
        self.assertIn("-first-", journal)
        self.assertIn("-second-", journal)

    def test_timeout_is_recorded(self):
        w = self.clone()
        t = time.time()
        p = self.labrun(w, "run", "--name", "slow", "--timeout", "2", "--", "sleep", "30", env={"LAB_BRANCH": "t-timeout"})
        self.assertLess(time.time() - t, 25)
        self.assertEqual(self.manifest(w)["status"], "timeout")
        self.assertNotEqual(p.returncode, 0)

    def test_interrupt_is_recorded(self):
        w = self.clone()
        proc = subprocess.Popen([sys.executable, "-I", f"{LAB_REL}/infra/labrun.py", "run", "--name", "interrupted",
                                 "--", "sleep", "30"], cwd=w, env={**self.env, "LAB_BRANCH": "t-int"},
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(3)
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=60)
        self.assertEqual(self.manifest(w)["status"], "interrupted")
        self.assertIn("interrupted", self.remote_log("t-int")[0])

    def test_large_output_kept_as_hash_only(self):
        w = self.clone()
        self.labrun(w, "run", "--name", "big", "--", sys.executable, "-c",
                    "import os;open(os.environ['LAB_RUN_OUT']+'/big.bin','wb').write(b'a'*(6<<20));open(os.environ['LAB_RUN_OUT']+'/small.txt','w').write('ok')",
                    env={"LAB_BRANCH": "t-big"}, check=True)
        m = self.manifest(w)
        self.assertEqual([o["path"] for o in m["outputs"]], ["outputs/small.txt"])
        self.assertEqual(m["not_committed"][0]["bytes"], 6 << 20)
        self.assertEqual(len(m["not_committed"][0]["sha256"]), 64)

    def test_hook_blocks_a_manual_commit_with_a_key(self):
        w = self.clone()
        with open(os.path.join(w, LAB_REL, "notes.txt"), "w") as f:
            f.write(f"key {FAKE}\n")
        self.sh(["git", "add", f"{LAB_REL}/notes.txt"], cwd=w)
        p = self.sh(["git", "commit", "-m", "notes"], cwd=w, check=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("github-token", p.stderr)
        self.assertNotIn(FAKE, p.stderr)

    def test_gather_unions_runs_across_branches(self):
        a = self.clone()
        self.labrun(a, "run", "--name", "on-branch-x", "--", sys.executable, "-c", "pass", env={"LAB_BRANCH": "t-x"}, check=True)
        b = self.clone()
        p = self.labrun(b, "gather", env={"LAB_BRANCH": "t-y"})
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(any("on-branch-x" in d for d in os.listdir(os.path.join(b, LAB_REL, "runs"))))
        self.assertIn("gather:", self.remote_log("t-y")[0])

    def test_checkpoint_imports_scratch_and_records_large_files(self):
        w = self.clone()
        scratch = os.path.join(self.tmp.name, f"scratch{self.n}")
        os.makedirs(scratch)
        with open(os.path.join(scratch, "step.py"), "w") as f:
            f.write("print('research step')\n")
        with open(os.path.join(scratch, "huge.json"), "wb") as f:
            f.write(b"0" * (6 << 20))
        p = self.labrun(w, "checkpoint", "-m", "shift end", "--import", f"{scratch}:topo/scratch", env={"LAB_BRANCH": "t-ckpt"})
        self.assertEqual(p.returncode, 0, p.stderr)
        files = self.sh(["git", "ls-tree", "-r", "--name-only", "t-ckpt"], cwd=self.remote).stdout
        self.assertIn(f"{LAB_REL}/topo/scratch/step.py", files)
        self.assertNotIn("huge.json\n", files.replace("LARGE_FILES.json", ""))
        ptr = json.loads(self.sh(["git", "show", f"t-ckpt:{LAB_REL}/topo/scratch/LARGE_FILES.json"], cwd=self.remote).stdout)
        self.assertEqual(ptr[0]["bytes"], 6 << 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
