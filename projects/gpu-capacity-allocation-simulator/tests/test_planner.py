import unittest
from planner import Planner, Rack, Reservation, sample_racks, sample_reservations

class TestPlanner(unittest.TestCase):
    def test_reservation_gpu_counts(self):
        for count in (0,1,10,-8):
            with self.assertRaises(ValueError): Reservation('bad',count)

    def test_contiguity_and_pod_affinity(self):
        p=Planner([Rack('rack-a','pod-a',slots=4),Rack('rack-b','pod-b',slots=4)])
        placed=p.place(Reservation('j',24,pod_affinity='pod-b'))
        self.assertEqual((placed.pod,placed.nodes),('pod-b',3))
        occupied=[i for i,x in enumerate(p.racks[1].occupancy) if x=='j']
        self.assertEqual(occupied, list(range(placed.start_node,placed.start_node+3)))

    def test_power_guardrail(self):
        p=Planner([Rack('r','pod',slots=8,power_limit=3,power_per_node=1)])
        self.assertIsNotNone(p.place(Reservation('small',24)))
        self.assertIsNone(p.place(Reservation('other',8)))

    def test_expire_reclaims_capacity(self):
        p=Planner([Rack('r','p',slots=4)])
        p.place(Reservation('hold',32,expires_at=5))
        self.assertEqual(p.metrics()['utilization_pct'],100.0)
        self.assertEqual(p.expire(4),[])
        self.assertEqual(p.expire(5),['hold'])
        self.assertEqual(p.metrics()['utilization_pct'],0.0)

    def test_fragmentation_metric(self):
        p=Planner([Rack('rack-1','pod',slots=8)])
        p.place(Reservation('a',16))
        p.place(Reservation('b',16))
        p.place(Reservation('c',16))
        p.expire(0)
        # One contiguous 16-GPU free run, so no fragmented free capacity.
        self.assertEqual(p.metrics()['fragmented_free_pct'],0.0)
        q=Planner([Rack('rack-1','pod',slots=8)])
        q.place(Reservation('x',8))
        q.place(Reservation('y',8,expires_at=1))
        q.place(Reservation('z',8))
        q.expire(1)
        self.assertEqual(q.metrics()['free_segments'],2)
        self.assertEqual(q.metrics()['fragmented_free_pct'],16.7)

    def test_no_overcommitment_or_overlap(self):
        p=Planner(sample_racks())
        p.schedule(sample_reservations())
        seen=set()
        for placement in p.placements.values():
            for j in range(placement.start_node,placement.start_node+placement.nodes):
                key=(placement.rack,j)
                self.assertNotIn(key,seen)
                seen.add(key)
        self.assertLessEqual(p.metrics()['allocated_gpus'],p.metrics()['total_gpus'])

if __name__=='__main__': unittest.main()