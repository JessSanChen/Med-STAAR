#!/usr/bin/env python3
"""
Fill Remaining Schedule Slots with Relaxed Constraints and Fairness Optimization

This script fills empty slots in an existing schedule while:
1. Maintaining hard constraints (credentialing, coverage requirements)
2. Relaxing soft constraints (shift counts, weekend/PM limits, volume)
3. Optimizing for fairness across all providers
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Set
import sys
sys.path.append('scheduler')
from data_loader import DataLoader
import json

class FairnessOptimizer:
    """Optimizer that fills remaining slots while maintaining fairness"""

    def __init__(self, schedule_path: str = './scheduler/final_schedule.xlsx'):
        """Initialize with existing schedule and data"""
        print("="*80)
        print("FAIRNESS-BASED SCHEDULE COMPLETION")
        print("="*80)
        print()

        # Load existing schedule
        self.schedule_df = pd.read_excel(schedule_path)
        self.shift_columns = [col for col in self.schedule_df.columns if ' - ' in str(col)]

        # Load scheduling data
        print("Loading scheduling data...")
        self.loader = DataLoader()
        self.data = self.loader.load_all_data(num_days=31)

        # Track provider assignments
        self.provider_stats = {}
        self._calculate_current_stats()

    def _calculate_current_stats(self):
        """Calculate current provider statistics from existing schedule"""
        print("\nAnalyzing current schedule...")

        for provider_name, provider in self.data.providers.items():
            self.provider_stats[provider_name] = {
                'contract_type': provider.contract_type,
                'contracted_shifts': provider.total_shift_count,
                'contracted_weekends': provider.weekend_shift_count,
                'contracted_pm': provider.pm_shift_count,
                'current_shifts': 0,
                'current_weekends': 0,
                'current_pm': 0,
                'shifts_by_type': {'MD1': 0, 'MD2': 0, 'PM': 0},
                'credentialed_facilities': provider.credentialed_facilities,
                'shift_preference': provider.shift_preference
            }

        # Count current assignments
        for day_idx in range(len(self.schedule_df)):
            is_weekend = self.schedule_df.loc[day_idx, 'Day of Week'] in ['Saturday', 'Sunday']

            for col in self.shift_columns:
                if pd.notna(self.schedule_df.loc[day_idx, col]):
                    provider = self.schedule_df.loc[day_idx, col]
                    if provider in self.provider_stats:
                        # Parse shift type from column name
                        shift_type = col.split(' - ')[0].strip()

                        self.provider_stats[provider]['current_shifts'] += 1
                        self.provider_stats[provider]['shifts_by_type'][shift_type] += 1

                        if is_weekend:
                            self.provider_stats[provider]['current_weekends'] += 1
                        if shift_type == 'PM':
                            self.provider_stats[provider]['current_pm'] += 1

    def calculate_fairness_score(self, provider_name: str, shift_type: str,
                                 is_weekend: bool) -> float:
        """
        Calculate fairness score for assigning a provider to a slot.

        HIGHER score = BETTER (more fair) assignment

        Components:
        1. Contract utilization balance (0-100 points)
        2. Preference matching (0-30 points)
        3. Workload distribution (0-20 points)
        4. Weekend/PM balance (0-20 points)

        Total: 0-170 points (normalized to 0-1)
        """
        stats = self.provider_stats[provider_name]
        score = 0.0
        explanation = []

        # 1. CONTRACT UTILIZATION BALANCE (0-100 points)
        # Favor providers who are furthest below their contract limits
        current_ratio = stats['current_shifts'] / max(stats['contracted_shifts'], 1)
        if current_ratio < 1.0:
            # Under contract - good candidate
            utilization_score = (1.0 - current_ratio) * 100
            explanation.append(f"Under-utilized: {current_ratio:.1%} of contract (+{utilization_score:.1f})")
        elif current_ratio < 1.2:
            # Slightly over - acceptable but penalized
            utilization_score = 50 * (1.2 - current_ratio) / 0.2
            explanation.append(f"Slightly over: {current_ratio:.1%} of contract (+{utilization_score:.1f})")
        else:
            # Significantly over - heavily penalized
            utilization_score = max(0, 10 - (current_ratio - 1.2) * 50)
            explanation.append(f"Over-utilized: {current_ratio:.1%} of contract (+{utilization_score:.1f})")
        score += utilization_score

        # 2. PREFERENCE MATCHING (0-30 points)
        if shift_type in stats['shift_preference']:
            score += 30
            explanation.append(f"Preferred shift type (+30)")
        else:
            explanation.append(f"Non-preferred shift type (+0)")

        # 3. WORKLOAD DISTRIBUTION (0-20 points)
        # Favor providers with fewer total shifts to balance workload
        avg_shifts = sum(p['current_shifts'] for p in self.provider_stats.values()) / len(self.provider_stats)
        if stats['current_shifts'] < avg_shifts:
            workload_score = min(20, (avg_shifts - stats['current_shifts']) * 5)
            score += workload_score
            explanation.append(f"Below avg workload (+{workload_score:.1f})")

        # 4. WEEKEND/PM BALANCE (0-20 points)
        if is_weekend:
            weekend_ratio = stats['current_weekends'] / max(stats['contracted_weekends'], 1)
            if weekend_ratio < 1.0:
                weekend_score = (1.0 - weekend_ratio) * 10
                score += weekend_score
                explanation.append(f"Under weekend limit (+{weekend_score:.1f})")

        if shift_type == 'PM':
            pm_ratio = stats['current_pm'] / max(stats['contracted_pm'], 1)
            if pm_ratio < 1.0:
                pm_score = (1.0 - pm_ratio) * 10
                score += pm_score
                explanation.append(f"Under PM limit (+{pm_score:.1f})")

        # Normalize to 0-1 range
        normalized_score = score / 170

        return normalized_score, explanation

    def find_eligible_providers(self, shift_id: str) -> List[str]:
        """Find providers who are credentialed for all facilities in a shift"""
        shift = self.data.shifts[shift_id]
        eligible = []

        for provider_name, provider in self.data.providers.items():
            # Check if provider is credentialed for ALL facilities
            is_credentialed = all(
                facility in provider.credentialed_facilities
                for facility in shift.facilities
            )
            if is_credentialed:
                eligible.append(provider_name)

        return eligible

    def fill_remaining_slots(self):
        """Fill all empty slots that require coverage"""
        print("\n" + "="*80)
        print("FILLING REMAINING SLOTS")
        print("="*80)

        # Identify slots that need coverage
        empty_slots = []
        for day_idx in range(len(self.schedule_df)):
            day_num = day_idx + 1
            is_weekend = self.schedule_df.loc[day_idx, 'Day of Week'] in ['Saturday', 'Sunday']

            for col in self.shift_columns:
                if pd.isna(self.schedule_df.loc[day_idx, col]):
                    # Check if this slot needs coverage
                    shift_id = col
                    if (shift_id, day_num) in self.data.coverage_required:
                        empty_slots.append((day_idx, day_num, col, is_weekend))

        print(f"\nFound {len(empty_slots)} empty slots that require coverage")

        # Fill each empty slot
        filled_count = 0
        assignment_log = []

        for day_idx, day_num, shift_col, is_weekend in empty_slots:
            shift_type = shift_col.split(' - ')[0].strip()

            # Get eligible providers
            eligible = self.find_eligible_providers(shift_col)

            if not eligible:
                print(f"\n❌ Day {day_num}, {shift_col}: NO ELIGIBLE PROVIDERS")
                assignment_log.append({
                    'day': day_num,
                    'shift': shift_col,
                    'status': 'NO_ELIGIBLE_PROVIDERS'
                })
                continue

            # Score each eligible provider
            provider_scores = []
            for provider in eligible:
                score, explanation = self.calculate_fairness_score(provider, shift_type, is_weekend)
                provider_scores.append((provider, score, explanation))

            # Sort by score (highest first)
            provider_scores.sort(key=lambda x: x[1], reverse=True)

            # Assign best provider
            best_provider, best_score, explanation = provider_scores[0]
            self.schedule_df.loc[day_idx, shift_col] = best_provider

            # Update stats
            self.provider_stats[best_provider]['current_shifts'] += 1
            self.provider_stats[best_provider]['shifts_by_type'][shift_type] += 1
            if is_weekend:
                self.provider_stats[best_provider]['current_weekends'] += 1
            if shift_type == 'PM':
                self.provider_stats[best_provider]['current_pm'] += 1

            filled_count += 1

            # Log assignment
            assignment_log.append({
                'day': day_num,
                'shift': shift_col,
                'provider': best_provider,
                'score': best_score,
                'explanation': explanation,
                'alternatives': len(eligible) - 1
            })

            # Print progress every 10 assignments
            if filled_count % 10 == 0:
                print(f"  Filled {filled_count}/{len(empty_slots)} slots...")

        print(f"\n✅ Successfully filled {filled_count}/{len(empty_slots)} empty slots")

        return assignment_log

    def generate_fairness_report(self):
        """Generate detailed fairness report"""
        print("\n" + "="*80)
        print("FAIRNESS ANALYSIS REPORT")
        print("="*80)

        # Calculate fairness metrics
        fairness_data = []

        for provider_name, stats in self.provider_stats.items():
            contracted = stats['contracted_shifts']
            actual = stats['current_shifts']

            fairness_data.append({
                'Provider': provider_name,
                'Type': stats['contract_type'],
                'Contracted': contracted,
                'Assigned': actual,
                'Utilization': f"{(actual/max(contracted,1)*100):.1f}%",
                'Difference': actual - contracted,
                'Weekend_Contract': stats['contracted_weekends'],
                'Weekend_Actual': stats['current_weekends'],
                'PM_Contract': stats['contracted_pm'],
                'PM_Actual': stats['current_pm']
            })

        df_fairness = pd.DataFrame(fairness_data)
        df_fairness = df_fairness.sort_values('Difference', ascending=False)

        print("\n📊 PROVIDER UTILIZATION SUMMARY:")
        print("-" * 80)

        # Group by utilization levels
        under_80 = df_fairness[df_fairness['Assigned'] < df_fairness['Contracted'] * 0.8]
        optimal = df_fairness[(df_fairness['Assigned'] >= df_fairness['Contracted'] * 0.8) &
                              (df_fairness['Assigned'] <= df_fairness['Contracted'] * 1.2)]
        over_120 = df_fairness[df_fairness['Assigned'] > df_fairness['Contracted'] * 1.2]

        print(f"\n✅ Optimal (80-120% of contract): {len(optimal)} providers")
        if len(optimal) > 0:
            for _, row in optimal.head(5).iterrows():
                print(f"   {row['Provider']:20} {row['Assigned']}/{row['Contracted']} ({row['Utilization']})")

        print(f"\n⚠️  Under-utilized (<80% of contract): {len(under_80)} providers")
        if len(under_80) > 0:
            for _, row in under_80.head(5).iterrows():
                print(f"   {row['Provider']:20} {row['Assigned']}/{row['Contracted']} ({row['Utilization']})")

        print(f"\n⚠️  Over-utilized (>120% of contract): {len(over_120)} providers")
        if len(over_120) > 0:
            for _, row in over_120.head(5).iterrows():
                print(f"   {row['Provider']:20} {row['Assigned']}/{row['Contracted']} ({row['Utilization']})")

        # Fairness metrics
        print("\n📈 FAIRNESS METRICS:")
        print("-" * 80)

        utilizations = df_fairness['Assigned'] / df_fairness['Contracted'].clip(lower=1)

        print(f"Average utilization: {utilizations.mean():.1%}")
        print(f"Standard deviation: {utilizations.std():.1%}")
        print(f"Min utilization: {utilizations.min():.1%}")
        print(f"Max utilization: {utilizations.max():.1%}")

        # Gini coefficient (measure of inequality, 0=perfect equality, 1=maximum inequality)
        sorted_utils = sorted(utilizations)
        n = len(sorted_utils)
        cumsum = np.cumsum(sorted_utils)
        gini = (2 * sum((i+1) * util for i, util in enumerate(sorted_utils))) / (n * sum(sorted_utils)) - (n+1)/n
        print(f"Gini coefficient: {gini:.3f} (0=perfect equality, 1=maximum inequality)")

        return df_fairness

    def save_completed_schedule(self, output_path: str = 'completed_schedule.xlsx'):
        """Save the completed schedule"""
        self.schedule_df.to_excel(output_path, index=False)
        print(f"\n✅ Completed schedule saved to: {output_path}")

        # Also save detailed report
        report_path = output_path.replace('.xlsx', '_report.json')
        report_data = {
            'provider_stats': self.provider_stats,
            'fairness_metrics': {
                'filled_slots': len([1 for col in self.shift_columns
                                    for val in self.schedule_df[col]
                                    if pd.notna(val)]),
                'total_slots': len(self.shift_columns) * len(self.schedule_df)
            }
        }

        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        print(f"📊 Detailed report saved to: {report_path}")

def main():
    """Main execution"""
    print("Starting fairness-based schedule completion...")

    # Initialize optimizer
    optimizer = FairnessOptimizer()

    # Fill remaining slots
    assignment_log = optimizer.fill_remaining_slots()

    # Generate fairness report
    fairness_df = optimizer.generate_fairness_report()

    # Save completed schedule
    optimizer.save_completed_schedule('completed_schedule.xlsx')

    # Save assignment log for transparency
    log_df = pd.DataFrame(assignment_log)
    log_df.to_csv('assignment_decisions.csv', index=False)
    print(f"📝 Assignment decisions saved to: assignment_decisions.csv")

    print("\n" + "="*80)
    print("SCHEDULE COMPLETION FINISHED")
    print("="*80)

if __name__ == "__main__":
    main()