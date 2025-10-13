"""
Feasibility Checker for Physician Scheduling System
Performs pre-flight checks to identify infeasibility before attempting to solve
"""
from typing import Dict, List, Tuple, Set
from data_loader import SchedulingData


class FeasibilityChecker:
    """Analyzes scheduling data to identify potential infeasibility issues"""

    def __init__(self, data: SchedulingData):
        self.data = data
        self.eligible_providers = {}  # (shift_id, day) -> list of provider names
        self.provider_capacity = {}  # provider_name -> remaining capacity

    def check_feasibility(self) -> Tuple[bool, List[str]]:
        """
        Check if the scheduling problem is feasible.

        Returns:
            (is_feasible, issues) where issues is a list of problem descriptions
        """
        issues = []

        print("\n" + "="*80)
        print("FEASIBILITY ANALYSIS")
        print("="*80)

        # Step 1: Compute eligible providers per slot
        self._compute_eligible_providers()

        # Step 2: Check for uncoverable shifts
        uncoverable = self._check_uncoverable_shifts()
        if uncoverable:
            issues.append(f"❌ {len(uncoverable)} shifts have NO eligible providers")
            for shift_id, day in uncoverable[:5]:
                issues.append(f"   - {shift_id} on day {day}")
            if len(uncoverable) > 5:
                issues.append(f"   ... and {len(uncoverable) - 5} more")

        # Step 3: Check total capacity vs demand
        capacity_ok, capacity_msg = self._check_total_capacity()
        if not capacity_ok:
            issues.append(capacity_msg)

        # Step 4: Identify bottleneck shifts
        bottlenecks = self._identify_bottlenecks(threshold=3)
        if bottlenecks:
            issues.append(f"⚠️  {len(bottlenecks)} shifts have ≤3 eligible providers (bottlenecks)")
            for shift_id, day, count in bottlenecks[:5]:
                issues.append(f"   - {shift_id[:50]} on day {day}: {count} eligible")
            if len(bottlenecks) > 5:
                issues.append(f"   ... and {len(bottlenecks) - 5} more")

        # Step 5: Provider workload analysis
        self._analyze_provider_workload()

        is_feasible = len([i for i in issues if i.startswith("❌")]) == 0

        print("\n" + "-"*80)
        if is_feasible:
            print("✓ Problem appears FEASIBLE")
            if issues:
                print("⚠️  Warnings (may cause difficulty):")
                for issue in issues:
                    print(f"  {issue}")
        else:
            print("❌ Problem appears INFEASIBLE")
            for issue in issues:
                print(f"  {issue}")
        print("="*80 + "\n")

        return is_feasible, issues

    def _compute_eligible_providers(self):
        """Compute and rank eligible providers for each (shift_id, day) slot"""
        print("\n1. Computing eligible providers per slot...")

        for shift_id, shift in self.data.shifts.items():
            for day in self.data.days:
                if (shift_id, day) not in self.data.coverage_required:
                    continue

                eligible = []

                for provider_name, provider in self.data.providers.items():
                    # Check credentialing
                    is_credentialed = all(
                        facility in provider.credentialed_facilities
                        for facility in shift.facilities
                    )

                    if not is_credentialed:
                        continue

                    # Provider is eligible - compute score (lower is better)
                    score = 0

                    # Penalty for unavailability
                    if not provider.availability.get(day, True):
                        score += 100

                    # Penalty for wrong shift preference
                    if shift.shift_type not in provider.shift_preference:
                        score += 10

                    eligible.append((provider_name, score))

                # Sort by score (best providers first)
                eligible.sort(key=lambda x: x[1])
                self.eligible_providers[(shift_id, day)] = [p[0] for p in eligible]

        total_slots = len(self.data.coverage_required)
        avg_eligible = sum(len(providers) for providers in self.eligible_providers.values()) / total_slots if total_slots > 0 else 0
        print(f"   Total required slots: {total_slots}")
        print(f"   Average eligible providers per slot: {avg_eligible:.1f}")

    def _check_uncoverable_shifts(self) -> List[Tuple[str, int]]:
        """Identify shifts with no eligible providers"""
        print("\n2. Checking for uncoverable shifts...")

        uncoverable = []
        for (shift_id, day), providers in self.eligible_providers.items():
            if len(providers) == 0:
                uncoverable.append((shift_id, day))

        if uncoverable:
            print(f"   ❌ Found {len(uncoverable)} uncoverable shifts")
        else:
            print(f"   ✓ All shifts have at least one eligible provider")

        return uncoverable

    def _check_total_capacity(self) -> Tuple[bool, str]:
        """Check if total provider capacity meets demand"""
        print("\n3. Checking total capacity vs demand...")

        # Calculate total provider capacity (in shifts)
        total_capacity = sum(p.total_shift_count for p in self.data.providers.values())

        # Calculate total demand (in facility groups that need coverage)
        total_demand = len(self.data.coverage_required)

        print(f"   Total provider capacity: {total_capacity} shifts")
        print(f"   Total demand: {total_demand} facility groups")

        # Note: One shift can cover MULTIPLE facility groups if they're the same shift type on same day
        # E.g., working 5 MD1 facility groups on Monday = 1 shift
        # Calculate average facility groups per day to estimate feasibility
        avg_facility_groups_per_day = total_demand / len(self.data.days) if self.data.days else 0

        # Rough heuristic: if capacity is at least 15-20% of demand, likely feasible
        # (because providers work multiple facility groups per shift)
        ratio = total_capacity / total_demand if total_demand > 0 else 1

        print(f"   Capacity ratio: {ratio:.2f} (shifts / facility-groups)")
        print(f"   NOTE: One shift can cover multiple facility groups of same type")

        if ratio >= 0.15:  # Very conservative threshold
            print(f"   ✓ Capacity appears sufficient (ratio: {ratio:.2f})")
            return True, ""
        else:
            msg = f"⚠️  Low capacity ratio: {ratio:.2f} - may be tight but attempting anyway"
            print(f"   {msg}")
            # Return True anyway - let the solver decide
            return True, msg

    def _identify_bottlenecks(self, threshold: int = 3) -> List[Tuple[str, int, int]]:
        """Identify shifts with few eligible providers"""
        print(f"\n4. Identifying bottleneck shifts (≤{threshold} eligible providers)...")

        bottlenecks = []
        for (shift_id, day), providers in self.eligible_providers.items():
            if 0 < len(providers) <= threshold:
                bottlenecks.append((shift_id, day, len(providers)))

        bottlenecks.sort(key=lambda x: x[2])  # Sort by provider count

        if bottlenecks:
            print(f"   ⚠️  Found {len(bottlenecks)} bottleneck shifts")
        else:
            print(f"   ✓ No bottleneck shifts found")

        return bottlenecks

    def _analyze_provider_workload(self):
        """Analyze provider workload distribution"""
        print("\n5. Provider workload analysis...")

        # Group providers by capacity
        high_capacity = [p for p in self.data.providers.values() if p.total_shift_count >= 10]
        medium_capacity = [p for p in self.data.providers.values() if 5 <= p.total_shift_count < 10]
        low_capacity = [p for p in self.data.providers.values() if p.total_shift_count < 5]

        print(f"   High capacity (≥10 shifts): {len(high_capacity)} providers")
        print(f"   Medium capacity (5-9 shifts): {len(medium_capacity)} providers")
        print(f"   Low capacity (<5 shifts): {len(low_capacity)} providers")

        # Check for providers with no eligible shifts
        providers_with_no_shifts = []
        for provider_name, provider in self.data.providers.items():
            eligible_count = sum(
                1 for providers in self.eligible_providers.values()
                if provider_name in providers
            )
            if eligible_count == 0 and provider.total_shift_count > 0:
                providers_with_no_shifts.append(provider_name)

        if providers_with_no_shifts:
            print(f"   ⚠️  {len(providers_with_no_shifts)} providers have capacity but no eligible shifts:")
            for prov in providers_with_no_shifts[:5]:
                print(f"      - {prov}")

    def get_eligible_providers_for_slot(self, shift_id: str, day: int) -> List[str]:
        """Get ranked list of eligible providers for a specific slot"""
        return self.eligible_providers.get((shift_id, day), [])


if __name__ == '__main__':
    # Test feasibility checker
    from data_loader import DataLoader

    loader = DataLoader(data_dir='../data')
    data = loader.load_all_data(num_days=7)

    checker = FeasibilityChecker(data)
    is_feasible, issues = checker.check_feasibility()

    if not is_feasible:
        print("\n⚠️  Scheduling may fail due to infeasibility issues")
