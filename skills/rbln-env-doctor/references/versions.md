# Validated version combinations

| Purpose | rebel-compiler | optimum-rbln | vllm-rbln | torch | transformers | Python |
|---|---|---|---|---|---|---|
| batch-1 latency | 0.10.5.dev143 (cp312 wheel) | 0.10.4 | — | 2.10.0+cpu | 4.57.6 | 3.12 (`/opt/python`) |
| serving (vllm-rbln image) | 0.11.0.post1 | 0.11.0.post1 | 0.11.0 | from image | from image | 3.12 |

- The 0.10.4 to 0.10.5.dev pairing emits a "different base versions"
  ImportWarning. Compilation and inference are fine. Record both actual versions
  in the result.
- rebel-compiler ships wheels for Python < 3.13. An example upper pin:
  `rebel-compiler>=0.10.5.dev0,<0.12`.
- Some container base images carry only the driver tools and expect you to
  install the Python SDK yourself. Image names and registries differ per
  environment, so record them as `<RBLN_IMAGE>`.
- Results reproduced within 1% on p50 across KMD 3.2.0-3.2.2 and kernel
  6.14-6.17.

## Hardware reference (from official specs)

| | ATOM (RBLN-CA22) | ATOM-Max (RBLN-CA25) |
|---|---|---|
| Card | 1 logical device | 4 logical devices |
| Memory per logical device | 16 GB | 16 GB (15.7 GiB observed) |
| Bandwidth per logical device | 256 GB/s | 256 GB/s (card 1024 GB/s divided by 4) |
| fp16 dense | 32 TFLOPS | 32 TFLOPS per device (card 128) |

Dividing whole-card figures by four is an arithmetic envelope, not a
vendor-attested TP=1 performance claim. Do not conflate the two SKUs.
