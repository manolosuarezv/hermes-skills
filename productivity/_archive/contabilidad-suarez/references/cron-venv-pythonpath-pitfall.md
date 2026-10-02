# Cron/Hermes env POISONS the contabilidad venv (cryptography crash)

## Symptom
Running the contabilidad backup/digest scripts under the Hermes cron (or any
shell that inherited the gateway's environment) crashes at import time:

```
Traceback (most recent call last):
  ...
  File ".../hermes-agent/venv/lib/python3.11/site-packages/cryptography/exceptions.py", line 9, in <module>
    from cryptography.hazmat.bindings._rust import exceptions as rust_exceptions
ImportError: dlopen(.../cryptography/hazmat/bindings/_rust.abi3.so, 0x0002):
  symbol not found in flat namespace '_PyType_GetName'
```

## Root cause
The Hermes gateway/cron exports:
  PYTHONPATH=/Users/manuelsuarez/.hermes/hermes-agent:.../hermes-agent/venv/lib/python3.11/site-packages
When `contabilidad/venv/bin/python3` (a symlink to system py3.9) runs, that
PYTHONPATH is prepended, so `cryptography` from the py3.11 hermes-agent venv is
loaded into py3.9 -> ABI symbol mismatch (`_PyType_GetName` is a 3.13 symbol).

The contabilidad venv HAS its own correct `cryptography-50.0.0` for py3.9 at
`contabilidad/venv/lib/python3.9/site-packages/cryptography`. It just gets
shadowed by the poisoned PYTHONPATH.

## Reproduction / proof
```
# broken (inherits PYTHONPATH)
./venv/bin/python3 -c "import cryptography"
# works (clean env)
env -u PYTHONPATH ./venv/bin/python3 -c "import cryptography,sys; print(cryptography.__file__)"
# -> .../contabilidad/venv/lib/python3.9/site-packages/cryptography/__init__.py
```

## Fix
Strip PYTHONPATH before spawning the script. `cierre_diario.py` does this via
`_clean_env()` (pops PYTHONPATH from os.environ before subprocess.run).
`backup_qbex.py` / `digest_diario.py` are only safe when spawned by
`cierre_diario.py` (clean env) -- if you call them directly, prefix `env -u PYTHONPATH`.

Note: `registrar.py` does NOT import cryptography/google, so it is unaffected
and can run normally under the poisoned env.
