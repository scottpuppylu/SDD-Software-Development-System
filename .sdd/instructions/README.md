# Stage Instruction Layer

Place the authoritative Stage-specific instruction text here as:

- `stage-01.md`
- `stage-02.md`
- ...
- `stage-10.md`

`stages.yaml` is the machine governance contract; these files are the reasoning/executor instructions. The Orchestrator loads both. This separation prevents prompt text from becoming the runtime authority registry and prevents the registry from losing the richer Stage reasoning behavior.

M3 intentionally does not fabricate missing Stage Instructions. Existing validated SDD 01–10 instruction artifacts should be imported here in a later migration step.
