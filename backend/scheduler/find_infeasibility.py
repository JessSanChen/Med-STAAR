"""
Diagnose which constraints are causing infeasibility
"""
from data_loader import DataLoader
from scheduler import PhysicianScheduler
import pulp

print("="*80)
print("INFEASIBILITY DIAGNOSIS")
print("="*80)

# Load data
loader = DataLoader(data_dir='../data')
data = loader.load_all_data(num_days=7)

print(f"\nLoaded {len(data.providers)} providers, {len(data.shifts)} shifts, {len(data.days)} days")
print(f"Coverage required: {len(data.coverage_required)} facility-day slots")

# Test 1: Can we fill coverage with NO other constraints?
print("\n" + "-"*80)
print("TEST 1: Coverage only (no provider constraints)")
print("-"*80)

scheduler = PhysicianScheduler(data, time_limit_seconds=60)

# Only add coverage constraints
for shift_id, shift in data.shifts.items():
    for day in data.days:
        providers_assigned = pulp.lpSum([
            scheduler.x[provider_name, shift_id, day]
            for provider_name in data.providers.keys()
        ])

        if (shift_id, day) in data.coverage_required:
            scheduler.problem += (
                providers_assigned >= 1,
                f"cov_{shift_id}_{day}".replace(" ", "_").replace(",", "").replace("-", "_")
            )

# Simple objective: minimize total assignments
scheduler.problem += pulp.lpSum([
    scheduler.x[prov, shift, day]
    for prov in data.providers.keys()
    for shift in data.shifts.keys()
    for day in data.days
]), "minimize_assignments"

print("Solving...")
scheduler.problem.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=60))
status1 = pulp.LpStatus[scheduler.problem.status]
print(f"Result: {status1}")

if status1 == "Optimal":
    total_assignments = sum(1 for var in scheduler.problem.variables()
                          if var.name.startswith('x_') and var.varValue and var.varValue > 0.5)
    print(f"  Total assignments needed: {total_assignments}")
    print("  ✓ Coverage is achievable without provider constraints")
else:
    print("  ❌ Even basic coverage is infeasible!")
    print("  This means some shifts have NO eligible providers")

# Test 2: Add credentialing
print("\n" + "-"*80)
print("TEST 2: Coverage + Credentialing")
print("-"*80)

scheduler2 = PhysicianScheduler(data, time_limit_seconds=60)

# Add coverage
for shift_id, shift in data.shifts.items():
    for day in data.days:
        providers_assigned = pulp.lpSum([
            scheduler2.x[provider_name, shift_id, day]
            for provider_name in data.providers.keys()
        ])

        if (shift_id, day) in data.coverage_required:
            scheduler2.problem += (providers_assigned >= 1, f"cov2_{shift_id}_{day}".replace(" ", "_").replace(",", "").replace("-", "_"))

# Add credentialing
scheduler2._add_credentialing_constraints()

scheduler2.problem += pulp.lpSum([
    scheduler2.x[prov, shift, day]
    for prov in data.providers.keys()
    for shift in data.shifts.keys()
    for day in data.days
]), "minimize_assignments2"

print("Solving...")
scheduler2.problem.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=60))
status2 = pulp.LpStatus[scheduler2.problem.status]
print(f"Result: {status2}")

if status2 != "Optimal":
    print("  ❌ Adding credentialing makes it infeasible!")
    print("  Some required shifts have NO credentialed providers")

# Test 3: Add shift count constraints
if status2 == "Optimal":
    print("\n" + "-"*80)
    print("TEST 3: Coverage + Credentialing + Shift Counts")
    print("-"*80)

    scheduler3 = PhysicianScheduler(data, time_limit_seconds=60)

    # Coverage
    for shift_id, shift in data.shifts.items():
        for day in data.days:
            providers_assigned = pulp.lpSum([
                scheduler3.x[provider_name, shift_id, day]
                for provider_name in data.providers.keys()
            ])
            if (shift_id, day) in data.coverage_required:
                scheduler3.problem += (providers_assigned >= 1, f"cov3_{shift_id}_{day}".replace(" ", "_").replace(",", "").replace("-", "_"))

    scheduler3._add_credentialing_constraints()
    scheduler3._link_shift_type_indicators()
    scheduler3._add_shift_count_constraints()

    scheduler3.problem += pulp.lpSum([
        scheduler3.x[prov, shift, day]
        for prov in data.providers.keys()
        for shift in data.shifts.keys()
        for day in data.days
    ]), "minimize_assignments3"

    print("Solving...")
    scheduler3.problem.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=60))
    status3 = pulp.LpStatus[scheduler3.problem.status]
    print(f"Result: {status3}")

    if status3 != "Optimal":
        print("  ❌ Adding shift count constraints makes it infeasible!")
        print("  Provider capacity vs coverage requirements mismatch")

