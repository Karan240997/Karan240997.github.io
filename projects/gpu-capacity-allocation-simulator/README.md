# GPU Cluster Capacity Allocation Simulator

A small **personal learning project** written in standard-library Python to demonstrate transferable allocation concepts for GPU clusters. It is a synthetic simulation and **does not operate GPU hardware or production schedulers**.

## What it models

- Reservations requested in whole **8-GPU node** increments.
- Placement within one **rack and InfiniBand pod** to approximate locality/contiguity constraints. Real network topology is more complex; adjacency of numbered nodes does not imply NVLink connectivity.
- Optional pod affinity for customer requests and configurable rack power budgets in synthetic units.
- Compare arrival-order `first_fit` with a largest-request-first, best-fit-inspired **bin-packing heuristic**. The heuristic prefers compact rack-local placements; it is not a solver or globally optimal policy.
- Temporary holds with expiry to release capacity after the expected demand event.
- Observable allocation metrics: utilization, largest contiguous rack-local free block, free-block segmentation, **fragmentation** and unplaced GPU demand.

**Limitations:** This is not a mathematical optimum and does not model NVLink domains, real InfiniBand route/topology, NIC rails, inter-rack placement, cooling, failures, capacity reservations by date/time, or live customer demand. Rack power units are illustrative, not actual electrical measurements. For a production workload, integrate validated placement policy, power/cooling telemetry, reliability constraints, and rollback/reconciliation.

## Try it

```bash
python demo.py
python benchmark.py
python -m unittest discover -s tests -v
```

There are no third-party dependencies. Python 3.10+ is sufficient.

## Architecture

- `planner.py`: data model, first-fit/best-fit allocation, expiry, and metrics.
- `demo.py`: deterministic synthetic scenario comparing policies.
- `benchmark.py`: 100 seeded synthetic workloads for reproducible averages.
- `tests/test_planner.py`: six unit tests covering overlap, power budgets, locality, validity, expiry, and fragmentation metrics.

## Reproducible results (100 synthetic scenarios)

On a fleet of six racks, each with eight **8-GPU nodes** (384 GPUs total),
`benchmark.py` generates 100 seeded workloads with variable request sizes and
25% probability of synthetic pod affinity. Workloads contain roughly 352 GPUs
of requested capacity on average. This is a batch-planning experiment, not an
online arrival-time benchmark.

| Mean metric over 100 scenarios | Arrival-order first-fit | Largest-first best-fit |
|---|---:|---:|
| GPU utilization | 86.74% | 88.14% |
| Fragmented free GPU capacity | 26.14% | 2.97% |
| Largest contiguous rack-local free block | 36.40 GPUs | 43.44 GPUs |
| Number of free rack-local segments | 2.07 | 1.14 |
| Unplaced requested GPUs | 18.80 | 13.44 |

**Definition:** `fragmented_free_pct = 100 × (1 − largest_contiguous_free_gpus / all_free_gpus)`; 0% if there is no free capacity. Each contiguous block is constrained to one rack. This definition is an intentionally simple indicator of free-space fragmentation, not a full topology, fabric, or customer-placement efficiency measure. The policies can allocate different total GPUs, so interpret fragmentation alongside utilization and unplaced demand.

The original fixed demonstration also produces **22/22** placed requests at **93.8%** utilization and one free segment for largest-first best-fit, versus **21/22**, **85.4%**, and four free segments for arrival-order first-fit. These fixed-case numbers are not the averages above.

## Next improvements

1. Add time-windowed reservations with conflict detection and fair customer priority.
2. Represent actual NVLink and InfiniBand network domains rather than synthetic rack adjacency.
3. Compare a CP-SAT/OR-Tools optimization model with the heuristic on reproducible workloads.
4. Add stranded-fragment metrics across different minimum reservation sizes, plus cost/power tradeoffs.
5. Add forecasted event demand and simulate expiry, reclaim, and reassignment across time.