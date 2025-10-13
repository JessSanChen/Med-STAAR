"""
Verify that the test schedule follows all constraints
"""
import pandas as pd
from data_loader import DataLoader
from collections import defaultdict

print("="*80)
print("VERIFYING TEST SCHEDULE AGAINST CONSTRAINTS")
print("="*80)

# Load data
loader = DataLoader(data_dir='test_data')
data = loader.load_all_data(num_days=7, start_date=pd.Timestamp('2025-01-06'))

# Load generated schedule
schedule_df = pd.read_excel('output/test_schedule.xlsx')

print("\n" + "="*80)
print("SCHEDULE OVERVIEW")
print("="*80)
print(schedule_df.to_string())

# Parse schedule into provider assignments
provider_assignments = defaultdict(list)  # provider -> list of (day, shift_id)
shift_coverage = defaultdict(list)  # (day, shift_id) -> list of providers

shift_columns = [col for col in schedule_df.columns if col.startswith('MD') or col.startswith('PM')]

for day_idx, row in schedule_df.iterrows():
    for shift_id in shift_columns:
        assignment = row[shift_id]
        if pd.notna(assignment) and str(assignment).strip():
            # Parse provider names (may be comma-separated)
            providers = [p.strip() for p in str(assignment).split(',')]
            for provider_name in providers:
                provider_assignments[provider_name].append((day_idx, shift_id))
                shift_coverage[(day_idx, shift_id)].append(provider_name)

# Helper functions
def get_shift_type(shift_id):
    if shift_id.startswith('MD1'):
        return 'MD1'
    elif shift_id.startswith('MD2'):
        return 'MD2'
    elif shift_id.startswith('PM'):
        return 'PM'
    return None

def is_weekend(day_idx):
    return day_idx in data.weekends

# Verification counters
passed = 0
failed = 0
warnings = 0

print("\n" + "="*80)
print("P1 CONSTRAINT VERIFICATION (HARD CONSTRAINTS)")
print("="*80)

# 1. Credentialing Constraints
print("\n1. CREDENTIALING CONSTRAINTS")
print("-"*80)
for provider_name, assignments in provider_assignments.items():
    provider = data.providers[provider_name]

    for day_idx, shift_id in assignments:
        shift = data.shifts[shift_id]

        # Check if provider is credentialed for ALL facilities in this shift
        is_credentialed = all(
            facility in provider.credentialed_facilities
            for facility in shift.facilities
        )

        if not is_credentialed:
            print(f"  ❌ FAILED: {provider_name} assigned to {shift_id} but not credentialed")
            print(f"     Shift facilities: {shift.facilities}")
            print(f"     Provider credentials: {list(provider.credentialed_facilities)[:5]}...")
            failed += 1
        else:
            passed += 1

print(f"  ✓ All {passed} assignments respect credentialing")

# Specific checks
print("\n  Specific credentialing checks:")
bob_in_hospital_a = any(
    'Hospital_A' in shift_id
    for _, shift_id in provider_assignments.get('Dr. Bob', [])
)
if bob_in_hospital_a:
    print(f"  ❌ FAILED: Dr. Bob assigned to Hospital A (not credentialed)")
    failed += 1
else:
    print(f"  ✓ Dr. Bob NOT assigned to Hospital A (correct - not credentialed)")

diana_non_c = any(
    'Hospital_C' not in shift_id
    for _, shift_id in provider_assignments.get('Dr. Diana', [])
)
if diana_non_c:
    print(f"  ❌ FAILED: Dr. Diana assigned to non-Hospital C shift")
    failed += 1
else:
    print(f"  ✓ Dr. Diana ONLY assigned to Hospital C (correct)")

# 2. Availability Constraints
print("\n2. AVAILABILITY CONSTRAINTS")
print("-"*80)
availability_violations = 0

# Dr. Bob unavailable Wednesday (day 2, 0-indexed)
bob_wed = any(day_idx == 2 for day_idx, _ in provider_assignments.get('Dr. Bob', []))
if bob_wed:
    print(f"  ❌ FAILED: Dr. Bob assigned on Wednesday (unavailable)")
    failed += 1
    availability_violations += 1
else:
    print(f"  ✓ Dr. Bob NOT assigned Wednesday (correct - unavailable)")
    passed += 1

# Dr. Diana unavailable Friday & Saturday (days 4, 5)
diana_fri_sat = any(day_idx in [4, 5] for day_idx, _ in provider_assignments.get('Dr. Diana', []))
if diana_fri_sat:
    print(f"  ❌ FAILED: Dr. Diana assigned on Friday or Saturday (unavailable)")
    failed += 1
    availability_violations += 1
else:
    print(f"  ✓ Dr. Diana NOT assigned Friday/Saturday (correct - unavailable)")
    passed += 1

