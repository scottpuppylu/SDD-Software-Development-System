# Stage09 Verification Failure Report — Fresh Normal-Route Run

```text
STAGE09_RESULT = FAIL
FAILURE_CLASS = IMPLEMENTATION_GAP
VERIFICATION_BASELINE = 968a9b09bc78fd7aa4b41ed502b96102e19fa77d
ENTRY_ROUTE = NORMAL_CURRENT_AUTHORITY_STAGE07_TO_STAGE08
AUTHORITATIVE_COMMAND = .\.venv\Scripts\python.exe -m pytest -q tests
PYTEST_EXIT_CODE = 1
PYTEST_SUMMARY = 2 failed, 596 passed, 486 subtests passed in 1305.62s
TERMINATION = NATURAL
TEMP_TMP_ISOLATED = YES
```

The durable local runner completed naturally with complete stdout, empty stderr, captured exit status, and isolated TEMP/TMP. Git integrity checks passed. Historical Stage09 FAIL evidence is preserved at `.sdd/evidence/20260924T111428.4945804Z-stage09-post-convergence.json`.

Failure cluster `STAGE08_SAFE_PAUSE_FIXTURE_SCOPE_COMPATIBILITY` (2 tests): V1118 fixture-created paths `src/only.py` and `src/two.py` were classified as unauthorized at Stage08 scope enforcement, raising `CodexAdapterError` before the expected assertions. This run creates no repair task.

Runtime: `C:\Users\user\AppData\Local\Temp\sdd-stage09-qualifying-ecf91b34b0ef44478475463fa2bac771`

- command SHA-256: `9DEF723850A56D72CBD1C6D4B448A12D6456391178383B62F829E8DC6ACA0327`
- stdout SHA-256: `92C2210589645642254DFDB770E777746289830F829CCED8D18578EA71093E99`
- stderr SHA-256: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`
- result SHA-256: `A00F4FE446EF0EF6FEFEF39F784480EA9D9AD3550E2D13DFFCB540A755246992`
