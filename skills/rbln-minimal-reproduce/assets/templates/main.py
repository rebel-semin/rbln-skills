"""RBLN minimal repro

kind      : <free text: compile bug | runtime crash | precision drift | decode TPOT | profile trace | ...>
title     : <one line: model, what happens, the setting that triggers it>
symptom   : <error-ending: exception type and the exact message fragment>
measured  : <metric-ending: the number(s) seen on the source server, with conditions>
produces  : <artifact-ending: what files appear under --out>
expected  : <what should have happened instead / the reference value>
found on  : <NPU name (e.g. ATOM-Max RBLN-CA25)>, KMD <x.y.z>, Python <x.y>
            rebel-compiler <ver>, optimum-rbln <ver>, torch <ver>, transformers <ver>
weights   : <random-init from <HF id> config (symptom re-verified) | pretrained <HF id> | local checkpoint via --model>
run       : python main.py [--device N]         # <expected duration>, one idle device
deps      : - rebel-compiler==<ver>   (internal index)
            - optimum-rbln==<ver>     (internal index)
            - transformers==<ver>
"""
import argparse
import sys
import time

import rebel
import torch
import transformers
import optimum.rbln
from transformers import AutoConfig, AutoModelForCausalLM
from optimum.rbln import <RBLNModelClass>, <RBLNModelClassConfig>


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="<HF id>", help="HF id or local path")
    ap.add_argument("--weights", choices=("random", "pretrained"), default="random")
    ap.add_argument("--device", type=int, default=0, help="container-visible RBLN id")
    ap.add_argument("--out", default="./out")            # keep only if files are written
    return ap.parse_args()


args = parse_args()

if args.weights == "random":
    torch.manual_seed(0)
    model = AutoModelForCausalLM.from_config(AutoConfig.from_pretrained(args.model))
else:
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.float32)
model.eval()

# --- body: the original code path, inlined, same API layer as where it was found ---
rbln_config = <RBLNModelClassConfig>(
    batch_size=1,
    max_seq_len=<n>,
    device=args.device,
)
t0 = time.perf_counter()
compiled = <RBLNModelClass>.from_model(model, rbln_config=rbln_config)   # error-ending: this line raises
print(f"compile {time.perf_counter() - t0:.0f}s")

# --- ending: keep exactly one of the three ---
# error   : nothing here; the exception above is the result.
# metric  : print(f"RESULT: <metric> p50 {p50:.1f} ms  p95 {p95:.1f} ms  (<conditions>)")
# artifact: compiled.save_pretrained(args.out); print("RESULT: wrote", sorted(os.listdir(args.out)))
