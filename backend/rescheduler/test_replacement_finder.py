#!/usr/bin/env python3
"""
Test script for the Shift Replacement Finder
Demonstrates usage with sample scenarios
"""

import sys
from datetime import datetime
from data_loader import DataLoader
from shift_replacement_finder import ShiftReplacementFinder


def create_sample_schedule(data):
    """Create a sample current schedule for testing"""
    schedule = {}

    # Sample assignments for first few days
    sample_assignments = {
        0: {  # Day 0
            'MD1 - NHMC, NMMC': ['Dr. Anderson'],
            'MD2 - NBAMC, NMHMC': ['Dr. Brown'],
            'PM - NHMC': ['Dr. Chen']
        },
        1: {  # Day 1
            'MD1 - NHMC, NMMC': ['Dr. Davis'],
            'PM - NBAMC': ['Dr. Evans']
        },
        2: {  # Day 2
            'MD1 - NBAMC': ['Dr. Anderson'],  # Dr. Anderson working consecutive MD1
            'MD2 - NHMC, NMHMC': ['Dr. Foster']
        }
    }

    # Only include assignments for shifts that actually exist in the data
    for day, shifts in sample_assignments.items():
        if day in data.days:
            schedule[day] = {}
            for shift_id, providers in shifts.items():
                if shift_id in data.shifts:
                    schedule[day][shift_id] = providers

    return schedule


def test_scenario_1(data, finder):
    """Test Scenario 1: Regular weekday shift replacement"""
    print("\n" + "="*100)
    print("TEST SCENARIO 1: Regular Weekday MD1 Shift Replacement")
    print("="*100)
    print("Scenario: Dr. Anderson called in sick for Day 2 MD1 shift")
    print("Context: Dr. Anderson already worked MD1 on Day 0 and Day 2")

    # Find first available MD1 shift
    md1_shifts = [shift_id for shift_id, shift in data.shifts.items()
                  if shift.shift_type == 'MD1']

    if md1_shifts:
        test_shift = md1_shifts[0]
        test_day = 2

        candidates = finder.find_replacements(
            shift_id=test_shift,
            day=test_day,
            dropped_provider="Dr. Anderson"
        )

        finder.print_replacement_report(candidates, max_candidates=5)
        return candidates
    else:
        print("No MD1 shifts found in data")
        return []


def test_scenario_2(data, finder):
    """Test Scenario 2: Weekend PM shift replacement"""
    print("\n" + "="*100)
    print("TEST SCENARIO 2: Weekend PM Shift Replacement")
    print("="*100)
    print("Scenario: Need to find weekend PM shift replacement")

    # Find a weekend day and PM shift
    weekend_days = [day for day in data.days if day in data.weekends]
    pm_shifts = [shift_id for shift_id, shift in data.shifts.items()
                 if shift.shift_type == 'PM']

    if weekend_days and pm_shifts:
        test_day = weekend_days[0]
        test_shift = pm_shifts[0]

        print(f"Testing weekend day {test_day} ({data.day_index_to_date[test_day].strftime('%A')})")

        candidates = finder.find_replacements(
            shift_id=test_shift,
            day=test_day
        )

        finder.print_replacement_report(candidates, max_candidates=5)
        return candidates
    else:
        print("No weekend days or PM shifts found in data")
        return []


def test_scenario_3(data, finder):
    """Test Scenario 3: High-credentialing requirement shift"""
    print("\n" + "="*100)
    print("TEST SCENARIO 3: Shift Requiring Multiple Facility Credentials")
    print("="*100)
    print("Scenario: Replacement needed for shift covering multiple facilities")

    # Find a shift with multiple facilities
    multi_facility_shifts = [
        (shift_id, shift) for shift_id, shift in data.shifts.items()
        if len(shift.facilities) >= 2
    ]

    if multi_facility_shifts:
        test_shift_id, test_shift = multi_facility_shifts[0]
        test_day = 5

        print(f"Testing shift with {len(test_shift.facilities)} facilities: {', '.join(test_shift.facilities)}")

        candidates = finder.find_replacements(
            shift_id=test_shift_id,
            day=test_day
        )

        finder.print_replacement_report(candidates, max_candidates=5)
        return candidates
    else:
        print("No multi-facility shifts found in data")
        return []


