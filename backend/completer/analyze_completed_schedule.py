#!/usr/bin/env python3
"""
Analyze the completed schedule with proper shift counting
"""

import pandas as pd
import numpy as np
from typing import Dict, Set, Tuple
import sys
sys.path.append('scheduler')
from data_loader import DataLoader

def analyze_schedule(schedule_path: str = 'output/completed_schedule.xlsx'):
    """Properly analyze the completed schedule"""
    print("="*80)
    print("COMPLETED SCHEDULE ANALYSIS")
    print("="*80)
    print()

    # Load schedule and data
    df = pd.read_excel(schedule_path)
    loader = DataLoader()
    data = loader.load_all_data(num_days=31)

    # Get shift columns
    shift_columns = [col for col in df.columns if ' - ' in str(col)]

    # Initialize provider statistics
    provider_stats = {}
    for provider_name, provider in data.providers.items():
        provider_stats[provider_name] = {
            'contract_type': provider.contract_type,
            'contracted_shifts': provider.total_shift_count,
            'contracted_weekends': provider.weekend_shift_count,
            'contracted_pm': provider.pm_shift_count,
            'actual_shifts': 0,
            'actual_weekends': 0,
            'actual_pm': 0,
            'days_worked': set(),
            'shift_types_by_day': {},  # day -> set of shift types
            'facility_groups_by_day': {}  # day -> list of facility groups
        }

    # Count assignments properly (a shift = unique shift TYPE per day)
    for day_idx in range(len(df)):
        day_num = day_idx + 1
        is_weekend = df.loc[day_idx, 'Day of Week'] in ['Saturday', 'Sunday']

        # Track which providers work which shift types on this day
        provider_shift_types = {}  # provider -> set of shift types

        for col in shift_columns:
            if pd.notna(df.loc[day_idx, col]):
                provider = df.loc[day_idx, col]
                shift_type = col.split(' - ')[0].strip()

                if provider in provider_stats:
                    # Track this facility group
                    if day_num not in provider_stats[provider]['facility_groups_by_day']:
                        provider_stats[provider]['facility_groups_by_day'][day_num] = []
                    provider_stats[provider]['facility_groups_by_day'][day_num].append(col)

                    # Track shift type for this day
                    if provider not in provider_shift_types:
                        provider_shift_types[provider] = set()
                    provider_shift_types[provider].add(shift_type)

        # Now count unique shift types per provider for this day
        for provider, shift_types in provider_shift_types.items():
            # Each unique shift type counts as one shift
            num_shifts_today = len(shift_types)
            provider_stats[provider]['actual_shifts'] += num_shifts_today
            provider_stats[provider]['days_worked'].add(day_num)
            provider_stats[provider]['shift_types_by_day'][day_num] = shift_types

            # Count weekends
            if is_weekend:
                provider_stats[provider]['actual_weekends'] += num_shifts_today

            # Count PM shifts
            if 'PM' in shift_types:
                provider_stats[provider]['actual_pm'] += 1

    # Print coverage analysis
    print("📊 COVERAGE ANALYSIS:")
    print("-" * 80)
    total_slots = 0
    filled_slots = 0
    for col in shift_columns:
        total_slots += len(df)
        filled_slots += df[col].notna().sum()

    print(f"Total shift-day slots: {total_slots}")
    print(f"Filled slots: {filled_slots}")
    print(f"Empty slots: {total_slots - filled_slots}")
    print(f"Coverage rate: {filled_slots/total_slots*100:.1f}%")

    # Print fairness analysis
    print("\n📊 FAIRNESS ANALYSIS (CORRECTED):")
    print("-" * 80)

    fairness_data = []
    for provider_name, stats in provider_stats.items():
        if stats['actual_shifts'] > 0 or stats['contracted_shifts'] > 0:
            utilization = stats['actual_shifts'] / max(stats['contracted_shifts'], 1)
            fairness_data.append({
                'Provider': provider_name,
                'Type': stats['contract_type'],
                'Contracted': stats['contracted_shifts'],
                'Actual': stats['actual_shifts'],
                'Utilization': utilization,
                'Days_Worked': len(stats['days_worked']),
                'Weekend_Contract': stats['contracted_weekends'],
                'Weekend_Actual': stats['actual_weekends'],
                'PM_Contract': stats['contracted_pm'],
                'PM_Actual': stats['actual_pm']
            })

    df_fairness = pd.DataFrame(fairness_data)
    df_fairness = df_fairness.sort_values('Utilization', ascending=False)

    # Group by utilization levels
    under_80 = df_fairness[df_fairness['Utilization'] < 0.8]
    optimal = df_fairness[(df_fairness['Utilization'] >= 0.8) & (df_fairness['Utilization'] <= 1.2)]
    over_120 = df_fairness[df_fairness['Utilization'] > 1.2]

    print(f"\n✅ Optimal (80-120% of contract): {len(optimal)} providers")
    for _, row in optimal.head(10).iterrows():
        print(f"   {row['Provider']:20} {row['Actual']}/{row['Contracted']} shifts ({row['Utilization']:.1%})")

    print(f"\n⚠️  Under-utilized (<80% of contract): {len(under_80)} providers")
    for _, row in under_80.head(10).iterrows():
        print(f"   {row['Provider']:20} {row['Actual']}/{row['Contracted']} shifts ({row['Utilization']:.1%})")

    print(f"\n⚠️  Over-utilized (>120% of contract): {len(over_120)} providers")
    for _, row in over_120.head(10).iterrows():
        print(f"   {row['Provider']:20} {row['Actual']}/{row['Contracted']} shifts ({row['Utilization']:.1%})")

    # Calculate fairness metrics
    print("\n📈 FAIRNESS METRICS:")
    print("-" * 80)
    utilizations = df_fairness['Utilization']

    print(f"Average utilization: {utilizations.mean():.1%}")
    print(f"Standard deviation: {utilizations.std():.1%}")
    print(f"Min utilization: {utilizations.min():.1%}")
    print(f"Max utilization: {utilizations.max():.1%}")

    # Calculate Gini coefficient
    sorted_utils = sorted(utilizations)
    n = len(sorted_utils)
    cumsum = np.cumsum(sorted_utils)
    if sum(sorted_utils) > 0:
        gini = (2 * sum((i+1) * util for i, util in enumerate(sorted_utils))) / (n * sum(sorted_utils)) - (n+1)/n
        print(f"Gini coefficient: {gini:.3f} (0=perfect equality, 1=maximum inequality)")

    # Print sample provider details
    print("\n📋 SAMPLE PROVIDER DETAILS:")
    print("-" * 80)

    sample_providers = ['Spencer Stevens', 'Riley Adams', 'Spencer Irving', 'Cameron Walker', 'Quinn Turner']
    for provider in sample_providers:
        if provider in provider_stats:
            stats = provider_stats[provider]
            if stats['actual_shifts'] > 0:
                print(f"\n{provider}:")
                print(f"  Contract: {stats['contracted_shifts']} shifts")
                print(f"  Actual: {stats['actual_shifts']} shifts")
                print(f"  Days worked: {len(stats['days_worked'])}")
                print(f"  Weekend shifts: {stats['actual_weekends']}/{stats['contracted_weekends']}")
                print(f"  PM shifts: {stats['actual_pm']}/{stats['contracted_pm']}")

                # Show a sample day
                if stats['shift_types_by_day']:
                    sample_day = list(stats['shift_types_by_day'].keys())[0]
                    shift_types = stats['shift_types_by_day'][sample_day]
                    facilities = stats['facility_groups_by_day'].get(sample_day, [])
                    print(f"  Example Day {sample_day}:")
                    print(f"    Shift types: {', '.join(shift_types)}")
                    if len(facilities) <= 3:
                        for facility in facilities:
                            print(f"      - {facility}")
                    else:
                        print(f"      - {len(facilities)} facility groups")

    # Save corrected report
    df_fairness.to_csv('output/corrected_fairness_report.csv', index=False)
    print("\n✅ Corrected fairness report saved to: output/corrected_fairness_report.csv")

    return df_fairness

if __name__ == "__main__":
    analyze_schedule()