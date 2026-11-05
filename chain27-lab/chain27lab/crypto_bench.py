"""Measures real Ed25519 and SHA-256 costs on this machine with the audited
`cryptography` library. The verify time feeds the simulator as CPU cost per vote."""
import hashlib
import os
import time


def bench(n=2000):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    pub = key.public_key()
    msg = os.urandom(150)
    t0 = time.perf_counter()
    sigs = [key.sign(msg) for _ in range(n)]
    t1 = time.perf_counter()
    for s in sigs:
        pub.verify(s, msg)
    t2 = time.perf_counter()
    blob = os.urandom(1_000_000)
    t3 = time.perf_counter()
    for _ in range(20):
        hashlib.sha256(blob).digest()
    t4 = time.perf_counter()
    return {
        "ed25519_sign_us": (t1 - t0) / n * 1e6,
        "ed25519_verify_us": (t2 - t1) / n * 1e6,
        "sha256_mb_per_s": 20 / (t4 - t3),
    }


if __name__ == "__main__":
    print(bench())
