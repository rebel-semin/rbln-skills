# <title: model, what happens, the setting that triggers it>

**kind**: <compile bug | runtime crash | precision drift | decode TPOT | profile trace | ...>

## Symptom | Measured | Produces

<error-ending: exception type and exact message fragment, as a fenced block>
<metric-ending: the numbers seen on the source server, with conditions>
<artifact-ending: what files appear under --out>

## Expected

<what should have happened instead / the reference value>

## Found on

- <NPU name (e.g. ATOM-Max RBLN-CA25)>, KMD <x.y.z>, Python <x.y>
- rebel-compiler <ver>, optimum-rbln <ver>, torch <ver>, transformers <ver>

## Weights

<random-init from <HF id> config (symptom re-verified) | pretrained <HF id> | local checkpoint, pass its path with --model; obtained from <where>>

## Requirements

- rebel-compiler==<ver>   (internal index)
- optimum-rbln==<ver>     (internal index)
- transformers==<ver>
- <other pinned package>

## Run

```bash
python main.py --device 0          # <expected duration>, one idle device
```

## Layout

- `main.py` — entry point; runs the whole path top to bottom
- `<module>.py` — <one line: what it implements and why it could not be inlined>
- `data/<file>` — <one line: what it is, how it was produced, size>

## Notes

- <what was replaced relative to the original: local paths -> args, dataset -> synthetic input, ...>
- <what was removed: logging, unrelated stages, ...>
- <anything that had to stay: e.g. real weights because random-init did not reproduce>