# Test 4: Add availability
if status3 == "Optimal":
    print("\n" + "-"*80)
    print("TEST 4: + Availability Constraints")
    print("-"*80)

    scheduler4 = PhysicianScheduler(data, time_limit_seconds=60)

    for shift_id, shift in data.shifts.items():
        for day in data.days:
            providers_assigned = pulp.lpSum([
                scheduler4.x[provider_name, shift_id, day]
                for provider_name in data.providers.keys()
            ])
            if (shift_id, day) in data.coverage_required:
                scheduler4.problem += (providers_assigned >= 1, f"cov4_{shift_id}_{day}".replace(" ", "_").replace(",", "").replace("-", "_"))

    scheduler4._add_credentialing_constraints()
    scheduler4._link_shift_type_indicators()
    scheduler4._add_shift_count_constraints()
    scheduler4._add_availability_constraints()

    scheduler4.problem += pulp.lpSum([
        scheduler4.x[prov, shift, day]
        for prov in data.providers.keys()
        for shift in data.shifts.keys()
        for day in data.days
    ]), "minimize_assignments4"

    print("Solving...")
    scheduler4.problem.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=60))
    status4 = pulp.LpStatus[scheduler4.problem.status]
    print(f"Result: {status4}")

    if status4 != "Optimal":
        print("  ❌ Adding availability constraints makes it infeasible!")
    else:
        # Test 5: Add weekend constraints
        print("\n" + "-"*80)
        print("TEST 5: + Weekend Constraints")
        print("-"*80)

        scheduler5 = PhysicianScheduler(data, time_limit_seconds=60)

        for shift_id, shift in data.shifts.items():
            for day in data.days:
                providers_assigned = pulp.lpSum([
                    scheduler5.x[provider_name, shift_id, day]
                    for provider_name in data.providers.keys()
                ])
                if (shift_id, day) in data.coverage_required:
                    scheduler5.problem += (providers_assigned >= 1, f"cov5_{shift_id}_{day}".replace(" ", "_").replace(",", "").replace("-", "_"))

        scheduler5._add_credentialing_constraints()
        scheduler5._link_shift_type_indicators()
        scheduler5._add_shift_count_constraints()
        scheduler5._add_availability_constraints()
        scheduler5._add_weekend_shift_constraints()

        scheduler5.problem += pulp.lpSum([
            scheduler5.x[prov, shift, day]
            for prov in data.providers.keys()
            for shift in data.shifts.keys()
            for day in data.days
        ]), "minimize_assignments5"

        print("Solving...")
        scheduler5.problem.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=60))
        status5 = pulp.LpStatus[scheduler5.problem.status]
        print(f"Result: {status5}")

        if status5 != "Optimal":
            print("  ❌ Adding weekend constraints makes it infeasible!")
        else:
            # Test 6: Add PM constraints
            print("\n" + "-"*80)
            print("TEST 6: + PM Shift Constraints")
            print("-"*80)

            scheduler6 = PhysicianScheduler(data, time_limit_seconds=60)

            for shift_id, shift in data.shifts.items():
                for day in data.days:
                    providers_assigned = pulp.lpSum([
                        scheduler6.x[provider_name, shift_id, day]
                        for provider_name in data.providers.keys()
                    ])
                    if (shift_id, day) in data.coverage_required:
                        scheduler6.problem += (providers_assigned >= 1, f"cov6_{shift_id}_{day}".replace(" ", "_").replace(",", "").replace("-", "_"))

            scheduler6._add_credentialing_constraints()
            scheduler6._link_shift_type_indicators()
            scheduler6._add_shift_count_constraints()
            scheduler6._add_availability_constraints()
            scheduler6._add_weekend_shift_constraints()
            scheduler6._add_pm_shift_constraints()

            scheduler6.problem += pulp.lpSum([
                scheduler6.x[prov, shift, day]
                for prov in data.providers.keys()
                for shift in data.shifts.keys()
                for day in data.days
            ]), "minimize_assignments6"

            print("Solving...")
            scheduler6.problem.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=60))
            status6 = pulp.LpStatus[scheduler6.problem.status]
            print(f"Result: {status6}")

            if status6 != "Optimal":
                print("  ❌ Adding PM shift constraints makes it infeasible!")
            else:
                # Test 7: Add daily hour constraints
                print("\n" + "-"*80)
                print("TEST 7: + Daily Hour Constraints")
                print("-"*80)

                scheduler7 = PhysicianScheduler(data, time_limit_seconds=60)

                for shift_id, shift in data.shifts.items():
                    for day in data.days:
                        providers_assigned = pulp.lpSum([
                            scheduler7.x[provider_name, shift_id, day]
                            for provider_name in data.providers.keys()
                        ])
                        if (shift_id, day) in data.coverage_required:
                            scheduler7.problem += (providers_assigned >= 1, f"cov7_{shift_id}_{day}".replace(" ", "_").replace(",", "").replace("-", "_"))

                scheduler7._add_credentialing_constraints()
                scheduler7._link_shift_type_indicators()
                scheduler7._add_shift_count_constraints()
                scheduler7._add_availability_constraints()
                scheduler7._add_weekend_shift_constraints()
                scheduler7._add_pm_shift_constraints()
                scheduler7._add_daily_hour_constraints()

                scheduler7.problem += pulp.lpSum([
                    scheduler7.x[prov, shift, day]
                    for prov in data.providers.keys()
                    for shift in data.shifts.keys()
                    for day in data.days
                ]), "minimize_assignments7"

                print("Solving...")
                scheduler7.problem.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=60))
                status7 = pulp.LpStatus[scheduler7.problem.status]
                print(f"Result: {status7}")

                if status7 != "Optimal":
                    print("  ❌ Adding daily hour constraints makes it infeasible!")
                else:
                    print("  ✓ All constraints up to daily hours are feasible!")
                    print("  The issue must be in consecutive shift constraints")

print("\n" + "="*80)
