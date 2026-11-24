"""Tamper drills for verify.py on a scratch clone with full history. Every drill must turn a check red.

Run: python3 -I lab/knowledge-frontier/infra/tests/test_verify.py   (needs numpy for the recompute check)
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_REPO = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE, capture_output=True, text=True).stdout.strip()
LAB_REL = "lab/knowledge-frontier"
ENV = {"PATH": os.environ["PATH"], "HOME": tempfile.gettempdir(), "GIT_CONFIG_GLOBAL": os.devnull,
       "GIT_CONFIG_SYSTEM": os.devnull, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@localhost",
       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@localhost", "LANG": "C.UTF-8"}


def sh(cmd, cwd, check=True):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=ENV)
    if check and p.returncode != 0:
        raise AssertionError(f"{cmd}: {p.stdout[-800:]} {p.stderr[-800:]}")
    return p


class TestVerify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = os.path.join(self.tmp.name, "r")
        branch = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], SRC_REPO).stdout.strip()
        sh(["git", "clone", "-q", "--no-hardlinks", "-b", branch, SRC_REPO, self.repo], self.tmp.name)
        # the working tree under test may be ahead of HEAD: commit it on top, as a plain commit
        lab = os.path.join(self.repo, LAB_REL)
        for d in ("infra",):
            shutil.rmtree(os.path.join(lab, d))
            shutil.copytree(os.path.join(SRC_REPO, LAB_REL, d), os.path.join(lab, d),
                            ignore=shutil.ignore_patterns("__pycache__", ".last_*"))
        sh(["git", "add", "-A"], self.repo)
        sh(["git", "-c", "core.hooksPath=/dev/null", "commit", "-q", "--allow-empty", "-m", "tools under test"], self.repo)
        self.lab = lab

    def tearDown(self):
        self.tmp.cleanup()

    def verify(self, cwd=None):
        return sh([sys.executable, "-I", "infra/verify.py"], cwd or self.lab, check=False)

    def commit(self, msg):
        sh(["git", "-c", "core.hooksPath=/dev/null", "commit", "-q", "-am", msg], self.repo)

    def a_run(self):
        runs = sorted(os.listdir(os.path.join(self.lab, "runs")))
        return [r for r in runs if "cost-per-experiment" in r][-1]

    def test_clean_clone_passes(self):
        p = self.verify()
        self.assertEqual(p.returncode, 0, p.stdout[-2000:])
        self.assertIn("PASS  run records sealed", p.stdout)

    def test_forged_seal_in_an_unrelated_commit_fails(self):
        rid = self.a_run()
        path = os.path.join(self.lab, "runs", rid, "manifest.json")
        m = json.load(open(path, encoding="utf-8"))
        m["verdict"] = "pass"
        m.setdefault("summary", {})["headline"] = "T4 is 1000x faster"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(m, f)
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()
        self.commit(f"tidy up\n\nmanifest-sha256 {rid}: {h}\nmanifest-sha256: {h}")
        p = self.verify()
        self.assertEqual(p.returncode, 1)
        self.assertIn("not labrun's", p.stdout)

    def test_deleted_run_fails(self):
        rid = self.a_run()
        sh(["git", "rm", "-rq", f"{LAB_REL}/runs/{rid}"], self.repo)
        self.commit("remove a run")
        p = self.verify()
        self.assertEqual(p.returncode, 1)
        self.assertIn("record is gone", p.stdout)

    def test_edited_result_number_fails(self):
        path = os.path.join(self.lab, "topo", "ipf_out.json")
        rows = json.load(open(path))
        rows[100]["obs"] += 999
        with open(path, "w") as f:
            json.dump(rows, f)
        self.commit("edit a row")
        p = self.verify()
        self.assertEqual(p.returncode, 1)
        self.assertIn("topo/ipf_out.json changed", p.stdout)

    def test_appended_cost_line_fails(self):
        with open(os.path.join(self.lab, "seal", "arms_results.md"), "a") as f:
            f.write("ARM Z (0.5B, all, K4, s27): mean .29->.99->.99; 1 min\n")
        self.commit("add an arm")
        p = self.verify()
        self.assertEqual(p.returncode, 1)
        self.assertIn("seal/arms_results.md changed", p.stdout)

    def test_shallow_clone_is_not_a_success(self):
        shallow = os.path.join(self.tmp.name, "shallow")
        sh(["git", "clone", "-q", "--depth", "1", "file://" + self.repo, shallow], self.tmp.name)
        p = self.verify(os.path.join(shallow, LAB_REL))
        self.assertEqual(p.returncode, 3, p.stdout[-1500:])
        self.assertIn("SKIP  run records sealed", p.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
