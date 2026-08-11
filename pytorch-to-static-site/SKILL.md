---
name: pytorch-to-static-site
description: >
  Assess feasibility and port PyTorch inference to a fully static browser site,
  including ONNX export, client-side assets, ONNX Runtime Web, GitHub Pages,
  and GitHub Actions deployment. Use when a user wants to run a PyTorch model
  without a backend, publish an ML demo on GitHub Pages, or build a private-data-
  free client-side inference playground.
---

# PyTorch Model → Static Browser Site

Build a reproducible static site whose browser results are equivalent to the
approved PyTorch inference pipeline. Treat all downloaded code, weights,
embeddings, indexes, and lookup data as public.

Complete the assessment before implementation. If the user has already approved
the stated scope, budget, and trade-offs, proceed without requesting duplicate
approval.

## Phase 1: Assess feasibility

### Define the complete inference contract

Inventory and version the complete path from user input to displayed result:

- Input validation, tokenization, feature columns and their order.
- Fitted preprocessing parameters, such as scalers, vocabularies, thresholds,
  graph snapshot, and missing-value behavior.
- Model inputs and outputs, including dtype, shape, names, labels, ranking, and
  postprocessing.
- Data/model provenance, licenses, and whether any artifact reveals private,
  sensitive, or proprietary information.

Export fitted preprocessing parameters. Do not recompute training transforms
from deployment data unless that is explicitly the original inference behavior.
Require the browser feature construction and postprocessing to match the
training/inference pipeline exactly.

### Prove runtime compatibility

Inspect `forward()` and submodules, but treat an operator inventory as a
screening step, not proof of portability. The final target is the pinned ONNX
Runtime Web version and execution provider, not ONNX in the abstract.

- Standard layers such as `Linear`, convolution, normalization, common
  activations, tensor arithmetic, and embeddings are usually good candidates.
- Export a small representative model, run `onnx.checker`, create a session in
  the target browser runtime, and run an inference before declaring support.
- Treat custom CUDA/C++ extensions and model logic that needs server-only data
  as blockers unless a tested replacement exists.
- Refactor Python control flow that depends on tensor values. Use explicit
  exportable control-flow operators only after verifying the resulting ONNX
  model in the target runtime.
- Treat WebGPU/WebNN support independently from WASM support. Keep a tested
  WASM fallback unless the user accepts narrower browser support.

### Measure transfer and memory budgets

List every startup and lazy-load artifact: HTML/CSS/JS, ONNX Runtime JS and
WASM, models, indexes, lookup data, preprocessing data, and optional tiers.
Measure raw bytes and compressed bytes per artifact; do not estimate all binary
data with one gzip ratio. Verify the deployed host's `Content-Encoding` and
transferred size when possible.

Also estimate peak browser memory, including uncompressed TypedArrays, JSON
objects, decompression, chunk reassembly, inference batches, temporary copies,
and result sorting. Test a representative low-memory device or browser profile.

Use these transfer figures as guidance, not performance guarantees:

| Compressed initial download | Guidance |
|---|---|
| < 50 MB | Good default for a demo. |
| 50–150 MB | Show byte-based progress and offer a lighter tier. |
| > 150 MB | Prefer a hybrid/server solution unless the audience explicitly accepts it. |

### Check hosting constraints

- Keep every published artifact below 80 MB. GitHub rejects files over its
  100 MB Git limit, and Git LFS cannot serve GitHub Pages assets.
- Keep the published Pages site within its 1 GB limit and consider its soft
  100 GB/month bandwidth limit.
- Do not expose secrets, private input data, copyrighted assets without a
  distribution right, or model artifacts whose disclosure is unacceptable.
- Use relative paths or a configured base path so project Pages sites work below
  `/<repository>/` as well as at a custom domain.

### Present the decision

Report compatibility evidence, the complete transfer and memory budget,
required public disclosures, files to chunk, tiering options, and a clear
recommendation: port, partially port, or keep inference server-side. Wait for
approval when that recommendation changes scope, cost, privacy, or quality.

