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

    def test_secret_in_command_line_is_scrubbed_without_hooks(self):
        # hooks deliberately replaced by an empty directory: labrun itself must keep the token out of history
        w = self.clone()
        empty = os.path.join(self.tmp.name, f"nohooks{self.n}")
        os.makedirs(empty)
        self.sh(["git", "config", "core.hooksPath", empty], cwd=w)
        p = self.labrun(w, "run", "--name", "argv", "--", sys.executable, "-c", "pass", f"--token={FAKE}",
                        env={"LAB_BRANCH": "t-argv"})
        self.assertEqual(p.returncode, 0, p.stderr)
        log = self.remote_log("t-argv")
        self.assertEqual(len(log), 2, log)  # registered + result, both pushed
        self.assertNotIn(FAKE, self.sh(["git", "log", "-p", "--all"], cwd=self.remote).stdout)
        self.assertNotIn(FAKE, open(os.path.join(w, LAB_REL, "runs", sorted(os.listdir(os.path.join(w, LAB_REL, "runs")))[-1],
                                                 "manifest.json"), encoding="utf-8").read())

    def test_main_and_ref_like_branch_names_are_refused_before_running(self):
        w = self.clone()
        marker = os.path.join(self.tmp.name, f"ran-main{self.n}")
        for b in ["main", "Main", " main", "main ", "refs/heads/main", "master", "origin/main", "heads/main",
                  "+main", "@", "HEAD", "head", "feature/../main", "release-1"]:
            p = self.labrun(w, "run", "--name", "to main", "--", "touch", marker, env={"LAB_BRANCH": b})
            self.assertEqual(p.returncode, 2, (b, p.stderr))
            self.assertIn("refusing", p.stderr, b)
        self.assertFalse(os.path.exists(marker))
        branches = self.sh(["git", "for-each-ref", "--format=%(refname:short)", "refs/heads"], cwd=self.remote).stdout.split()
        self.assertFalse([b for b in branches if "main" in b.lower() or b in ("@", "head", "HEAD")], branches)

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
        # never deleted: moved to the ignored data/ directory
        kept = os.path.join(w, m["not_committed"][0]["kept_locally"])
        self.assertEqual(os.path.getsize(kept), 6 << 20)
        self.assertNotIn("data/", self.sh(["git", "ls-tree", "-r", "--name-only", "t-big"], cwd=self.remote).stdout)

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

    def test_unrelated_staged_file_stays_out_of_run_commits(self):
        w = self.clone()
        with open(os.path.join(w, "unrelated.txt"), "w") as f:
            f.write("not part of any run\n")
        self.sh(["git", "add", "unrelated.txt"], cwd=w)
        self.labrun(w, "run", "--name", "clean commit", "--", sys.executable, "-c", "pass",
                    env={"LAB_BRANCH": "t-clean"}, check=True)
        files = self.sh(["git", "ls-tree", "-r", "--name-only", "t-clean"], cwd=self.remote).stdout.split()
        self.assertNotIn("unrelated.txt", files)
        self.assertIn("unrelated.txt", self.sh(["git", "diff", "--cached", "--name-only"], cwd=w).stdout)
        p = self.labrun(w, "checkpoint", "-m", "x", env={"LAB_BRANCH": "t-clean"})
        self.assertEqual(p.returncode, 2)
        self.assertIn("outside the lab are staged", p.stderr)

    def test_collect_outside_workspace_is_refused(self):
        w = self.clone()
        self.labrun(w, "run", "--name", "collect", "--collect", "/etc/hostname", "--collect", "../../",
                    "--", sys.executable, "-c", "pass", env={"LAB_BRANCH": "t-collect"}, check=True)
        m = self.manifest(w)
        self.assertEqual(m["outputs"], [])
        self.assertEqual(sorted(x["reason"][:7] for x in m["not_committed"]), ["outside", "outside"])

    def test_unsafe_criterion_is_refused_before_anything_runs(self):
        w = self.clone()
        marker = os.path.join(self.tmp.name, f"ran{self.n}")
        p = self.labrun(w, "run", "--name", "evil", "--success-expr", "().__class__.__base__.__subclasses__()",
                        "--", "touch", marker, env={"LAB_BRANCH": "t-evil"})
        self.assertEqual(p.returncode, 2)
        self.assertFalse(os.path.exists(marker))
        self.assertFalse(os.path.isdir(os.path.join(w, LAB_REL, "runs")) and os.listdir(os.path.join(w, LAB_REL, "runs")))

    # ---- red-team findings (24.11.2026): each test reproduces one finding and checks the fix
    def history(self):
        return self.sh(["git", "log", "-p", "--all"], cwd=self.remote).stdout

    def test_F1_private_key_body_is_redacted(self):
        w = self.clone()
        rnd = random.Random(9)
        body = ["".join(rnd.choice(string.ascii_letters + string.digits + "+/") for _ in range(64)) for _ in range(5)]
        key = "".join(["-----BEGIN ", "OPENSSH PRIVATE", " KEY-----\n"]) + "\n".join(body) + "".join(["\n-----END ", "OPENSSH PRIVATE", " KEY-----\n"])
        path = os.path.join(w, "id_test")
        with open(path, "w") as f:
            f.write(key)
        self.labrun(w, "run", "--name", "print key", "--", "cat", path, env={"LAB_BRANCH": "t-key"}, check=True)
        self.labrun(w, "run", "--name", "collect key", "--collect", "id_test", "--", "true", env={"LAB_BRANCH": "t-key"}, check=True)
        h = self.history()
        for line in body:
            self.assertNotIn(line, h)

    def test_F5_launch_errors_are_recorded(self):
        w = self.clone()
        noexec = os.path.join(w, "noexec.sh")
        with open(noexec, "w") as f:
            f.write("#!/bin/sh\necho hi\n")
        noshebang = os.path.join(w, "noshebang.sh")
        with open(noshebang, "w") as f:
            f.write("echo hi\n")
        os.chmod(noshebang, 0o755)
        for args in (["--", noexec], ["--", noshebang], ["--cwd", noexec, "--", "true"], ["--", "no-such-command-xyz"]):
            p = self.labrun(w, "run", "--name", "launch", *args, env={"LAB_BRANCH": "t-launch"})
            self.assertIn(p.returncode, (126, 127), p.stderr)
            self.assertEqual(self.manifest(w)["status"], "launch-error")
        self.assertEqual(sum("launch-error" in x for x in self.remote_log("t-launch")), 4)

    def test_F5_dangling_symlink_in_outputs(self):
        w = self.clone()
        p = self.labrun(w, "run", "--name", "dangling", "--", sys.executable, "-c",
                        "import os;os.symlink('/nonexistent/x', os.environ['LAB_RUN_OUT']+'/broken')",
                        env={"LAB_BRANCH": "t-link"})
        self.assertEqual(p.returncode, 0, p.stderr)
        m = self.manifest(w)
        self.assertEqual(m["status"], "ok")
        self.assertIn("symlink", m["not_committed"][0]["reason"])

    def test_F5_sighup_is_recorded(self):
        w = self.clone()
        proc = subprocess.Popen([sys.executable, "-I", f"{LAB_REL}/infra/labrun.py", "run", "--name", "hup", "--", "sleep", "30"],
                                cwd=w, env={**self.env, "LAB_BRANCH": "t-hup"}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(3)
        proc.send_signal(signal.SIGHUP)
        proc.communicate(timeout=60)
        self.assertEqual(self.manifest(w)["status"], "interrupted")

    def test_F5_recover_after_labrun_is_killed(self):
        w = self.clone()
        proc = subprocess.Popen([sys.executable, "-I", f"{LAB_REL}/infra/labrun.py", "run", "--name", "killed", "--",
                                 "sh", "-c", "echo started; sleep 30"],
                                cwd=w, env={**self.env, "LAB_BRANCH": "t-kill"}, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(3)
        proc.kill()
        proc.communicate(timeout=30)
        self.assertEqual(self.manifest(w)["status"], "registered")
        p = self.labrun(w, "recover", env={"LAB_BRANCH": "t-kill"})
        self.assertIn("recovered 1", p.stdout, p.stderr)
        m = self.manifest(w)
        self.assertEqual(m["status"], "lost")
        self.assertIn("lost", self.remote_log("t-kill")[0])
        with open(os.path.join(w, LAB_REL, "runs", m["run_id"], "log.txt")) as f:
            self.assertIn("started", f.read())

    def test_F6_timeout_kills_a_command_that_ignores_sigterm(self):
        w = self.clone()
        t = time.time()
        self.labrun(w, "run", "--name", "stubborn", "--timeout", "2", "--", "sh", "-c", "trap '' TERM; sleep 40",
                    env={"LAB_BRANCH": "t-stub", "LAB_KILL_GRACE_S": "2"})
        self.assertLess(time.time() - t, 20)
        self.assertEqual(self.manifest(w)["status"], "timeout")

    def test_F7_failed_push_stays_pending_until_sync(self):
        w = self.clone()
        hidden = self.remote + ".away"
        os.rename(self.remote, hidden)
        try:
            p = self.labrun(w, "run", "--name", "offline", "--", "true", env={"LAB_BRANCH": "t-offline"})
            self.assertIn("pending", p.stderr)
            st = json.loads(self.labrun(w, "status").stdout)
            self.assertEqual(st["pending_push"]["branch"], "t-offline")
        finally:
            os.rename(hidden, self.remote)
        self.sh(["git", "checkout", "-q", "-b", "elsewhere"], cwd=w)  # sync must use the stored target, not HEAD's name
        p = self.labrun(w, "sync")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(len(self.remote_log("t-offline")), 2)
        self.assertIsNone(json.loads(self.labrun(w, "status").stdout)["pending_push"])

    def test_F8_big_log_is_capped_and_hashed(self):
        w = self.clone()
        self.labrun(w, "run", "--name", "chatty", "--quiet", "--", sys.executable, "-c",
                    "import sys\nfor i in range(140000): print('line %06d ' % i + 'x' * 40)", env={"LAB_BRANCH": "t-log"}, check=True)
        m = self.manifest(w)
        log = os.path.join(w, LAB_REL, "runs", m["run_id"], "log.txt")
        self.assertLess(os.path.getsize(log), 4.2 * 1048576)
        self.assertGreater(m["log"]["total_bytes"], 6 * 1048576)
        self.assertGreater(m["log"]["omitted_bytes"], 0)
        with open(log) as f:
            text = f.read()
        self.assertIn("line 000000", text)
        self.assertIn("line 139999", text)
        self.assertTrue(os.path.exists(os.path.join(w, m["log"]["local_copy"])))

    def test_F10_parallel_runs_in_one_checkout(self):
        w = self.clone()
        marks = [os.path.join(self.tmp.name, f"par{self.n}-{i}") for i in range(4)]
        procs = [subprocess.Popen([sys.executable, "-I", f"{LAB_REL}/infra/labrun.py", "run", "--name", f"par{i}", "--quiet",
                                   "--", "sh", "-c", f"sleep 1; touch {m}"], cwd=w, env={**self.env, "LAB_BRANCH": "t-par"},
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i, m in enumerate(marks)]
        outs = [p.communicate(timeout=120) for p in procs]
        self.assertEqual([p.returncode for p in procs], [0, 0, 0, 0], [o[1] for o in outs])
        self.assertTrue(all(os.path.exists(m) for m in marks))
        log = self.remote_log("t-par")
        self.assertEqual(sum("registered" in x for x in log), 4, log)
        self.assertEqual(sum(": ok" in x for x in log), 4, log)

    def test_F12_gather_leaves_out_a_bad_record_and_continues(self):
        a = self.clone()
        self.labrun(a, "run", "--name", "good", "--", "true", env={"LAB_BRANCH": "t-good"}, check=True)
        b = self.clone()
        bad = os.path.join(b, LAB_REL, "runs", "20200101T000000Z-bad-0000")
        os.makedirs(bad)
        with open(os.path.join(bad, "log.txt"), "w") as f:
            f.write("contact " + "someone" + "@" + "gmail" + ".com\n")
        with open(os.path.join(bad, "manifest.json"), "w") as f:
            f.write('{"run_id": "20200101T000000Z-bad-0000", "status": "ok"}\n')
        self.sh(["git", "add", "-A"], cwd=b)
        self.sh(["git", "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "bad record"], cwd=b)
        self.sh(["git", "push", "-q", "origin", "HEAD:refs/heads/t-bad"], cwd=b)
        c = self.clone()
        p = self.labrun(c, "gather", env={"LAB_BRANCH": "t-gathered"})
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("left out 1 record", p.stdout)
        runs = os.listdir(os.path.join(c, LAB_REL, "runs"))
        self.assertTrue(any("-good-" in r for r in runs))
        self.assertFalse(any("-bad-" in r for r in runs))

    def test_criterion_cannot_hang_or_exhaust_memory(self):
        w = self.clone()
        t = time.time()
        self.labrun(w, "run", "--name", "greedy", "--success-expr", "len('ab' * 900000000) > 0", "--", "true",
                    env={"LAB_BRANCH": "t-greedy"}, check=True)
        self.assertLess(time.time() - t, 30)
        self.assertTrue(self.manifest(w)["verdict"].startswith("error"), self.manifest(w)["verdict"])

    def test_tracked_file_changes_are_recorded(self):
        w = self.clone()
        target = f"{LAB_REL}/README.md"
        self.labrun(w, "run", "--name", "edits", "--", "sh", "-c", f"echo extra >> {target}", env={"LAB_BRANCH": "t-edit"}, check=True)
        m = self.manifest(w)
        self.assertEqual(m["tracked_changes"]["files"], [target])
        self.assertTrue(os.path.exists(os.path.join(w, LAB_REL, "runs", m["run_id"], "tracked.diff")))

    def test_rebase_with_a_dirty_tree_still_pushes(self):
        a, b = self.clone(), self.clone()
        self.labrun(a, "run", "--name", "first", "--", "true", env={"LAB_BRANCH": "t-dirty"}, check=True)
        with open(os.path.join(b, LAB_REL, "README.md"), "a") as f:
            f.write("uncommitted local edit\n")
        p = self.labrun(b, "run", "--name", "second", "--", "true", env={"LAB_BRANCH": "t-dirty"})
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(sum("registered" in x for x in self.remote_log("t-dirty")), 2)
        with open(os.path.join(b, LAB_REL, "README.md")) as f:
            self.assertIn("uncommitted local edit", f.read())


if __name__ == "__main__":
    unittest.main(verbosity=2)
