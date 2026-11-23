from planner import Planner, sample_racks, sample_reservations


def run():
    jobs = sample_reservations()
    print('GPU Cluster Capacity Allocation - synthetic demonstration')
    for name,algorithm in [('Arrival-order first fit','first_fit'),
                           ('Largest-first best fit','best_fit')]:
        engine = Planner(sample_racks())
        output=engine.schedule(jobs,algorithm)
        refused=[k for k,v in output.items() if v is None]
        print(f'\n{name}:')
        print('  ',engine.metrics())
        print('  Unplaced:',refused or 'none')
        if algorithm=='best_fit':
            released=engine.expire(3)
            print('  Released at t=3:',released)
            print('  Capacity after expiry:',engine.metrics())

if __name__=='__main__':
    run()