def analyze_system_constraints(data):
    """Analyze the constraint complexity of the system"""
    print("\n" + "="*100)
    print("SYSTEM CONSTRAINT ANALYSIS")
    print("="*100)

    # Provider analysis
    print(f"PROVIDERS ({len(data.providers)}):")
    ft_providers = [p for p in data.providers.values() if p.contract_type == 'FT']
    ic_providers = [p for p in data.providers.values() if p.contract_type == 'IC']

    print(f"  Full-time: {len(ft_providers)}")
    print(f"  Independent Contractor: {len(ic_providers)}")

    # Credentialing complexity
    all_facilities = set()
    for provider in data.providers.values():
        all_facilities.update(provider.credentialed_facilities)

    print(f"\nFACILITIES ({len(all_facilities)}):")
    for facility in sorted(all_facilities)[:10]:
        credentialed_count = sum(1 for p in data.providers.values()
                               if facility in p.credentialed_facilities)
        print(f"  {facility}: {credentialed_count} providers credentialed")

    if len(all_facilities) > 10:
        print(f"  ... and {len(all_facilities) - 10} more facilities")

    # Shift type analysis
    shift_types = {}
    for shift in data.shifts.values():
        shift_types[shift.shift_type] = shift_types.get(shift.shift_type, 0) + 1

    print(f"\nSHIFT TYPES:")
    for shift_type, count in shift_types.items():
        print(f"  {shift_type}: {count} shifts")

    # Preference analysis
    preferences = {}
    for provider in data.providers.values():
        for pref in provider.shift_preference:
            preferences[pref] = preferences.get(pref, 0) + 1

    print(f"\nSHIFT PREFERENCES:")
    for pref, count in preferences.items():
        print(f"  {pref}: {count} providers prefer")


def main():
    print("SHIFT REPLACEMENT FINDER - TEST SUITE")
    print("="*100)

    # Load data
    print("Loading scheduling data...")
    try:
        loader = DataLoader(data_dir='../../data')
        data = loader.load_all_data(num_days=31)
        print(f"✓ Loaded {len(data.providers)} providers, {len(data.shifts)} shifts, {len(data.days)} days")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        print("Make sure you're running this from the scheduler directory with data in ../data/")
        sys.exit(1)

    # Analyze system constraints
    analyze_system_constraints(data)

    # Create sample schedule
    current_schedule = create_sample_schedule(data)
    print(f"\n✓ Created sample schedule with {sum(len(shifts) for shifts in current_schedule.values())} assignments")

    # Initialize replacement finder
    finder = ShiftReplacementFinder(data, current_schedule)

    # Run test scenarios
    scenarios = [
        test_scenario_1,
        test_scenario_2,
        test_scenario_3
    ]

    results = {}
    for i, scenario_func in enumerate(scenarios, 1):
        try:
            candidates = scenario_func(data, finder)
            viable_count = len([c for c in candidates if c.viability_score > -1000])
            results[f"Scenario {i}"] = {
                'total_candidates': len(candidates),
                'viable_candidates': viable_count
            }
        except Exception as e:
            print(f"❌ Error in scenario {i}: {e}")
            results[f"Scenario {i}"] = {'error': str(e)}

    # Summary
    print("\n" + "="*100)
    print("TEST SUMMARY")
    print("="*100)

    for scenario_name, result in results.items():
        if 'error' in result:
            print(f"{scenario_name}: ❌ Error - {result['error']}")
        else:
            total = result['total_candidates']
            viable = result['viable_candidates']
            print(f"{scenario_name}: {viable}/{total} viable candidates")

    print(f"\nReplacement Finder is ready for use!")
    print(f"Run with: python shift_replacement_finder.py --help")


if __name__ == '__main__':
    main()