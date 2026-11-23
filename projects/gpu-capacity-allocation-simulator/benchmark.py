"""Repeatable synthetic GPU-bin-packing benchmark (100 seeded workloads).

This models offline batch planning, not an online production scheduler.
All power units and pod affinity are abstractions rather than hardware telemetry.
"""
import random
from statistics import mean
from planner import Planner, Reservation, sample_racks

SEEDS = 100
SIZES = (8, 8, 16, 16, 24, 32, 40)
MAX_DEMAND_GPUS = 365


def workload(seed):
    rng = random.Random(seed)
    jobs = []
    demand = 0
    while demand < MAX_DEMAND_GPUS - 8 and len(jobs) < 40:
        gpus = rng.choice(SIZES)
        if demand + gpus > MAX_DEMAND_GPUS:
            break
        affinity = rng.choice(('pod-east', 'pod-west')) if rng.random() < 0.25 else None
        jobs.append(Reservation(f'job-{len(jobs):03d}', gpus, affinity))
        demand += gpus
    return jobs


def evaluate(seeds=SEEDS):
    measurements = {'first_fit': [], 'best_fit': []}
    for seed in range(seeds):
        jobs = workload(seed)
        for heuristic in measurements:
            planner = Planner(sample_racks())
            planner.schedule(jobs, heuristic=heuristic)
            metrics = planner.metrics()
            metrics['unplaced_gpus'] = sum(j.gpus for j in jobs if j.id not in planner.placements)
            measurements[heuristic].append(metrics)
    keys = ('utilization_pct', 'free_segments', 'largest_contiguous_free_gpus',
            'fragmented_free_pct', 'placed_reservations', 'unplaced_gpus')
    return {name: {k: round(mean(r[k] for r in rows), 2) for k in keys}
            for name, rows in measurements.items()}


if __name__ == '__main__':
    print('Synthetic 384-GPU fleet; 100 seeded workloads, offline planning')
    for policy, metrics in evaluate().items():
        print(policy, metrics)