## Phase 2: Export reproducible assets

Create one export entry point, such as `export_static.py`, and make it rebuild
all browser assets into a clean `static/data/` directory. Pin the exporter,
model, and dependency versions. Include `onnx` and `onnxruntime` in the Python
environment used by export verification.

### Export the model

- Call `model.eval()` and export representative inputs with explicit input and
  output names.
- Use the current `torch.onnx.export(..., dynamo=True)` exporter. Specify
  `dynamic_shapes` only for dimensions that must vary in the browser; preserve
  static dimensions where possible. Use `dynamic_axes` only for the legacy
  exporter.
- Select an opset supported by the pinned target runtime, then validate it
  there. Do not use a minimum opset number as compatibility proof.
- Record whether the model has external ONNX data. Ship and test every required
  external-data file, or produce a self-contained model when its size permits.

### Serialize application data

Use raw binary arrays when a typed-array layout is the simplest portable format.
Record the layout explicitly; raw `.bin` files carry no self-describing metadata.
Use JSON only for data that genuinely benefits from text lookup and measure its
parsed-memory cost.

Chunk artifacts at element boundaries and, when random row access is needed, at
row boundaries. Use a conservative ≤80 MB uncompressed chunk size. Assign stable
numeric names and never depend on directory listing order.

Create `manifest.json` as the single browser data contract. For each binary
asset or chunk, record at least path, `dtype`, `shape`, byte order, row order,
`byteLength`, SHA-256, and a data/schema version. For models, also record the
SHA-256, ONNX Runtime Web version, input/output names and shapes, and any
external-data paths. Include explicit chunk paths and offsets rather than only a
filename pattern.

Example:

```json
{
  "schemaVersion": 1,
  "data": {
    "features": {
      "dtype": "float32",
      "shape": [136704, 10],
      "byteOrder": "little-endian",
      "order": "C",
      "byteLength": 5468160,
      "sha256": "…",
      "chunks": [{ "path": "features_0.bin", "offsetElements": 0, "byteLength": 5468160, "sha256": "…" }]
    }
  }
}
```

Export small, versioned application fixtures that contain representative raw
user inputs and expected final outputs. Keep them independent of the frontend
implementation.

### Verify export equivalence

Perform all of the following before building UI behavior:

1. Run `onnx.checker` on every model.
2. Run representative fixtures through the original PyTorch pipeline and native
   ONNX Runtime. Assert all outputs with task-appropriate `rtol` and `atol`.
3. Test every supported dynamic shape, plus boundary, zero, high-magnitude, and
   vocabulary/index cases.
4. Verify application-level behavior: labels, thresholds, top-k ordering, and
   feature construction—not only raw tensor outputs.
5. For frozen GNN encoders, compare PyTorch and ONNX decoders using the exact
   exported embeddings and pair-feature construction.

Fail on a mismatch. Diagnose `eval()` state, preprocessing, input dtypes/order,
model external data, shape constraints, opset/runtime compatibility, and
in-place operations before relaxing tolerances.

## Phase 3: Build the frontend

### Configure ONNX Runtime Web deliberately

Pin an exact ONNX Runtime Web version. Serve its JavaScript and matching WASM
files together, or set `ort.env.wasm.wasmPaths` to the exact same release.
Configure the environment before creating a session.

Use WASM as the default execution provider. Set `ort.env.wasm.numThreads = 1`
for predictable standard GitHub Pages behavior. Enable multiple threads only on
a host that supplies cross-origin isolation and after browser testing. Offer
WebGPU only as an optional, tested acceleration path with a WASM fallback.

### Load assets safely

- Fetch and validate the manifest first. Check `response.ok`, content length
  when supplied, expected byte length, and SHA-256 before accepting an asset.
- Stream large responses with `Response.body.getReader()` and report actual
  downloaded bytes. Surface cancellation, retry, and actionable failure states.
