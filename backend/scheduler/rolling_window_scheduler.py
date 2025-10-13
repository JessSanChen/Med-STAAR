"""
Rolling Window Scheduler for Physician Scheduling System
Decomposes the scheduling problem into smaller overlapping windows
"""
import pulp
from typing import Dict, List, Set, Tuple
from data_loader import SchedulingData
from feasibility_checker import FeasibilityChecker


class RollingWindowScheduler:
    """Schedules physicians using a rolling window approach with overlap"""

    def __init__(self, data: SchedulingData, window_size: int = 4, overlap: int = 1,
                 time_limit_per_window: int = 60):
        """
        Initialize rolling window scheduler.

        Args:
            data: SchedulingData object
            window_size: Number of days per window (default: 4)
            overlap: Number of days overlap between windows (default: 1)
            time_limit_per_window: Solver time limit per window in seconds
        """
        self.data = data
        self.window_size = window_size
        self.overlap = overlap
        self.time_limit = time_limit_per_window

        # State tracking across windows
        self.assignments = {}  # (provider, shift_id, day) -> 1
        self.provider_shift_counts = {p: 0 for p in data.providers.keys()}  # Cumulative shifts
        self.provider_consecutive_history = {}  # (provider, shift_type) -> list of days worked
        self.locked_assignments = set()  # Set of (provider, shift_id, day) that are fixed

        # Feasibility checker for eligible providers
        self.feasibility_checker = FeasibilityChecker(data)
        self.feasibility_checker._compute_eligible_providers()

        print(f"Rolling Window Scheduler initialized:")
        print(f"  Window size: {window_size} days")
        print(f"  Overlap: {overlap} days")
        print(f"  Total days: {len(data.days)}")

    def solve(self) -> bool:
        """
        Solve the scheduling problem using rolling windows.

        Returns:
            True if successful, False otherwise
        """
        print("\n" + "="*80)
        print("ROLLING WINDOW SCHEDULING")
        print("="*80)

        # Generate windows
        windows = self._generate_windows()
        print(f"\nGenerated {len(windows)} windows:")
        for i, (start, end) in enumerate(windows):
            print(f"  Window {i+1}: Days {start}-{end}")

        # Solve each window
        for window_idx, (start_day, end_day) in enumerate(windows):
            print(f"\n" + "-"*80)
            print(f"WINDOW {window_idx + 1}/{len(windows)}: Days {start_day}-{end_day}")
            print("-"*80)

            success = self._solve_window(start_day, end_day, window_idx)

            if not success:
                print(f"\n❌ Failed to solve window {window_idx + 1}")
                return False

            # Lock overlap region for next window
            if window_idx < len(windows) - 1:
                self._lock_overlap_region(start_day, end_day)

        print("\n" + "="*80)
        print("✓ ALL WINDOWS SOLVED SUCCESSFULLY")
        print("="*80)

        return True

    def _generate_windows(self) -> List[Tuple[int, int]]:
        """Generate overlapping windows covering all days"""
        windows = []
        current_start = 0

        while current_start < len(self.data.days):
            current_end = min(current_start + self.window_size - 1, len(self.data.days) - 1)
            windows.append((current_start, current_end))

            # Move to next window, accounting for overlap
            current_start = current_end - self.overlap + 1

            # If next window would be tiny, merge with current
            if current_start < len(self.data.days) and len(self.data.days) - current_start <= self.overlap:
                break

        return windows

    def _solve_window(self, start_day: int, end_day: int, window_idx: int) -> bool:
        """
        Solve scheduling for a specific window.

        Args:
            start_day: First day of window
            end_day: Last day of window
            window_idx: Index of current window

        Returns:
            True if solved successfully
        """
        window_days = list(range(start_day, end_day + 1))
        print(f"  Window days: {window_days}")

        # Create MILP for this window
        problem = pulp.LpProblem(f"Window_{window_idx}", pulp.LpMinimize)

        # Decision variables for this window only
        x = {}  # x[provider, shift_id, day] for days in window
        working_shift_type = {}  # working_shift_type[provider, shift_type, day]

        # Create variables
        print(f"  Creating variables...")
        created_vars = 0
        locked_vars = 0

        for day in window_days:
            for shift_id in self.data.shifts.keys():
                if (shift_id, day) not in self.data.coverage_required:
                    continue

                # Get eligible providers for this slot
                eligible_providers = self.feasibility_checker.get_eligible_providers_for_slot(shift_id, day)

                for provider_name in eligible_providers:
                    if (provider_name, shift_id, day) in self.locked_assignments:
                        # This assignment is locked from previous window
                        locked_vars += 1
                        continue

                    var_name = f"x_{provider_name}_{shift_id}_{day}".replace(" ", "_").replace(",", "").replace("-", "_")
                    x[provider_name, shift_id, day] = pulp.LpVariable(var_name, cat='Binary')
                    created_vars += 1

        # Create shift type indicators
        for provider_name in self.data.providers.keys():
            for shift_type in ['MD1', 'MD2', 'PM']:
                for day in window_days:
                    var_name = f"w_{provider_name}_{shift_type}_{day}".replace(" ", "_")
                    working_shift_type[provider_name, shift_type, day] = pulp.LpVariable(var_name, cat='Binary')

        print(f"    Created {created_vars} assignment variables ({locked_vars} locked from previous window)")

        # Add constraints
        print(f"  Adding constraints...")

        # 1. Link shift type indicators to assignments
        for provider_name in self.data.providers.keys():
            for shift_type in ['MD1', 'MD2', 'PM']:
                for day in window_days:
                    shifts_of_type = [
                        shift_id for shift_id, shift in self.data.shifts.items()
                        if shift.shift_type == shift_type
                    ]

                    available_vars = [
                        x[provider_name, shift_id, day]
                        for shift_id in shifts_of_type
                        if (provider_name, shift_id, day) in x
                    ]

                    # Account for locked assignments
                    locked_count = sum(
                        1 for shift_id in shifts_of_type
                        if (provider_name, shift_id, day) in self.locked_assignments
                    )

                    if not available_vars and locked_count == 0:
                        problem += working_shift_type[provider_name, shift_type, day] == 0
                    elif available_vars:
                        total = pulp.lpSum(available_vars) + locked_count
                        problem += working_shift_type[provider_name, shift_type, day] >= pulp.lpSum(available_vars) / len(available_vars)
                        problem += working_shift_type[provider_name, shift_type, day] <= total
                    elif locked_count > 0:
                        problem += working_shift_type[provider_name, shift_type, day] == 1

        # 2. Coverage: exactly 1 provider per required slot
        for day in window_days:
            for shift_id in self.data.shifts.keys():
                if (shift_id, day) not in self.data.coverage_required:
                    continue

                available_vars = [
                    x[provider_name, shift_id, day]
                    for provider_name in self.data.providers.keys()
                    if (provider_name, shift_id, day) in x
                ]

                # Check if this slot is locked
                locked_provider = None
                for provider_name in self.data.providers.keys():
                    if (provider_name, shift_id, day) in self.locked_assignments:
                        locked_provider = provider_name
                        break

                if locked_provider:
                    # Slot is already filled by locked assignment - ensure no other assignments
                    if available_vars:
                        problem += pulp.lpSum(available_vars) == 0
                elif available_vars:
                    # Must assign exactly one provider
                    problem += pulp.lpSum(available_vars) == 1
                else:
                    # No eligible providers and not locked - infeasible
                    print(f"    ⚠️  No eligible providers for {shift_id} on day {day}")
                    return False

        # 3. One shift type per provider per day
        for provider_name in self.data.providers.keys():
            for day in window_days:
                total_shift_types = pulp.lpSum([
                    working_shift_type[provider_name, shift_type, day]
                    for shift_type in ['MD1', 'MD2', 'PM']
                ])
                problem += total_shift_types <= 1

        # 4. Cumulative shift count constraints (considering previous windows)
        for provider_name, provider in self.data.providers.items():
            # Count shifts in this window
            window_shifts = pulp.lpSum([
                working_shift_type[provider_name, shift_type, day]
                for shift_type in ['MD1', 'MD2', 'PM']
                for day in window_days
            ])

            # Add shifts from previous windows
            previous_shifts = self.provider_shift_counts[provider_name]

            # Total shifts must respect contract
            if provider.contract_type == 'FT':
                # FT: exactly equal (but only enforce if we're in last window covering all days)
                if end_day == max(self.data.days):
                    problem += window_shifts + previous_shifts == provider.total_shift_count
                else:
                    # For intermediate windows, just don't exceed
                    problem += window_shifts + previous_shifts <= provider.total_shift_count
            else:  # IC
                problem += window_shifts + previous_shifts <= provider.total_shift_count

        # 5. One provider per facility group per day
        for day in window_days:
            for shift_id in self.data.shifts.keys():
                if (shift_id, day) not in self.data.coverage_required:
                    continue

                available_vars = [
                    x[provider_name, shift_id, day]
                    for provider_name in self.data.providers.keys()
                    if (provider_name, shift_id, day) in x
                ]

                # Check for locked assignment
                has_locked = any(
                    (provider_name, shift_id, day) in self.locked_assignments
                    for provider_name in self.data.providers.keys()
                )

                if available_vars:
                    if has_locked:
                        # Already has locked assignment - no new assignments allowed
                        problem += pulp.lpSum(available_vars) == 0
                    else:
                        # At most one provider
                        problem += pulp.lpSum(available_vars) <= 1

        print(f"    Added {len(problem.constraints)} constraints")

        # Build objective: minimize soft constraint violations
        objective_terms = []

        # Penalize availability violations
        for provider_name, provider in self.data.providers.items():
            for day in window_days:
                if not provider.availability.get(day, True):
                    for shift_type in ['MD1', 'MD2', 'PM']:
                        objective_terms.append(1000.0 * working_shift_type[provider_name, shift_type, day])

        # Penalize preference violations
        for provider_name, provider in self.data.providers.items():
            for shift_id, shift in self.data.shifts.items():
                if shift.shift_type not in provider.shift_preference:
                    for day in window_days:
                        if (provider_name, shift_id, day) in x:
                            objective_terms.append(100.0 * x[provider_name, shift_id, day])

        if objective_terms:
            problem += pulp.lpSum(objective_terms)
        else:
            problem += 0

        # Solve
        print(f"  Solving window MILP...")
        solver = pulp.PULP_CBC_CMD(
            msg=1,
            timeLimit=self.time_limit,
            gapRel=0.05,
            threads=0
        )

        problem.solve(solver)

        status = pulp.LpStatus[problem.status]
        print(f"  Solution status: {status}")

        if problem.status not in [pulp.LpStatusOptimal, pulp.LpStatusNotSolved]:
            print(f"  ❌ Failed to find feasible solution for window")
            return False

        # Extract solution
        print(f"  Extracting solution...")
        assignments_count = 0

        for (provider_name, shift_id, day), var in x.items():
            if var.varValue and var.varValue > 0.5:
                self.assignments[(provider_name, shift_id, day)] = 1
                assignments_count += 1

        # Update provider shift counts
        for provider_name in self.data.providers.keys():
            window_shift_count = 0
            for shift_type in ['MD1', 'MD2', 'PM']:
                for day in window_days:
                    if working_shift_type[provider_name, shift_type, day].varValue and \
                       working_shift_type[provider_name, shift_type, day].varValue > 0.5:
                        window_shift_count += 1

            self.provider_shift_counts[provider_name] += window_shift_count

        print(f"  ✓ Window solved: {assignments_count} assignments made")

        return True

    def _lock_overlap_region(self, start_day: int, end_day: int):
        """Lock assignments in the overlap region for next window"""
        # Lock assignments in last 'overlap' days of current window
        lock_start = end_day - self.overlap + 1

        for day in range(lock_start, end_day + 1):
            for (provider_name, shift_id, assign_day), value in self.assignments.items():
                if assign_day == day:
                    self.locked_assignments.add((provider_name, shift_id, day))

        print(f"  Locked {len([d for d in range(lock_start, end_day + 1)])} day(s) for overlap")

    def get_schedule(self) -> Dict[int, Dict[str, List[str]]]:
        """
        Convert assignments to schedule format.

        Returns:
            schedule dict: day -> shift_id -> [provider_names]
        """
        schedule = {}

        for day in self.data.days:
            schedule[day] = {}

            for shift_id in self.data.shifts.keys():
                providers = []
                for provider_name in self.data.providers.keys():
                    if (provider_name, shift_id, day) in self.assignments or \
                       (provider_name, shift_id, day) in self.locked_assignments:
                        providers.append(provider_name)

                if providers:
                    schedule[day][shift_id] = providers

        return schedule
