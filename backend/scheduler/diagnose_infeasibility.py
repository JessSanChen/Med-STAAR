"""
Diagnostic script to identify infeasibility causes
"""
from data_loader import DataLoader
import pandas as pd


def diagnose_data_issues():
    """Analyze data to identify potential infeasibility causes"""

    print("="*80)
    print("DIAGNOSING POTENTIAL INFEASIBILITY ISSUES")
    print("="*80)

    loader = DataLoader()
    data = loader.load_all_data(num_days=31)

    # 1. Check supply vs demand
    print("\n1. SUPPLY VS DEMAND ANALYSIS")
    print("-"*80)

    total_shift_slots = len(data.shifts) * len(data.days)
    print(f"Total shift slots to fill: {total_shift_slots} (88 shifts x 31 days)")

    # Calculate total available provider-shifts
    total_ft_shifts = sum(p.total_shift_count for p in data.providers.values() if p.contract_type == 'FT')
    total_ic_shifts = sum(p.total_shift_count for p in data.providers.values() if p.contract_type == 'IC')
    total_provider_shifts = total_ft_shifts + total_ic_shifts

    print(f"Total FT contracted shifts: {total_ft_shifts}")
    print(f"Total IC contracted shifts (max): {total_ic_shifts}")
    print(f"Total provider capacity: {total_provider_shifts}")
    print(f"Ratio: {total_provider_shifts / total_shift_slots:.2f}x")

    if total_provider_shifts < total_shift_slots:
        print("⚠️  WARNING: Not enough provider capacity to fill all shifts!")
    else:
        print("✓ Sufficient provider capacity exists")

    # 2. Check credentialing coverage
    print("\n2. CREDENTIALING ANALYSIS")
    print("-"*80)

    uncovered_shifts = 0
    poorly_covered = []

    for shift_id, shift in data.shifts.items():
        # Count how many providers can work this shift
        eligible_providers = []
        for provider_name, provider in data.providers.items():
            is_credentialed = all(
                facility in provider.credentialed_facilities
                for facility in shift.facilities
            )
            if is_credentialed:
                eligible_providers.append(provider_name)

        if len(eligible_providers) == 0:
            uncovered_shifts += 1
            print(f"  ⚠️  No providers credentialed for: {shift_id[:60]}")
        elif len(eligible_providers) < 5:
            poorly_covered.append((shift_id, len(eligible_providers)))

    print(f"\nShifts with NO eligible providers: {uncovered_shifts}/{len(data.shifts)}")
    print(f"Shifts with <5 eligible providers: {len(poorly_covered)}/{len(data.shifts)}")

    if poorly_covered:
        print("\nPoorly covered shifts:")
        for shift_id, count in sorted(poorly_covered, key=lambda x: x[1])[:10]:
            print(f"  {shift_id[:60]}: {count} providers")

    # 3. Check FT provider constraints
    print("\n3. FULL-TIME PROVIDER ANALYSIS")
    print("-"*80)

    for provider_name, provider in data.providers.items():
        if provider.contract_type == 'FT':
            # Count eligible shifts
            eligible_shifts = []
            for shift_id, shift in data.shifts.items():
                is_credentialed = all(
                    facility in provider.credentialed_facilities
                    for facility in shift.facilities
                )
                if is_credentialed:
                    eligible_shifts.append(shift_id)

            # Maximum possible assignments (accounting for availability)
            available_days = sum(1 for day in data.days if provider.availability.get(day, True))
            max_possible = len(eligible_shifts) * available_days

            if provider.total_shift_count > max_possible:
                print(f"  ⚠️  {provider_name}: needs {provider.total_shift_count} shifts, "
                      f"but max possible is {max_possible}")
                print(f"      (eligible shifts: {len(eligible_shifts)}, available days: {available_days})")

    # 4. Check weekend constraints
    print("\n4. WEEKEND CONSTRAINT ANALYSIS")
    print("-"*80)

    weekend_shifts_needed = len(data.shifts) * len(data.weekends)
    weekend_capacity = sum(p.weekend_shift_count for p in data.providers.values())

    print(f"Weekend shift slots: {weekend_shifts_needed} ({len(data.shifts)} shifts x {len(data.weekends)} weekend days)")
    print(f"Weekend provider capacity: {weekend_capacity}")
    print(f"Ratio: {weekend_capacity / weekend_shifts_needed:.2f}x")

    if weekend_capacity < weekend_shifts_needed:
        print("⚠️  WARNING: Not enough weekend capacity!")
    else:
        print("✓ Sufficient weekend capacity")

    # 5. Availability analysis
    print("\n5. AVAILABILITY ANALYSIS")
    print("-"*80)

    providers_with_restrictions = 0
    for provider_name, provider in data.providers.items():
        unavailable_days = sum(1 for day in data.days if not provider.availability.get(day, True))
        if unavailable_days > 0:
            providers_with_restrictions += 1

    print(f"Providers with availability restrictions: {providers_with_restrictions}/{len(data.providers)}")

    # 6. Recommendations
    print("\n6. RECOMMENDATIONS")
    print("-"*80)

    if uncovered_shifts > 0:
        print("1. ⚠️  CRITICAL: Some shifts have no credentialed providers")
        print("   → Remove these shifts from the schedule or expand provider credentialing")

    if total_provider_shifts < total_shift_slots * 0.9:
        print("2. ⚠️  Not enough provider capacity for all shifts")
        print("   → Consider reducing number of shifts or increasing provider capacity")

    if weekend_capacity < weekend_shifts_needed * 0.9:
        print("3. ⚠️  Insufficient weekend coverage capacity")
        print("   → Increase weekend shift allowances for providers")

    print("\n4. Consider relaxing constraints:")
    print("   - Allow shift coverage gaps (don't require every shift to be filled)")
    print("   - Allow FT providers some flexibility around target (±1 shift)")
    print("   - Temporarily relax consecutive shift constraints for testing")


if __name__ == '__main__':
    diagnose_data_issues()
