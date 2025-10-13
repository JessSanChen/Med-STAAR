"""
Output Generator for Physician Scheduling System
Formats schedule into Excel file matching sample structure
"""
import pandas as pd
from typing import Dict, List
from datetime import datetime
from data_loader import SchedulingData


class OutputGenerator:
    """Generates formatted schedule output"""

    def __init__(self, data: SchedulingData, schedule: Dict[int, Dict[str, List[str]]]):
        """
        Initialize output generator.

        Args:
            data: SchedulingData object containing scheduling information
            schedule: Dictionary mapping day -> shift_id -> list of provider names
        """
        self.data = data
        self.schedule = schedule

    def generate_excel(self, output_path: str = 'output/generated_schedule.xlsx'):
        """
        Generate Excel file matching sample schedule format.

        Args:
            output_path: Path for output Excel file
        """
        print(f"\nGenerating schedule Excel file: {output_path}")

        # Create DataFrame structure
        rows = []

        for day_idx in self.data.days:
            date_obj = self.data.day_index_to_date[day_idx]
            day_of_week = date_obj.strftime('%a')  # Mon, Tue, Wed, etc.
            day_of_month = date_obj.day

            row = {
                'Day of Week': day_of_week,
                'Day Of Month': day_of_month
            }

            # Fill in each shift column
            for shift_id in sorted(self.data.shifts.keys()):
                if day_idx in self.schedule and shift_id in self.schedule[day_idx]:
                    providers = self.schedule[day_idx][shift_id]
                    # Join multiple providers with comma if more than one
                    row[shift_id] = ', '.join(providers) if providers else ''
                else:
                    row[shift_id] = ''  # Empty cell for uncovered shift

            rows.append(row)

        # Create DataFrame
        df = pd.DataFrame(rows)

        # Reorder columns to match sample: Day columns first, then shifts
        date_columns = ['Day of Week', 'Day Of Month']
        shift_columns = sorted(self.data.shifts.keys())
        df = df[date_columns + shift_columns]

        # Write to Excel
        df.to_excel(output_path, index=False, engine='openpyxl')

        print(f"✓ Schedule written to {output_path}")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {len(df.columns)}")

        return df

    def generate_summary_report(self, output_path: str = 'output/schedule_report.txt'):
        """
        Generate a text summary report of the schedule.

        Args:
            output_path: Path for output text file
        """
        print(f"\nGenerating schedule summary report: {output_path}")

        with open(output_path, 'w') as f:
            f.write("="*80 + "\n")
            f.write("PHYSICIAN SCHEDULING REPORT\n")
            f.write("="*80 + "\n\n")

            # Provider workload summary
            f.write("1. PROVIDER WORKLOAD SUMMARY\n")
            f.write("-"*80 + "\n")

            provider_stats = self._calculate_provider_stats()

            f.write(f"{'Provider':<25} {'Contracted':>12} {'Assigned':>12} {'Utilization':>12}\n")
            f.write("-"*80 + "\n")

            for provider_name in sorted(provider_stats.keys()):
                stats = provider_stats[provider_name]
                contracted = stats['contracted']
                assigned = stats['assigned']
                utilization = (assigned / contracted * 100) if contracted > 0 else 0

                f.write(f"{provider_name:<25} {contracted:>12} {assigned:>12} {utilization:>11.1f}%\n")

            # Overall statistics
            f.write("\n\n2. OVERALL STATISTICS\n")
            f.write("-"*80 + "\n")

            total_slots = len(self.data.shifts) * len(self.data.days)
            total_assignments = sum(len(providers)
                                   for day_shifts in self.schedule.values()
                                   for providers in day_shifts.values())
            coverage_pct = (total_assignments / total_slots * 100) if total_slots > 0 else 0

            f.write(f"Total shift slots: {total_slots}\n")
            f.write(f"Filled slots: {total_assignments}\n")
            f.write(f"Coverage: {coverage_pct:.1f}%\n")
            f.write(f"Uncovered slots: {total_slots - total_assignments}\n")

            # Shift type breakdown
            f.write("\n\n3. SHIFT TYPE BREAKDOWN\n")
            f.write("-"*80 + "\n")

            shift_type_stats = self._calculate_shift_type_stats()

            f.write(f"{'Shift Type':<15} {'Slots':>10} {'Filled':>10} {'Coverage':>12}\n")
            f.write("-"*80 + "\n")

            for shift_type in ['MD1', 'MD2', 'PM']:
                stats = shift_type_stats.get(shift_type, {'slots': 0, 'filled': 0})
                slots = stats['slots']
                filled = stats['filled']
                coverage = (filled / slots * 100) if slots > 0 else 0

                f.write(f"{shift_type:<15} {slots:>10} {filled:>10} {coverage:>11.1f}%\n")

            # Weekend coverage
            f.write("\n\n4. WEEKEND COVERAGE\n")
            f.write("-"*80 + "\n")

            weekend_stats = self._calculate_weekend_stats()
            f.write(f"Weekend days: {weekend_stats['days']}\n")
            f.write(f"Weekend shift slots: {weekend_stats['slots']}\n")
            f.write(f"Weekend assignments: {weekend_stats['assignments']}\n")
            f.write(f"Weekend coverage: {weekend_stats['coverage_pct']:.1f}%\n")

            # Constraint violations
            f.write("\n\n5. CONSTRAINT COMPLIANCE\n")
            f.write("-"*80 + "\n")

            violations = self._check_constraint_violations()

            if violations:
                for violation in violations:
                    f.write(f"⚠️  {violation}\n")
            else:
                f.write("✓ All P1 constraints satisfied\n")

        print(f"✓ Report written to {output_path}")

    def _calculate_provider_stats(self) -> Dict:
        """Calculate statistics for each provider"""
        stats = {}

        for provider_name, provider in self.data.providers.items():
            # Count unique (shift_type, day) pairs where provider is working
            # A "shift" = working any facility groups of a shift TYPE on a given day
            shift_type_days = set()

            for day_idx, day_shifts in self.schedule.items():
                for shift_id, providers in day_shifts.items():
                    if provider_name in providers:
                        # Get shift type for this facility group
                        shift_type = self.data.shifts[shift_id].shift_type
                        shift_type_days.add((shift_type, day_idx))

            assigned = len(shift_type_days)

            stats[provider_name] = {
                'contracted': provider.total_shift_count,
                'assigned': assigned,
                'contract_type': provider.contract_type
            }

        return stats

    def _calculate_shift_type_stats(self) -> Dict:
        """Calculate statistics by shift type"""
        stats = {}

        for shift_type in ['MD1', 'MD2', 'PM']:
            # Count total slots
            shifts_of_type = [
                shift_id for shift_id, shift in self.data.shifts.items()
                if shift.shift_type == shift_type
            ]
            slots = len(shifts_of_type) * len(self.data.days)

            # Count filled slots
            filled = 0
            for day_idx in self.data.days:
                if day_idx in self.schedule:
                    for shift_id in shifts_of_type:
                        if shift_id in self.schedule[day_idx]:
                            filled += len(self.schedule[day_idx][shift_id])

            stats[shift_type] = {
                'slots': slots,
                'filled': filled
            }

        return stats

    def _calculate_weekend_stats(self) -> Dict:
        """Calculate weekend coverage statistics"""
        weekend_days = len(self.data.weekends)
        weekend_slots = len(self.data.shifts) * weekend_days

        weekend_assignments = 0
        for day_idx in self.data.weekends:
            if day_idx in self.schedule:
                for providers in self.schedule[day_idx].values():
                    weekend_assignments += len(providers)

        coverage_pct = (weekend_assignments / weekend_slots * 100) if weekend_slots > 0 else 0

        return {
            'days': weekend_days,
            'slots': weekend_slots,
            'assignments': weekend_assignments,
            'coverage_pct': coverage_pct
        }

    def _check_constraint_violations(self) -> List[str]:
        """Check for any constraint violations in the schedule"""
        violations = []

        provider_stats = self._calculate_provider_stats()

        # Check FT provider exact match
        for provider_name, stats in provider_stats.items():
            if stats['contract_type'] == 'FT':
                if stats['assigned'] != stats['contracted']:
                    violations.append(
                        f"FT provider {provider_name}: assigned {stats['assigned']} "
                        f"instead of {stats['contracted']} shifts"
                    )

            # Check IC provider max
            elif stats['contract_type'] == 'IC':
                if stats['assigned'] > stats['contracted']:
                    violations.append(
                        f"IC provider {provider_name}: assigned {stats['assigned']} "
                        f"exceeds max {stats['contracted']} shifts"
                    )

        return violations

    def print_daily_schedule(self, day_idx: int = None):
        """
        Print schedule for a specific day (for debugging/viewing).

        Args:
            day_idx: Day index to print (default: first day with assignments)
        """
        if day_idx is None:
            # Find first day with assignments
            day_idx = min(self.schedule.keys()) if self.schedule else 0

        if day_idx not in self.schedule:
            print(f"No assignments for day {day_idx}")
            return

        date_obj = self.data.day_index_to_date[day_idx]
        print(f"\n{'='*80}")
        print(f"Schedule for {date_obj.strftime('%A, %B %d, %Y')}")
        print(f"{'='*80}")

        for shift_id, providers in sorted(self.schedule[day_idx].items()):
            shift = self.data.shifts[shift_id]
            provider_str = ', '.join(providers) if providers else '(uncovered)'
            print(f"\n{shift_id}")
            print(f"  Providers: {provider_str}")
            print(f"  Facilities: {', '.join(shift.facilities[:3])}{'...' if len(shift.facilities) > 3 else ''}")


if __name__ == '__main__':
    # Test output generation
    from data_loader import DataLoader
    from scheduler import PhysicianScheduler

    print("Loading data...")
    loader = DataLoader()
    data = loader.load_all_data(num_days=31)

    print("\nSolving schedule...")
    scheduler = PhysicianScheduler(data, time_limit_seconds=60)
    scheduler.add_hard_constraints()
    scheduler.build_objective()
    success = scheduler.solve()

    if success:
        schedule = scheduler.get_schedule()

        print("\nGenerating outputs...")
        generator = OutputGenerator(data, schedule)

        # Generate Excel file
        generator.generate_excel('output/')

        # Generate text report
        generator.generate_summary_report('output/schedule_report.txt')

        # Print first day's schedule
        generator.print_daily_schedule(0)

        print("\n✓ Output generation complete!")
