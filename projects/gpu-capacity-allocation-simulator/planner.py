"""A synthetic, topology-aware GPU reservation packing demonstration.

This is an educational placement simulator, NOT a production GPU scheduler.
Rack-level contiguity is an abstraction; real network locality must model the
actual GPU interconnect, bandwidth and failure domains.
"""
from dataclasses import dataclass, field
from typing import Optional

GPUS_PER_NODE = 8

@dataclass(frozen=True)
class Reservation:
    id: str
    gpus: int
    pod_affinity: Optional[str] = None
    expires_at: Optional[int] = None  # Simulated time step

    def __post_init__(self):
        if self.gpus <= 0 or self.gpus % GPUS_PER_NODE:
            raise ValueError('Reservations must be positive multiples of 8 GPUs')

    @property
    def nodes(self):
        return self.gpus // GPUS_PER_NODE

@dataclass
class Rack:
    id: str
    pod: str
    slots: int = 8
    power_limit: int = 8  # Synthetic units; not real kW
    power_per_node: int = 1
    occupancy: list = field(default_factory=list)

    def __post_init__(self):
        if self.slots < 1 or self.power_limit < 0 or self.power_per_node < 1:
            raise ValueError('Invalid rack capacity/power')
        if not self.occupancy:
            self.occupancy = [None] * self.slots
        if len(self.occupancy) != self.slots:
            raise ValueError('occupancy must match rack slots')

    def candidate_starts(self, size):
        active = sum(x is not None for x in self.occupancy)
        if (active + size) * self.power_per_node > self.power_limit:
            return []
        return [i for i in range(self.slots-size+1)
                if all(x is None for x in self.occupancy[i:i+size])]

    def free_runs(self):
        lengths, current = [], 0
        for x in self.occupancy + ['SENTINEL']:
            if x is None:
                current += 1
            elif current:
                lengths.append(current)
                current = 0
        return lengths

@dataclass(frozen=True)
class Placement:
    reservation: str
    pod: str
    rack: str
    start_node: int
    nodes: int

class Planner:
    def __init__(self, racks):
        self.racks = [Rack(r.id, r.pod, r.slots, r.power_limit, r.power_per_node)
                      for r in racks]
        self.placements = {}
        self.reservations = {}

    def place(self, request: Reservation, heuristic='best_fit'):
        if request.id in self.reservations:
            raise ValueError('Duplicate reservation id')
        candidates = []
        for rack in self.racks:
            if request.pod_affinity and request.pod_affinity != rack.pod:
                continue
            for start in rack.candidate_starts(request.nodes):
                if heuristic == 'best_fit':
                    # Prefer fewer wasted free slots, fewer free gaps, and a tightly
                    # consolidated rack. Deterministic tie-breaker for reproducibility.
                    test = rack.occupancy.copy()
                    test[start:start+request.nodes] = [request.id] * request.nodes
                    free_runs, n = [], 0
                    for value in test + ['END']:
                        if value is None:
                            n += 1
                        elif n:
                            free_runs.append(n); n = 0
                    score = (sum(free_runs), len(free_runs), -max(free_runs,default=0), rack.id, start)
                elif heuristic == 'first_fit':
                    score = (rack.id, start)
                else:
                    raise ValueError('Unknown heuristic')
                candidates.append((score, rack, start))
        if not candidates:
            return None
        _,rack,start = min(candidates, key=lambda x:x[0])
        rack.occupancy[start:start+request.nodes] = [request.id] * request.nodes
        p = Placement(request.id, rack.pod, rack.id, start, request.nodes)
        self.placements[request.id] = p
        self.reservations[request.id] = request
        return p

    def schedule(self, requests, heuristic='best_fit'):
        if heuristic == 'best_fit':
            # Largest jobs first reduces failure caused by packing small jobs early.
            requests = sorted(requests, key=lambda r: (-r.nodes, r.id))
        return {r.id:self.place(r,heuristic) for r in requests}

    def expire(self, now):
        released = []
        for request_id, request in list(self.reservations.items()):
            if request.expires_at is not None and request.expires_at <= now:
                for rack in self.racks:
                    rack.occupancy = [None if x == request_id else x for x in rack.occupancy]
                self.reservations.pop(request_id)
                self.placements.pop(request_id)
                released.append(request_id)
        return released

    def metrics(self):
        total_nodes = sum(r.slots for r in self.racks)
        used_nodes = sum(sum(x is not None for x in r.occupancy) for r in self.racks)
        free_runs = [length for r in self.racks for length in r.free_runs()]
        total_free = (total_nodes - used_nodes) * GPUS_PER_NODE
        largest_free = max(free_runs,default=0)*GPUS_PER_NODE
        fragmented_free_pct = (round(100 * (1-largest_free/total_free),1)
                               if total_free else 0.0)
        return {
            'total_gpus':total_nodes * GPUS_PER_NODE,
            'allocated_gpus':used_nodes * GPUS_PER_NODE,
            'utilization_pct':round(100*used_nodes/total_nodes,1),
            'free_segments':len(free_runs),
            'largest_contiguous_free_gpus':largest_free,
            'fragmented_free_pct':fragmented_free_pct,
            'placed_reservations':len(self.placements)
        }


def sample_racks():
    return [Rack(f'{pod}-rack-{i}',pod,slots=8,power_limit=8)
            for pod in ('pod-east','pod-west') for i in range(1,4)]


def sample_reservations():
    # Synthetic demand: small jobs appear first, as they might arrive in real time.
    sizes=[8]*9+[16]*6+[24]*4+[32]*3
    return [Reservation(f'client-{i:02d}',size,expires_at=(3 if i%5==0 else None))
            for i,size in enumerate(sizes,1)]