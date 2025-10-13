#!/usr/bin/env python3
"""
Main CLI script for Physician Scheduling System
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

from data_loader import DataLoader
from scheduler import PhysicianScheduler
from output_generator import OutputGenerator


def main():
    parser = argparse.ArgumentParser(
        description='Physician Scheduling System - MILP-based optimizer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate schedule for January 2025 (31 days)
  python main.py --days 31 --start-date 2025-01-01

  # Generate schedule with longer solver time
  python main.py --days 31 --time-limit 300

  # Specify custom data directory and output file
  python main.py --data-dir ../data --output output/my_schedule.xlsx

  # Run diagnostics only (no scheduling)
  python main.py --diagnose-only
        """
    )

    parser.add_argument(
        '--days',
        type=int,
        default=31,
        help='Number of days to schedule (default: 31)'
    )

    parser.add_argument(
        '--start-date',
        type=str,
        default=None,
        help='Start date for schedule (YYYY-MM-DD format, default: today)'
    )

    parser.add_argument(
        '--data-dir',
        type=str,
        default='../data',
        help='Directory containing input Excel files (default: ../data)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='output/generated_schedule.xlsx',
        help='Output Excel file name (default: output/generated_schedule.xlsx)'
    )

    parser.add_argument(
        '--report',
        type=str,
        default='output/schedule_report.txt',
        help='Output report file name (default: output/schedule_report.txt)'
    )

    parser.add_argument(
        '--time-limit',
        type=int,
        default=120,
        help='Maximum solver time in seconds (default: 120)'
    )

    parser.add_argument(
        '--method',
        type=str,
        default='milp',
        choices=['milp', 'rolling-window'],
        help='Scheduling method: milp (single large MILP) or rolling-window (decomposed) (default: milp)'
    )

    parser.add_argument(
        '--window-size',
        type=int,
        default=4,
        help='Days per window for rolling-window method (default: 4)'
    )

    parser.add_argument(
        '--diagnose-only',
        action='store_true',
        help='Run diagnostics only, do not generate schedule'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Print banner
    print("=" * 80)
    print("PHYSICIAN SCHEDULING SYSTEM")
    print("MILP-based Optimization with Constraint Satisfaction")
    print("=" * 80)
    print()

    # Parse start date
    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        except ValueError:
            print(f"❌ Error: Invalid date format '{args.start_date}'. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    print(f"Configuration:")
    print(f"  Schedule period: {args.days} days starting {start_date.strftime('%Y-%m-%d')}")
    print(f"  Method: {args.method}")
    if args.method == 'rolling-window':
        print(f"  Window size: {args.window_size} days")
    print(f"  Data directory: {args.data_dir}")
    print(f"  Solver time limit: {args.time_limit} seconds")
    print(f"  Output file: {args.output}")
    print(f"  Report file: {args.report}")
    print()

    # Validate data directory
    data_path = Path(args.data_dir)
    if not data_path.exists():
        print(f"❌ Error: Data directory '{args.data_dir}' does not exist")
        sys.exit(1)

    # Check required files
    required_files = [
        'Provider contract.xlsx',
        'Provider Credentialing.xlsx',
        'Provider Availability.xlsx',
        'Facility volume.xlsx',
        'Facility Coverage.xlsx',
        'Sample Schedule.xlsx'
    ]

    missing_files = []
    for filename in required_files:
        if not (data_path / filename).exists():
            missing_files.append(filename)

    if missing_files:
        print(f"❌ Error: Missing required data files in '{args.data_dir}':")
        for filename in missing_files:
            print(f"  - {filename}")
        sys.exit(1)

    # Run diagnostics if requested
    if args.diagnose_only:
        print("Running diagnostics...")
        print()
        run_diagnostics(args.data_dir, args.days, start_date)
        return

    try:
        # Step 1: Load data
        print("Step 1: Loading data...")
        print("-" * 80)
        loader = DataLoader(data_dir=args.data_dir)
        data = loader.load_all_data(num_days=args.days, start_date=start_date)
        print(f"✓ Loaded {len(data.providers)} providers")
        print(f"✓ Loaded {len(data.shifts)} shifts")
        print(f"✓ Scheduling for {len(data.days)} days")
        print()

        # Step 2: Run feasibility check
        print("Step 2: Feasibility analysis...")
        print("-" * 80)
        from feasibility_checker import FeasibilityChecker
        checker = FeasibilityChecker(data)
        is_feasible, issues = checker.check_feasibility()

        if not is_feasible:
            print("\n❌ Problem appears infeasible. Aborting.")
            sys.exit(1)
        print()

        # Step 3: Solve based on method
        if args.method == 'rolling-window':
            print("Step 3: Solving with rolling window method...")
            print("-" * 80)
            from rolling_window_scheduler import RollingWindowScheduler
            scheduler = RollingWindowScheduler(
                data,
                window_size=args.window_size,
                overlap=1,
                time_limit_per_window=args.time_limit
            )
            success = scheduler.solve()

            if not success:
                print("❌ Failed to find feasible solution")
                sys.exit(1)

            schedule = scheduler.get_schedule()

        else:  # MILP method
            print("Step 3: Building monolithic MILP model...")
            print("-" * 80)
            scheduler = PhysicianScheduler(data, time_limit_seconds=args.time_limit)
            print()

            print("Step 4: Adding constraints...")
            print("-" * 80)
            scheduler.add_hard_constraints()
            print()

            print("Step 5: Building objective function...")
            print("-" * 80)
            scheduler.build_objective()
            print()

            print("Step 6: Solving optimization problem...")
            print("-" * 80)
            success = scheduler.solve()
            print()

            if not success:
                print("❌ Failed to find feasible solution")
                print("   Try running with --method rolling-window")
                sys.exit(1)

            schedule = scheduler.get_schedule()

        # Generate outputs
        print("\nGenerating outputs...")
        print("-" * 80)
        generator = OutputGenerator(data, schedule)

        # Generate Excel file
        generator.generate_excel(args.output)

        # Generate text report
        generator.generate_summary_report(args.report)

        # Print summary to console (only for MILP method which has print_summary)
        if args.method == 'milp' and hasattr(scheduler, 'print_summary'):
            print()
            scheduler.print_summary()

        print()
        print("=" * 80)
        print("✓ SCHEDULING COMPLETE")
        print("=" * 80)
        print(f"  Schedule: {args.output}")
        print(f"  Report: {args.report}")
        print()

    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def run_diagnostics(data_dir: str, num_days: int, start_date: datetime):
    """Run diagnostic checks on the data"""
    from diagnose_infeasibility import diagnose_data_issues

    # Temporarily set data directory for diagnostics
    import data_loader
    original_init = data_loader.DataLoader.__init__

    def patched_init(self, data_dir_arg=None):
        original_init(self, data_dir_arg or data_dir)

    data_loader.DataLoader.__init__ = patched_init

    try:
        diagnose_data_issues()
    finally:
        data_loader.DataLoader.__init__ = original_init


if __name__ == '__main__':
    main()
