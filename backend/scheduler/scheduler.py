"""
MILP-based Physician Scheduler
Core optimization model using PuLP
"""
import pulp
import numpy as np
from typing import Dict, List, Tuple, Set
from data_loader import SchedulingData, Provider, Shift
from datetime import datetime


class PhysicianScheduler:
    """Mixed-Integer Linear Programming scheduler for physician assignments"""

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize variable/constraint names for PuLP"""
        return name.replace(" ", "_").replace(",", "").replace("-", "_")

    def __init__(self, data: SchedulingData, time_limit_seconds: int = 300):
        """
        Initialize the scheduler with data and create the optimization model.

        Args:
            data: SchedulingData object containing all scheduling information
            time_limit_seconds: Maximum time for solver to run
        """
        self.data = data
        self.time_limit = time_limit_seconds

        # Create the optimization problem (minimization)
        self.problem = pulp.LpProblem("Physician_Scheduling", pulp.LpMinimize)

        # Decision variables
        # x[provider_name, shift_id, day] = 1 if assigned to specific facility group
        self.x = {}
        # working_shift_type[provider, shift_type, day] = 1 if working ANY facility of that type
        self.working_shift_type = {}
        # Note: consecutive_days variables removed - using rolling window constraints instead

        # Soft constraint violation variables
        self.preference_violation = {}  # Shift type preference violations
        self.availability_violation = {}  # Scheduling on unavailable days
        self.weekend_over = {}  # Weekend shifts over limit
        self.pm_over = {}  # PM shifts over limit

        # Solution storage
        self.solution = None
        self.is_solved = False

        print("Creating decision variables...")
        self._create_variables()

    def _create_variables(self):
        """Create all decision variables for the MILP model"""

        # Primary assignment variables: x[p, s, d] ∈ {0, 1}
        # Only create variables for feasible (provider, shift, day) combinations
        print(f"  Creating assignment variables for {len(self.data.providers)} providers, "
              f"{len(self.data.shifts)} shifts, {len(self.data.days)} days...")

        pruned_count = 0
        created_count = 0

        for provider_name, provider in self.data.providers.items():
            for shift_id, shift in self.data.shifts.items():
                # Check if provider is credentialed for this shift
                is_credentialed = all(
                    facility in provider.credentialed_facilities
                    for facility in shift.facilities
                )

                if not is_credentialed:
                    # Don't create variable - provider can never work this shift
                    pruned_count += len(self.data.days)
                    continue

                for day in self.data.days:
                    # Check if this shift needs coverage on this day
                    if (shift_id, day) not in self.data.coverage_required:
                        # Don't create variable - shift doesn't need coverage this day
                        pruned_count += 1
                        continue

                    var_name = f"x_{provider_name}_{shift_id}_{day}"
                    var_name = self._sanitize_name(var_name)
                    self.x[provider_name, shift_id, day] = pulp.LpVariable(
                        var_name, cat='Binary'
                    )
                    created_count += 1

        print(
            f"    Created {created_count} variables, pruned {pruned_count} impossible assignments")

        # Auxiliary variables: is provider working this shift TYPE on this day?
        print("  Creating shift type working indicators...")
        for provider_name in self.data.providers.keys():
            for shift_type in ['MD1', 'MD2', 'PM']:
                for day in self.data.days:
                    var_name = f"working_{provider_name}_{shift_type}_{day}"
                    var_name = self._sanitize_name(var_name)
                    self.working_shift_type[provider_name, shift_type, day] = pulp.LpVariable(
                        var_name, cat='Binary'
                    )

        # Preference violation variables (for soft constraints)
        print("  Creating preference violation variables...")
        for provider_name in self.data.providers.keys():
            provider = self.data.providers[provider_name]
            for shift_id in self.data.shifts.keys():
                shift = self.data.shifts[shift_id]
                # Only create violation variable if shift type is NOT in preferences
                if shift.shift_type not in provider.shift_preference:
                    for day in self.data.days:
                        var_name = self._sanitize_name(
                            f"pref_viol_{provider_name}_{shift_id}_{day}")
                        self.preference_violation[provider_name, shift_id, day] = pulp.LpVariable(
                            var_name, cat='Binary'
                        )

        # Availability violation variables (soft constraint)
        print("  Creating availability violation variables...")
        for provider_name in self.data.providers.keys():
            for day in self.data.days:
                var_name = self._sanitize_name(
                    f"avail_viol_{provider_name}_{day}")
                self.availability_violation[provider_name, day] = pulp.LpVariable(
                    var_name, cat='Binary'
                )

        # Weekend/PM over-limit variables (soft constraints)
        print("  Creating weekend/PM over-limit variables...")
        for provider_name in self.data.providers.keys():
            var_name_wk = self._sanitize_name(f"weekend_over_{provider_name}")
            var_name_pm = self._sanitize_name(f"pm_over_{provider_name}")
            self.weekend_over[provider_name] = pulp.LpVariable(
                var_name_wk, lowBound=0, cat='Continuous')
            self.pm_over[provider_name] = pulp.LpVariable(
                var_name_pm, lowBound=0, cat='Continuous')

        total_vars = (len(self.x) + len(self.working_shift_type) +
                      len(self.preference_violation) +
                      len(self.availability_violation) + len(self.weekend_over) + len(self.pm_over))
        print(f"  Total variables created: {total_vars}")

    def add_hard_constraints(self):
        """Add all P1 (hard) constraints that must be satisfied"""
        print("\nAdding P1 (hard) constraints...")
        print("  Hard: Credentialing, Contract coverage, Shift counts, Consecutive shifts,")
        print("        One shift type per provider per day, One provider per facility group per day,")
        print("        Volume constraints (min/max patient volume per shift type)")
        print("  Soft: Availability, Weekend limits, PM limits, Preferences")

        self._link_shift_type_indicators()
        self._add_credentialing_constraints()
        self._add_one_shift_type_per_day_constraint()
        self._add_one_provider_per_facility_group_constraint()
        self._add_shift_count_constraints()
        self._add_coverage_constraints()
        self._add_consecutive_shift_constraints()
        self._add_volume_constraints()  # Add the new volume constraints

        # Link soft constraint violation variables
        self._link_availability_violations()
        self._link_weekend_pm_violations()
        self._link_preference_violations()

        print(f"Total constraints added: {len(self.problem.constraints)}")

    def _link_shift_type_indicators(self):
        """Link working_shift_type indicators to actual facility assignments"""
        print("  Linking shift type indicators to assignments...")
        count = 0

        for provider_name in self.data.providers.keys():
            for shift_type in ['MD1', 'MD2', 'PM']:
                # Get all shifts of this type
                shifts_of_type = [
                    shift_id for shift_id, shift in self.data.shifts.items()
                    if shift.shift_type == shift_type
                ]

                for day in self.data.days:
                    # Sum of all facility assignments for this shift type on this day
                    # Only include variables that were created (not pruned)
                    available_vars = [
                        self.x[provider_name, shift_id, day]
                        for shift_id in shifts_of_type
                        if (provider_name, shift_id, day) in self.x
                    ]

                    if not available_vars:
                        # No feasible assignments for this provider/shift type/day
                        # Force working_shift_type to 0
                        self.problem += (
                            self.working_shift_type[provider_name,
                                                    shift_type, day] == 0,
                            self._sanitize_name(
                                f"link_none_{provider_name}_{shift_type}_{day}")
                        )
                        count += 1
                        continue

                    total_assignments = pulp.lpSum(available_vars)

                    # If any assignment exists, working_shift_type must be 1
                    # working_shift_type[p, st, d] >= x[p, s, d] for all s of type st
                    for shift_id in shifts_of_type:
                        if (provider_name, shift_id, day) in self.x:
                            self.problem += (
                                self.working_shift_type[provider_name, shift_type, day] >=
                                self.x[provider_name, shift_id, day],
                                self._sanitize_name(
                                    f"link_upper_{provider_name}_{shift_type}_{day}_{shift_id}")
                            )
                            count += 1

                    # If no assignment, working_shift_type must be 0
                    # working_shift_type[p, st, d] <= sum of all x[p, s, d]
                    self.problem += (
                        self.working_shift_type[provider_name,
                                                shift_type, day] <= total_assignments,
                        self._sanitize_name(
                            f"link_lower_{provider_name}_{shift_type}_{day}")
                    )
                    count += 1

        print(f"    Added {count} shift type indicator link constraints")

    def _add_credentialing_constraints(self):
        """P1: Credentialing handled by variable pruning - no explicit constraints needed"""
        print("  Credentialing constraints handled via variable pruning")

    def _add_one_shift_type_per_day_constraint(self):
        """P1: A provider can work at most ONE shift type per day (no MD1+PM on same day)"""
        print("  Adding one-shift-type-per-day constraints...")
        count = 0

        for provider_name in self.data.providers.keys():
            for day in self.data.days:
                # Sum of all shift type indicators for this provider on this day must be <= 1
                total_shift_types = pulp.lpSum([
                    self.working_shift_type[provider_name, shift_type, day]
                    for shift_type in ['MD1', 'MD2', 'PM']
                ])

                self.problem += (
                    total_shift_types <= 1,
                    self._sanitize_name(
                        f"one_shift_type_{provider_name}_{day}")
                )
                count += 1

        print(f"    Added {count} one-shift-type-per-day constraints")

    def _add_one_provider_per_facility_group_constraint(self):
        """P1: Each facility group can have at most ONE provider per day"""
        print("  Adding one-provider-per-facility-group constraints...")
        count = 0

        for shift_id in self.data.shifts.keys():
            for day in self.data.days:
                # Only include variables that exist (not pruned)
                available_vars = [
                    self.x[provider_name, shift_id, day]
                    for provider_name in self.data.providers.keys()
                    if (provider_name, shift_id, day) in self.x
                ]

                if available_vars:
                    total_providers = pulp.lpSum(available_vars)
                    self.problem += (
                        total_providers <= 1,
                        self._sanitize_name(f"one_provider_{shift_id}_{day}")
                    )
                    count += 1

        print(f"    Added {count} one-provider-per-facility-group constraints")

    def _link_availability_violations(self):
        """Link availability violation variables (SOFT CONSTRAINT)"""
        print("  Linking availability violation variables (soft)...")
        count = 0

        for provider_name, provider in self.data.providers.items():
            for day in self.data.days:
                if not provider.availability.get(day, True):
                    # Provider is unavailable on this day
                    # Check available variables for this provider on this day
                    available_vars = [
                        self.x[provider_name, shift_id, day]
                        for shift_id in self.data.shifts.keys()
                        if (provider_name, shift_id, day) in self.x
                    ]

                    if available_vars:
                        total_assignments = pulp.lpSum(available_vars)
                        self.problem += (
                            self.availability_violation[provider_name,
                                                        day] >= total_assignments / len(available_vars),
                            f"avail_link_{provider_name}_{day}".replace(
                                " ", "_")
                        )
                        count += 1

        print(f"    Added {count} availability violation links")

    def _add_shift_count_constraints(self):
        """P1: Total shift count constraints (exact for FT, <= for IC)"""
        print("  Adding shift count constraints...")
        print(
            "     NOTE: A 'shift' = working any facilities of a shift TYPE on a given day")
        print("     (e.g., working multiple MD1 facilities on Monday = 1 shift)")

        for provider_name, provider in self.data.providers.items():
            # Count unique (shift_type, day) pairs where provider is working
            # This is the sum of working_shift_type indicators
            total_shifts = pulp.lpSum([
                self.working_shift_type[provider_name, shift_type, day]
                for shift_type in ['MD1', 'MD2', 'PM']
                for day in self.data.days
            ])

            if provider.contract_type == 'FT':
                # Full-time: exactly equal to contracted shifts
                self.problem += (
                    total_shifts == provider.total_shift_count,
                    f"shift_count_ft_{provider_name}".replace(" ", "_")
                )
            else:  # IC
                # Independent contractor: less than or equal to contracted shifts
                self.problem += (
                    total_shifts <= provider.total_shift_count,
                    f"shift_count_ic_{provider_name}".replace(" ", "_")
                )

        print(f"    Added {len(self.data.providers)} shift count constraints")

    def _link_weekend_pm_violations(self):
        """Link weekend and PM over-limit variables (SOFT CONSTRAINTS)"""
        print("  Linking weekend/PM over-limit variables (soft)...")

        for provider_name, provider in self.data.providers.items():
            # Weekend shifts
            weekend_shifts = pulp.lpSum([
                self.working_shift_type[provider_name, shift_type, day]
                for shift_type in ['MD1', 'MD2', 'PM']
                for day in self.data.days
                if day in self.data.weekends
            ])

            # weekend_over = max(0, weekend_shifts - limit)
            self.problem += (
                self.weekend_over[provider_name] >= weekend_shifts -
                provider.weekend_shift_count,
                f"weekend_over_{provider_name}".replace(" ", "_")
            )

            # PM shifts
            pm_shifts = pulp.lpSum([
                self.working_shift_type[provider_name, 'PM', day]
                for day in self.data.days
            ])

            # pm_over = max(0, pm_shifts - limit)
            self.problem += (
                self.pm_over[provider_name] >= pm_shifts -
                provider.pm_shift_count,
                f"pm_over_{provider_name}".replace(" ", "_")
            )

        print(
            f"    Added {len(self.data.providers) * 2} weekend/PM violation links")

    def _add_coverage_constraints(self):
        """P1: Coverage requirements - exactly 1 provider per facility group that needs coverage"""
        print("  Adding coverage requirement constraints...")
        # Shifts that need coverage: MUST have exactly 1 provider
        # Shifts that don't need coverage: implicitly 0 (variables not created)

        coverage_count = 0
        no_coverage_count = 0

        for shift_id, shift in self.data.shifts.items():
            for day in self.data.days:
                # Only check variables that exist (not pruned)
                available_vars = [
                    self.x[provider_name, shift_id, day]
                    for provider_name in self.data.providers.keys()
                    if (provider_name, shift_id, day) in self.x
                ]

                if (shift_id, day) in self.data.coverage_required:
                    # This shift MUST be covered - exactly 1 provider required
                    providers_assigned = pulp.lpSum(available_vars)
                    self.problem += (
                        providers_assigned == 1,  # Exactly 1 provider required
                        self._sanitize_name(f"coverage_{shift_id}_{day}")
                    )
                    coverage_count += 1
                # No need for "no coverage" constraints - pruned variables are implicitly 0
                # (they don't exist, so they can't be assigned)

        print(
            f"    Added {coverage_count} MUST-COVER constraints (exactly 1 provider per required shift)")

    def _add_consecutive_shift_constraints(self):
        """P1: Maximum consecutive shift restrictions using rolling window approach"""
        print("  Adding consecutive shift constraints...")
        count = 0

        for provider_name, provider in self.data.providers.items():
            for shift_type in ['MD1', 'MD2', 'PM']:
                max_consec = provider.max_consecutive_days.get(shift_type, 7)

                # Use rolling window approach: for any window of (max_consec + 1) days,
                # the provider can work at most max_consec days
                for start_day in self.data.days:
                    # Create a window of max_consec + 1 days
                    end_day = min(start_day + max_consec, max(self.data.days))
                    if end_day - start_day < max_consec:
                        # Not enough days left for a full window
                        continue

                    # Sum all working days in this window for this shift type
                    window_work_days = []
                    for day in range(start_day, end_day + 1):
                        if day in self.data.days:
                            # Use working_shift_type variable which already exists
                            # This avoids creating new sums and is more efficient
                            window_work_days.append(
                                self.working_shift_type[provider_name,
                                                        shift_type, day]
                            )

                    if window_work_days:
                        # In any window of (max_consec + 1) days, work at most max_consec days
                        self.problem += (
                            pulp.lpSum(window_work_days) <= max_consec,
                            self._sanitize_name(
                                f"max_consec_{provider_name}_{shift_type}_{start_day}_{end_day}")
                        )
                        count += 1

        print(f"    Added {count} consecutive shift constraints")

    def _add_volume_constraints(self):
        """P1: Volume constraints - total volume per shift type per day must be within limits"""
        print("  Adding volume constraints...")
        count = 0

        # Volume limits by shift type
        volume_limits = {
            'MD1': {'min': 6, 'max': 14},
            'MD2': {'min': 8, 'max': 16},
            'PM': {'min': 5, 'max': 10}
        }

        for provider_name in self.data.providers.keys():
            for day in self.data.days:
                for shift_type in ['MD1', 'MD2', 'PM']:
                    # Get all shifts of this type
                    shifts_of_type = [
                        shift_id for shift_id, shift in self.data.shifts.items()
                        if shift.shift_type == shift_type
                    ]

                    # Calculate total volume for this provider, shift type, and day
                    volume_terms = []
                    for shift_id in shifts_of_type:
                        if (provider_name, shift_id, day) in self.x:
                            # Get the expected volume for this shift
                            shift_volume = self.data.shifts[shift_id].expected_volume
                            # Multiply by assignment variable
                            volume_terms.append(
                                shift_volume * self.x[provider_name, shift_id, day]
                            )

                    if volume_terms:
                        total_volume = pulp.lpSum(volume_terms)
                        limits = volume_limits[shift_type]

                        # Only add constraints if provider is working this shift type
                        # Use working_shift_type indicator to conditionally apply constraint
                        # If working_shift_type == 1, then min <= total_volume <= max
                        # If working_shift_type == 0, then total_volume == 0 (automatically satisfied)

                        # Use Big-M method for conditional constraints
                        # M should be large enough to make constraint always satisfied when not working
                        M = 100  # Large number greater than any possible volume

                        # If working this shift type, volume must be >= min
                        # total_volume >= min * working_shift_type
                        self.problem += (
                            total_volume >= limits['min'] * self.working_shift_type[provider_name, shift_type, day],
                            self._sanitize_name(f"volume_min_{provider_name}_{shift_type}_{day}")
                        )
                        count += 1

                        # If working this shift type, volume must be <= max
                        # total_volume <= max * working_shift_type + M * (1 - working_shift_type)
                        # When working (indicator=1): total_volume <= max
                        # When not working (indicator=0): total_volume <= M (always satisfied)
                        self.problem += (
                            total_volume <= limits['max'] * self.working_shift_type[provider_name, shift_type, day] +
                            M * (1 - self.working_shift_type[provider_name, shift_type, day]),
                            self._sanitize_name(f"volume_max_{provider_name}_{shift_type}_{day}")
                        )
                        count += 1

        print(f"    Added {count} volume constraints")

    def _link_preference_violations(self):
        """Link preference violation variables to assignments (SOFT CONSTRAINT)"""
        print("  Linking preference violation variables (soft)...")
        count = 0

        for provider_name, provider in self.data.providers.items():
            for shift_id, shift in self.data.shifts.items():
                # Check if this shift type is NOT in provider's preferences
                if shift.shift_type not in provider.shift_preference:
                    for day in self.data.days:
                        # Check both that the violation variable exists AND the assignment variable exists
                        if ((provider_name, shift_id, day) in self.preference_violation and
                                (provider_name, shift_id, day) in self.x):
                            # If assigned to this shift, violation must be 1
                            # preference_violation >= assignment
                            self.problem += (
                                self.preference_violation[provider_name, shift_id, day] >=
                                self.x[provider_name, shift_id, day],
                                f"pref_link_{provider_name}_{shift_id}_{day}".replace(
                                    " ", "_").replace(",", "").replace("-", "_")
                            )
                            count += 1

        print(f"    Added {count} preference violation links")

    def build_objective(self, weights: Dict[str, float] = None):
        """
        Build the objective function with weighted soft constraints.

        Args:
            weights: Dictionary of weights for different soft constraints
        """
        if weights is None:
            # Default weights for soft constraints (P2 and P3)
            weights = {
                # P2: Very high penalty for scheduling unavailable days
                'availability_violation': 1000.0,
                'preference_violation': 100.0,     # P2: Penalize assignments against preferences
                'weekend_over': 50.0,              # P2: Penalize exceeding weekend limits
                'pm_over': 50.0,                   # P2: Penalize exceeding PM limits
            }

        print("\nBuilding objective function with soft constraints...")

        objective_terms = []

        # P2: Minimize availability violations (highest priority soft constraint)
        print("  Adding availability violation penalties...")
        for key, var in self.availability_violation.items():
            objective_terms.append(weights['availability_violation'] * var)

        # P2: Minimize preference violations
        print("  Adding preference violation penalties...")
        for key, var in self.preference_violation.items():
            objective_terms.append(weights['preference_violation'] * var)

        # P2: Minimize weekend over-limit violations
        print("  Adding weekend over-limit penalties...")
        for provider_name, var in self.weekend_over.items():
            objective_terms.append(weights['weekend_over'] * var)

        # P2: Minimize PM over-limit violations
        print("  Adding PM over-limit penalties...")
        for provider_name, var in self.pm_over.items():
            objective_terms.append(weights['pm_over'] * var)

        # Set the objective: minimize total weighted violations
        self.problem += pulp.lpSum(objective_terms), "Total_Cost"

        print(f"  Objective function built with {len(objective_terms)} terms")
        print(f"  Goal: Minimize total weighted soft constraint violations")

    def solve(self) -> bool:
        """
        Solve the MILP problem.

        Returns:
            True if optimal or feasible solution found, False otherwise
        """
        print(
            f"\nSolving MILP with time limit of {self.time_limit} seconds...")
        print(
            f"Problem size: {len(self.problem.variables())} variables, {len(self.problem.constraints)} constraints")

        # Solve using CBC solver with parallelization and performance tuning
        solver = pulp.PULP_CBC_CMD(
            msg=1,
            timeLimit=self.time_limit,
            gapRel=0.05,  # Allow 5% optimality gap
            threads=0,  # Use all available CPU cores (0 = auto-detect)
            options=[
                'presolve on',  # Enable presolve to reduce problem size
                'cuts on',  # Enable cutting planes
                'heuristics on',  # Enable heuristics for faster initial solutions
                'strategy 1'  # Aggressive branching strategy
            ]
        )

        self.problem.solve(solver)

        # Check solution status
        status = pulp.LpStatus[self.problem.status]
        print(f"\nSolution Status: {status}")

        if self.problem.status in [pulp.LpStatusOptimal, pulp.LpStatusNotSolved]:
            self.is_solved = True
            self._extract_solution()
            return True
        else:
            print("No feasible solution found!")
            return False

    def _extract_solution(self):
        """Extract the solution from solved model"""
        print("\nExtracting solution...")

        self.solution = {}
        assignment_count = 0

        for (provider_name, shift_id, day), var in self.x.items():
            if var.varValue and var.varValue > 0.5:  # Binary variable is 1
                if day not in self.solution:
                    self.solution[day] = {}
                if shift_id not in self.solution[day]:
                    self.solution[day][shift_id] = []

                self.solution[day][shift_id].append(provider_name)
                assignment_count += 1

        print(f"  Total assignments: {assignment_count}")
        print(f"  Days scheduled: {len(self.solution)}")

    def get_schedule(self) -> Dict[int, Dict[str, List[str]]]:
        """
        Get the schedule as a dictionary.

        Returns:
            Dictionary mapping day -> shift_id -> list of provider names
        """
        if not self.is_solved:
            raise ValueError("Problem has not been solved yet!")

        return self.solution

    def print_summary(self):
        """Print a summary of the schedule"""
        if not self.is_solved:
            print("No solution available")
            return

        print("\n" + "="*80)
        print("SCHEDULE SUMMARY")
        print("="*80)

        # Provider workload summary
        print("\nProvider Workload:")
        provider_shifts = {}
        for day, shifts in self.solution.items():
            for shift_id, providers in shifts.items():
                for provider in providers:
                    if provider not in provider_shifts:
                        provider_shifts[provider] = 0
                    provider_shifts[provider] += 1

        for provider_name in sorted(provider_shifts.keys()):
            contracted = self.data.providers[provider_name].total_shift_count
            actual = provider_shifts[provider_name]
            print(f"  {provider_name}: {actual}/{contracted} shifts")

        # Shift coverage summary
        print("\nShift Coverage:")
        uncovered_days = 0
        for day in self.data.days:
            if day not in self.solution:
                uncovered_days += 1

        print(f"  Total days: {len(self.data.days)}")
        print(f"  Days with coverage: {len(self.solution)}")
        print(f"  Uncovered days: {uncovered_days}")

        # Objective value
        print(f"\nObjective Value: {pulp.value(self.problem.objective):.2f}")


if __name__ == '__main__':
    # Test the scheduler
    from data_loader import DataLoader

    print("Loading data...")
    loader = DataLoader()
    data = loader.load_all_data(num_days=31)

    print("\nInitializing scheduler...")
    scheduler = PhysicianScheduler(data, time_limit_seconds=60)

    print("\nAdding constraints...")
    scheduler.add_hard_constraints()

    print("\nBuilding objective...")
    scheduler.build_objective()

    print("\nSolving...")
    success = scheduler.solve()

    if success:
        scheduler.print_summary()