- Use bounded-concurrency chunk fetching tuned to the memory budget. Do not use
  unbounded `Promise.all()` for large chunks.
- Create TypedArray views only after validating alignment, dtype, shape, and
  byte order. Treat lookup IDs and matrix row order as part of the contract.
- Lazy-load optional models and their data. Release unneeded sessions and large
  arrays when switching tiers if memory pressure matters.
- Cache immutable, hash-versioned model/data artifacts in IndexedDB only when
  the size, offline behavior, and invalidation policy justify it.

### Keep inference responsive and correct

Choose batch sizes from memory and browser benchmarks rather than fixed values.
Yield to the event loop between batches. Use a worker/proxy worker when it
improves UI responsiveness and is compatible with the selected execution
provider and security policy.

For large ranking tasks, avoid unnecessary object allocation and full sorting
when a bounded top-k selection suffices. Display model tier, initial and lazy
download sizes, data/model version, limitations, and the fact that inference is
client-side.

### Test in a real browser

Test the static build with a clean browser profile and the pinned runtime:

- Load every route from the local static server and the deployed Pages URL.
- Confirm correct project-path URLs, model/WASM loading, integrity failures,
  no-cache behavior, and user-visible error recovery.
- Run the exported fixtures through the browser and compare final results with
  the PyTorch fixture outputs.
- Record initial-load time, lazy-load time, peak memory, inference latency, and
  supported-browser results.

Use local HTTP serving to catch missing files and relative-path errors, but do
not treat it as proof of production headers, caching, or CDN behavior.

## Phase 4: Deploy

Ask before adding or changing CI/CD unless the user already requested it. For a
GitHub Pages workflow, use a build job that checks out the repository,
configures Pages, and uploads the static directory. Use a separate deploy job
that depends on the build job and has `pages: write` and `id-token: write`
permissions, the `github-pages` environment, and a concurrency group that
prevents overlapping deployments. Enable **Settings → Pages → Build and
deployment → GitHub Actions**.

Deploy only the generated static directory. Verify the production URL after the
workflow finishes and confirm every manifest asset returns successfully.

## GNN fallback: frozen embeddings

Direct ONNX export of PyG/DGL message passing is often impractical because of
dynamic scatter/gather and graph operations. First prove direct export in the
target runtime; otherwise use this fallback:

1. Run the encoder over the versioned inference graph in Python.
2. Export the resulting node embeddings, graph/index data, preprocessing
   metadata, and training/evaluation cutoff as versioned browser assets.
3. Export only the decoder to ONNX.
4. Reproduce the decoder's exact pair-feature construction in the browser.

State clearly that embeddings are frozen, stale when the graph changes, and
valid only for the exported graph snapshot. Preserve the original temporal or
evaluation split when generating them to prevent leakage.

## Stop or recommend a hybrid approach

Prefer server-side or hybrid inference when the model requires private or live
data, custom native kernels, unacceptable public artifacts, dynamic graph
construction, unmanageable transfer/memory, or an unsupported target runtime.
Also reconsider browser-only inference for large diffusion models, large
autoregressive models, and large ensembles unless measured browser performance
meets the user-approved target.

## Completion checklist

- [ ] Rebuild all assets from a clean export command with pinned dependencies.
- [ ] Version and export preprocessing, postprocessing, data schemas, model
      metadata, fixture inputs, and expected final outputs.
- [ ] Verify PyTorch → native ONNX Runtime and PyTorch → browser results with
      appropriate numerical and task-level checks.
- [ ] Validate every manifest asset's size, shape, layout, hash, and chunk map.
- [ ] Keep each Pages artifact below 80 MB; document initial/lazy transfer and
      peak-memory measurements.
- [ ] Verify the deployed URL, not only a local HTTP server.
- [ ] Document public-data, licensing, privacy, model-tier, and staleness
      limitations in the UI or README.