# Dr. Eve unavailable Sunday (day 6)
eve_sun = any(day_idx == 6 for day_idx, _ in provider_assignments.get('Dr. Eve', []))
if eve_sun:
    print(f"  ❌ FAILED: Dr. Eve assigned on Sunday (unavailable)")
    failed += 1
    availability_violations += 1
else:
    print(f"  ✓ Dr. Eve NOT assigned Sunday (correct - unavailable)")
    passed += 1

# 3. Shift Count Constraints
print("\n3. SHIFT COUNT CONSTRAINTS")
print("-"*80)
for provider_name, provider in data.providers.items():
    assignments = provider_assignments.get(provider_name, [])
    actual_count = len(assignments)
    contracted = provider.total_shift_count

    if provider.contract_type == 'FT':
        # Full-time: must be exact
        if actual_count != contracted:
            print(f"  ❌ FAILED: {provider_name} (FT) has {actual_count} shifts, needs exactly {contracted}")
            failed += 1
        else:
            print(f"  ✓ {provider_name} (FT): {actual_count}/{contracted} shifts (exact match)")
            passed += 1
    else:  # IC
        # Independent contractor: can be less than or equal
        if actual_count > contracted:
            print(f"  ❌ FAILED: {provider_name} (IC) has {actual_count} shifts, max is {contracted}")
            failed += 1
        else:
            print(f"  ✓ {provider_name} (IC): {actual_count}/{contracted} shifts (within limit)")
            passed += 1

# 4. Weekend Shift Constraints
print("\n4. WEEKEND SHIFT CONSTRAINTS")
print("-"*80)
for provider_name, provider in data.providers.items():
    assignments = provider_assignments.get(provider_name, [])
    weekend_count = sum(1 for day_idx, _ in assignments if is_weekend(day_idx))
    max_weekend = provider.weekend_shift_count

    if weekend_count > max_weekend:
        print(f"  ❌ FAILED: {provider_name} has {weekend_count} weekend shifts, max is {max_weekend}")
        failed += 1
    else:
        print(f"  ✓ {provider_name}: {weekend_count}/{max_weekend} weekend shifts")
        passed += 1

# 5. PM Shift Constraints
print("\n5. PM SHIFT CONSTRAINTS")
print("-"*80)
for provider_name, provider in data.providers.items():
    assignments = provider_assignments.get(provider_name, [])
    pm_count = sum(1 for _, shift_id in assignments if get_shift_type(shift_id) == 'PM')
    max_pm = provider.pm_shift_count

    if pm_count > max_pm:
        print(f"  ❌ FAILED: {provider_name} has {pm_count} PM shifts, max is {max_pm}")
        failed += 1
    else:
        print(f"  ✓ {provider_name}: {pm_count}/{max_pm} PM shifts")
        passed += 1

# P2 Soft Constraints
print("\n" + "="*80)
print("P2 SOFT CONSTRAINT ANALYSIS (PREFERENCES)")
print("="*80)

print("\n6. SHIFT PREFERENCE MATCHING")
print("-"*80)
for provider_name, provider in data.providers.items():
    assignments = provider_assignments.get(provider_name, [])
    preferences = provider.shift_preference

    if not assignments:
        continue

    shift_types = [get_shift_type(shift_id) for _, shift_id in assignments]
    violations = [st for st in shift_types if st not in preferences]

    if violations:
        print(f"  ⚠️  {provider_name} (prefers {preferences}):")
        print(f"      Assigned {len(assignments)} shifts: {dict((st, shift_types.count(st)) for st in set(shift_types))}")
        print(f"      {len(violations)} preference violations")
        warnings += 1
    else:
        print(f"  ✓ {provider_name} (prefers {preferences}): All assignments match preference")

# Coverage Analysis
print("\n7. COVERAGE ANALYSIS")
print("-"*80)
total_slots = len(data.shifts) * len(data.days)
filled_slots = sum(len(providers) for providers in shift_coverage.values())
coverage_pct = (filled_slots / total_slots * 100)

print(f"  Total shift slots: {total_slots}")
print(f"  Filled slots: {filled_slots}")
print(f"  Coverage: {coverage_pct:.1f}%")
print(f"  Uncovered slots: {total_slots - filled_slots}")

# Summary
print("\n" + "="*80)
print("VERIFICATION SUMMARY")
print("="*80)
print(f"Hard constraints passed: {passed}")
print(f"Hard constraints failed: {failed}")
print(f"Soft constraint warnings: {warnings}")
print()

if failed == 0:
    print("✅ ALL HARD CONSTRAINTS SATISFIED!")
    print("   The schedule is VALID and ready to use.")
else:
    print(f"❌ {failed} CONSTRAINT VIOLATIONS FOUND!")
    print("   The schedule has issues that need to be fixed.")

print()
print("="*80)
