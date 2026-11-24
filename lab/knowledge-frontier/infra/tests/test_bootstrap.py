"""Empty-machine tests for bootstrap.sh against a local bare repository standing in for GitHub.

The environment is wiped (env -i semantics): empty HOME, no git config, only PATH and the machine's
proxy/CA variables, so pip can reach PyPI the way a fresh cloud machine would. Needs network to PyPI.
Run: python3 -I lab/knowledge-frontier/infra/tests/test_bootstrap.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_REPO = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE, capture_output=True, text=True).stdout.strip()
LAB_REL = "lab/knowledge-frontier"
PASS_THROUGH = ["HTTPS_PROXY", "https_proxy", "no_proxy", "NO_PROXY", "SSL_CERT_FILE", "PIP_CERT", "REQUESTS_CA_BUNDLE"]


class TestBootstrap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = cls.tmp.name
        cls.env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": os.path.join(t, "home"), "LANG": "C.UTF-8",
                   "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
                   **{k: os.environ[k] for k in PASS_THROUGH if k in os.environ}}
        os.makedirs(cls.env["HOME"])
        ident = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@localhost", "GIT_COMMITTER_NAME": "t",
                 "GIT_COMMITTER_EMAIL": "t@localhost"}
        stage = os.path.join(t, "stage")
        cls.run_(["git", "clone", "-q", "--no-hardlinks", SRC_REPO, stage])
        lab = os.path.join(stage, LAB_REL)
        cls.run_(["git", "checkout", "-q", "-B", "lab-tools"], cwd=stage)
        shutil.rmtree(lab)  # inside our own temporary clone; run records and JOURNAL come along unchanged
        shutil.copytree(os.path.join(SRC_REPO, LAB_REL), lab, ignore=shutil.ignore_patterns(".venv", "__pycache__", "data"))
        cls.run_(["git", "add", "-A"], cwd=stage)
        cls.run_(["git", "commit", "-q", "-m", "tools", "--allow-empty"], cwd=stage, env=ident)
        # a branch with NEWER lab content but without the tools (like the branch of 23.11 before this work)
        base = subprocess.run(["git", "log", "--format=%H", "--", f"{LAB_REL}/README.md"], cwd=SRC_REPO,
                              capture_output=True, text=True).stdout.split()[-1]
        cls.run_(["git", "checkout", "-q", "-b", "newer-without-tools", base], cwd=stage)
        with open(os.path.join(stage, LAB_REL, "README.md"), "a") as f:
            f.write("\nnewer note\n")
        time.sleep(1.1)
        cls.run_(["git", "commit", "-q", "-am", "newer lab content"], cwd=stage, env=ident)
        # an OLD copy of the tools on a branch whose tip is newer (unrelated commit): must not be chosen
        first_tools = subprocess.run(["git", "log", "--reverse", "--format=%H", "--", f"{LAB_REL}/infra/labrun.py"],
                                     cwd=SRC_REPO, capture_output=True, text=True).stdout.split()[0]
        cls.run_(["git", "checkout", "-q", "-b", "stale-tools", first_tools], cwd=stage)
        with open(os.path.join(stage, "backend", "unrelated.txt"), "w") as f:
            f.write("newer unrelated commit\n")
        time.sleep(1.1)
        cls.run_(["git", "add", "backend/unrelated.txt"], cwd=stage)
        cls.run_(["git", "commit", "-q", "-m", "unrelated newer commit"], cwd=stage, env=ident)
        cls.remote = os.path.join(t, "remote.git")
        cls.run_(["git", "clone", "-q", "--bare", stage, cls.remote])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def run_(cls, cmd, cwd=None, env=None, check=True):
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env={**cls.env, **(env or {})})
        if check and p.returncode != 0:
            raise AssertionError(f"{cmd} rc={p.returncode}\n{p.stdout[-2000:]}\n{p.stderr[-2000:]}")
        return p

    def bootstrap(self, target, **env):
        return self.run_(["bash", os.path.join(SRC_REPO, LAB_REL, "infra", "bootstrap.sh"), target],
                         env={"LAB_REPO_URL": "file://" + self.remote, **env}, check=False)

    def test_empty_machine_then_rerun_keeps_local_work(self):
        target = os.path.join(self.tmp.name, "machine", "esh27-core")
        t = time.time()
        p = self.bootstrap(target)
        first = time.time() - t
        out = p.stdout + p.stderr
        self.assertEqual(p.returncode, 0, out[-3000:])
        self.assertIn("branch: lab-tools", out)  # not stale-tools, whose tip is newer
        self.assertRegex(out, r"verify: \d+ pass, 0 fail, 0 skipped")
        self.assertIn("PASS  run records sealed in git history", out)
        self.assertIn("warning: newer-without-tools has newer lab changes", out)
        self.assertNotIn("warning: stale-tools", out)
        print(f"\n  empty machine -> verified lab: {first:.1f} s", file=sys.stderr)
        # local work that was never pushed must survive a second bootstrap in the same directory
        with open(os.path.join(target, LAB_REL, "local-note.md"), "w") as f:
            f.write("unpushed work\n")
        self.run_(["git", "add", f"{LAB_REL}/local-note.md"], cwd=target)
        self.run_(["git", "commit", "-q", "-m", "local unpushed work"], cwd=target)
        p = self.bootstrap(target)
        out = p.stdout + p.stderr
        self.assertEqual(p.returncode, 0, out[-3000:])
        self.assertIn("not on the remote; keeping them", out)
        log = self.run_(["git", "log", "--format=%s", "-3"], cwd=target).stdout
        self.assertIn("local unpushed work", log)

    def test_diverged_tools_stop_bootstrap_unless_a_branch_is_named(self):
        # an OLD copy of the tools plus one fresh edit in infra/: must not win by recency
        remote2 = os.path.join(self.tmp.name, "remote2.git")
        self.run_(["git", "clone", "-q", "--bare", self.remote, remote2])
        work = os.path.join(self.tmp.name, "w2")
        self.run_(["git", "clone", "-q", "-b", "stale-tools", "file://" + remote2, work])
        with open(os.path.join(work, LAB_REL, "infra", "hosts.py"), "a") as f:
            f.write("# one fresh comment line\n")
        ident = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@localhost", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@localhost"}
        self.run_(["git", "-c", "core.hooksPath=/dev/null", "commit", "-q", "-am", "touch infra"], cwd=work, env=ident)
        self.run_(["git", "push", "-q", "origin", "HEAD:refs/heads/stale-infra"], cwd=work)
        p = self.run_(["bash", os.path.join(SRC_REPO, LAB_REL, "infra", "bootstrap.sh"), os.path.join(self.tmp.name, "m2")],
                      env={"LAB_REPO_URL": "file://" + remote2}, check=False)
        out = p.stdout + p.stderr
        self.assertEqual(p.returncode, 2, out[-2000:])
        self.assertIn("diverged", out)
        p = self.run_(["bash", os.path.join(SRC_REPO, LAB_REL, "infra", "bootstrap.sh"), os.path.join(self.tmp.name, "m3")],
                      env={"LAB_REPO_URL": "file://" + remote2, "LAB_SOURCE_BRANCH": "lab-tools"}, check=False)
        self.assertEqual(p.returncode, 0, (p.stdout + p.stderr)[-2000:])


if __name__ == "__main__":
    unittest.main(verbosity=2)
