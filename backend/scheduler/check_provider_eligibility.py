#!/usr/bin/env python3
"""
Script to check which providers can service specific facility groups
"""
import pandas as pd
import sys
from typing import List, Set, Dict
from data_loader import DataLoader

def check_provider_eligibility(facility_group: str = None):
    """
    Check which providers are eligible to work each facility group

    Args:
        facility_group: Optional specific facility group to check (e.g., "MD1 - WRNMMC, FBCH")
                       If None, shows all facility groups
    """
    print("="*80)
    print("PROVIDER ELIGIBILITY CHECKER")
    print("="*80)
    print()

    # Load data
    print("Loading data...")
    loader = DataLoader()
    data = loader.load_all_data(num_days=1)  # We only need structure, not days

    print(f"Found {len(data.providers)} providers and {len(data.shifts)} facility groups\n")

    # Build eligibility mapping
    eligibility_map = {}

    for shift_id, shift in data.shifts.items():
        eligible_providers = []

        for provider_name, provider in data.providers.items():
            # Check if provider is credentialed for ALL facilities in this group
            is_eligible = all(
                facility in provider.credentialed_facilities
                for facility in shift.facilities
            )

            if is_eligible:
                eligible_providers.append(provider_name)

        eligibility_map[shift_id] = {
            'facilities': shift.facilities,
            'shift_type': shift.shift_type,
            'volume': shift.expected_volume,
            'eligible_providers': eligible_providers,
            'count': len(eligible_providers)
        }

    # Display results
    if facility_group:
        # Show specific facility group
        if facility_group in eligibility_map:
            show_facility_group_details(facility_group, eligibility_map[facility_group])
        else:
            print(f"❌ Facility group '{facility_group}' not found!")
            print("\nAvailable facility groups:")
            for fg in sorted(eligibility_map.keys()):
                print(f"  - {fg}")
    else:
        # Show all facility groups
        show_all_facility_groups(eligibility_map)

def show_facility_group_details(group_name: str, info: Dict):
    """Display detailed information about a specific facility group"""
    print(f"Facility Group: {group_name}")
    print("-" * 80)
    print(f"Shift Type: {info['shift_type']}")
    print(f"Facilities: {', '.join(info['facilities'])}")
    print(f"Expected Volume: {info['volume']:.2f}")
    print(f"Eligible Providers: {info['count']}")
    print()

    if info['eligible_providers']:
        print("Providers who can work this facility group:")
        for i, provider in enumerate(sorted(info['eligible_providers']), 1):
            print(f"  {i:3}. {provider}")
    else:
        print("⚠️  NO PROVIDERS ARE ELIGIBLE FOR THIS FACILITY GROUP!")
        print("    (No provider is credentialed for all required facilities)")

def show_all_facility_groups(eligibility_map: Dict):
    """Display summary of all facility groups"""

    # Separate groups by eligibility status
    no_providers = []
    few_providers = []
    normal_groups = []

    for group_name, info in eligibility_map.items():
        if info['count'] == 0:
            no_providers.append(group_name)
        elif info['count'] <= 3:
            few_providers.append((group_name, info['count']))
        else:
            normal_groups.append((group_name, info['count']))

    # Show problematic groups first
    if no_providers:
        print("❌ CRITICAL: Facility groups with NO eligible providers:")
        print("-" * 80)
        for group in sorted(no_providers):
            facilities = ', '.join(eligibility_map[group]['facilities'])
            print(f"  • {group}")
            print(f"    Facilities: {facilities}")
        print()

    if few_providers:
        print("⚠️  WARNING: Facility groups with FEW eligible providers (≤3):")
        print("-" * 80)
        for group, count in sorted(few_providers):
            print(f"  • {group} ({count} providers)")
        print()

    # Show summary statistics
    print("📊 SUMMARY STATISTICS:")
    print("-" * 80)
    total_groups = len(eligibility_map)
    avg_providers = sum(info['count'] for info in eligibility_map.values()) / total_groups

    print(f"  Total facility groups: {total_groups}")
    print(f"  Groups with no providers: {len(no_providers)}")
    print(f"  Groups with 1-3 providers: {len(few_providers)}")
    print(f"  Groups with 4+ providers: {len(normal_groups)}")
    print(f"  Average providers per group: {avg_providers:.1f}")
    print()

    # Show groups by shift type
    by_shift_type = {'MD1': [], 'MD2': [], 'PM': []}
    for group_name, info in eligibility_map.items():
        shift_type = info['shift_type']
        if shift_type in by_shift_type:
            by_shift_type[shift_type].append((group_name, info['count']))

    print("📋 GROUPS BY SHIFT TYPE:")
    print("-" * 80)
    for shift_type in ['MD1', 'MD2', 'PM']:
        groups = by_shift_type[shift_type]
        if groups:
            avg_count = sum(count for _, count in groups) / len(groups)
            print(f"\n{shift_type} Shifts ({len(groups)} groups, avg {avg_count:.1f} providers):")

            # Sort by provider count (ascending) to show problematic ones first
            for group_name, count in sorted(groups, key=lambda x: x[1])[:5]:
                status = "❌" if count == 0 else "⚠️ " if count <= 3 else "✓"
                print(f"  {status} {group_name[:40]:<40} | {count} providers")

            if len(groups) > 5:
                print(f"  ... and {len(groups) - 5} more")

    print("\n" + "="*80)
    print("Use --facility-group 'NAME' to see details for a specific group")
    print("Example: python check_provider_eligibility.py --facility-group 'MD1 - WRNMMC, FBCH'")

def main():
    """Main entry point"""
    facility_group = None

    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h']:
            print("Usage: python check_provider_eligibility.py [--facility-group 'GROUP_NAME']")
            print("\nExamples:")
            print("  python check_provider_eligibility.py")
            print("  python check_provider_eligibility.py --facility-group 'MD1 - WRNMMC, FBCH'")
            print("  python check_provider_eligibility.py --facility-group 'MD2 - FHWM, FNHM'")
            return
        elif sys.argv[1] == '--facility-group' and len(sys.argv) > 2:
            facility_group = sys.argv[2]

    try:
        check_provider_eligibility(facility_group)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()