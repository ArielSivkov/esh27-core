"""Tests for secretscan. Fake credentials are assembled at runtime so this file itself stays clean."""
import os
import random
import string
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import secretscan  # noqa: E402

R = random.Random(7)
def rnd(n, alphabet=string.ascii_letters + string.digits):
    return "".join(R.choice(alphabet) for _ in range(n))

J = "".join  # joining pieces keeps literal patterns out of the source
POSITIVE = {
    "github-token": J(["gh", "p_", rnd(36)]),
    "huggingface-token": J(["h", "f_", rnd(34)]),
    "anthropic-key": J(["sk-", "ant-", rnd(40)]),
    "google-api-key": J(["AI", "za", rnd(35)]),
    "aws-access-key": J(["AK", "IA", rnd(16, string.ascii_uppercase + string.digits)]),
    "kaggle-json-key": J(['{"username": "u", "ke', 'y": "', rnd(32, "0123456789abcdef"), '"}']),
    "kaggle-env-key": J(["KAGGLE", "_KEY=", rnd(32, "0123456789abcdef")]),
    "private-key": J(["-----BEGIN ", "RSA PRIVATE", " KEY-----"]),
    "telegram-bot-token": J(["123456789", ":AA", rnd(33)]),
    "generic-secret": J(['api_', 'key = "', rnd(24), '"']),
    "url-credentials": J(["https://user", ":", rnd(12), "@example.net/x"]),
    "phone-il": J(["call 05", "2-555", "1234."]),
    "email": J(["write to some", ".one@", "gmail", ".com"]),
}
NEGATIVE = [
    "0.05047137568930365 0.0512345678 1203.0147 math/0512345 2610.31672",   # floats and arXiv ids
    'token = os.environ.get("HF_TOKEN")', 'password = "changeme-placeholder-123"',
    "git clone git@github.com:owner/repo.git", "Co-Authored-By: Claude <noreply@anthropic.com>",
    '{"key": "not-a-hex-key"}', "sha256 62dc5c5cbec42ae8fc2e91a2f640e99af1260494f885ae7b173c347b4ed6fa1a",
    "loss 0.523 step 0523456789x", "@property def x(self): pass", "npm i @scope/pkg@1.2.3",
]


class TestScanner(unittest.TestCase):
    def test_every_kind_is_caught(self):
        for kind, sample in POSITIVE.items():
            kinds = [h[3] for h in secretscan.find(f"prefix {sample} suffix")]
            self.assertIn(kind, kinds, f"{kind} not detected")

    def test_no_false_positives(self):
        for text in NEGATIVE:
            self.assertEqual([], secretscan.find(text), text)

    def test_redaction_removes_value(self):
        sample = POSITIVE["github-token"]
        text = f"log line with {sample} inside"
        out = secretscan.redact(text, secretscan.find(text))
        self.assertNotIn(sample, out)
        self.assertIn("[REDACTED:github-token]", out)

    def test_allowlist_by_digest(self):
        sample = POSITIVE["email"].split()[-1]
        allow = {("email", secretscan._digest(sample))}
        self.assertEqual([], secretscan.find(sample, allow))

    def test_findings_never_contain_the_value(self):
        sample = POSITIVE["huggingface-token"]
        found = secretscan.scan_bytes("f.txt", sample.encode(), set())
        self.assertTrue(found)
        self.assertNotIn(sample, repr(found))


if __name__ == "__main__":
    unittest.main()
