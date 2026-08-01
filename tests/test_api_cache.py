# Tests de cache + reintentos para api.py — run from repo cwd
import io
import json
import os
import sys
import time
import types
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import api

# ── 1. cache: misma URL no vuelve a la red dentro del TTL ──────
llamadas = []

class _FakeResp:
    def __init__(self, data):
        self._data = data
    def read(self):
        return json.dumps(self._data).encode()
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False

def fake_urlopen(req, timeout=0, context=None):
    llamadas.append(req.full_url)
    return _FakeResp({"ok": 1})

api.urllib.request.urlopen = fake_urlopen
api._cache.clear()

r1 = api._fetch_json("https://x/1", 10)
r2 = api._fetch_json("https://x/1", 10)
r3 = api._fetch_json("https://x/2", 10)
assert r1 == {"ok": 1} and r2 == {"ok": 1} and r3 == {"ok": 1}
assert llamadas == ["https://x/1", "https://x/2"], f"deberia llamar 2 veces, llamo {len(llamadas)}"
print("PASS cache: misma URL dentro del TTL -> 1 sola llamada de red")

# ── 2. cache expira despues del TTL ────────────────────────────
api._cache.clear()
llamadas.clear()
fake_urlopen.__dict__["n"] = 0

def fake_urlopen_ttl(req, timeout=0, context=None):
    llamadas.append(req.full_url)
    return _FakeResp({"n": len(llamadas)})

api.urllib.request.urlopen = fake_urlopen_ttl
api._fetch_json("https://x/t", 10)
api._fetch_json("https://x/t", 10)  # cache hit
api._cache["https://x/t"] = (time.time() - 61, {"n": 999})  # expirar
api._fetch_json("https://x/t", 10)  # cache miss -> red
assert len(llamadas) == 2, f"deberia llamar 2 veces (1 + 1 tras expirar), llamo {len(llamadas)}"
print("PASS cache: expira tras TTL -> vuelve a la red")

# ── 3. 429 -> reintenta con backoff y devuelve datos ───────────
api._cache.clear()
intentos = []

class _Fake429:
    def __init__(self):
        self.code = 429
        self.reason = "Too Many Requests"

def fake_urlopen_429(req, timeout=0, context=None):
    intentos.append(req.full_url)
    if len(intentos) < 3:
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", None, None)
    return _FakeResp({"ok": "despues de 429"})

api.urllib.request.urlopen = fake_urlopen_429
api.time.sleep = lambda s: None  # no esperar de verdad
buf = io.StringIO()
api.console = type(api.console)(file=buf, force_terminal=False)

r = api._fetch_json("https://x/429", 10)
assert r == {"ok": "despues de 429"}, f"deberia recuperarse, obtuve {r!r}"
assert len(intentos) == 3, f"deberia reintentar 3 veces, fue {len(intentos)}"
print("PASS 429: reintenta 3 veces con backoff y se recupera")

# ── 4. 429 persistente -> devuelve None y avisa ────────────────
api._cache.clear()
intentos.clear()
buf2 = io.StringIO()
api.console = type(api.console)(file=buf2, force_terminal=False)

def fake_urlopen_429_fail(req, timeout=0, context=None):
    intentos.append(req.full_url)
    raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", None, None)

api.urllib.request.urlopen = fake_urlopen_429_fail
r = api._fetch_json("https://x/429b", 10)
assert r is None, "deberia devolver None tras 3 fallos"
assert "429" in buf2.getvalue(), f"deberia avisar 429, salida: {buf2.getvalue()!r}"
print("PASS 429 persistente: None + aviso al usuario")

print("\nTODOS LOS TESTS DE API PASARON")
