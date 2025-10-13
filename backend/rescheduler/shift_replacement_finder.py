#!/usr/bin/env python3
"""
Shift Replacement Finder for Physician Scheduling System
Brute-force calculates possible replacements when a physician drops out of a shift
"""

import argparse
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
from pathlib import Path
import warnings

# Optional imports for enhanced modeling
try:
    import numpy as np
    from scipy.stats import poisson
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    warnings.warn("scipy not available - absence probability modeling will use simplified calculations")

from data_loader import DataLoader, SchedulingData, Provider
from output_generator import OutputGenerator


class AbsenceProbabilityCalculator:
    """Calculate absence probabilities using Poisson distribution modeling"""

    def __init__(self, base_absence_rate: float = 0.03, seasonal_factor: float = 1.0,
                 weekend_multiplier: float = 1.2, pm_shift_multiplier: float = 1.1):
        """
        Initialize absence probability calculator.

        Args:
            base_absence_rate: Base daily absence rate (e.g., 0.03 = 3% chance per day)
            seasonal_factor: Seasonal multiplier (e.g., 1.5 for flu season)
            weekend_multiplier: Multiplier for weekend shifts (typically higher absence)
            pm_shift_multiplier: Multiplier for PM shifts (typically higher absence)
        """
        self.base_absence_rate = base_absence_rate
        self.seasonal_factor = seasonal_factor
        self.weekend_multiplier = weekend_multiplier
        self.pm_shift_multiplier = pm_shift_multiplier

    def calculate_provider_absence_probability(self, provider: Provider, day: int,
                                             shift_type: str, data: SchedulingData) -> float:
        """
        Calculate absence probability for a specific provider on a specific day/shift.

        Uses Poisson modeling based on:
        - Base absence rate
        - Provider-specific factors (contract type, recent workload)
        - Temporal factors (weekend, shift type)
        - Seasonal adjustments

        Args:
            provider: Provider object
            day: Day index
            shift_type: Type of shift ('MD1', 'MD2', 'PM')
            data: SchedulingData object

        Returns:
            Probability of absence (0.0 to 1.0)
        """
        # Start with base rate
        lambda_rate = self.base_absence_rate

        # Apply seasonal factor
        lambda_rate *= self.seasonal_factor

        # Weekend factor
        if day in data.weekends:
            lambda_rate *= self.weekend_multiplier

        # PM shift factor
        if shift_type == 'PM':
            lambda_rate *= self.pm_shift_multiplier

        # Provider-specific adjustments
        # IC providers may have higher absence rates due to flexibility
        if provider.contract_type == 'IC':
            lambda_rate *= 1.15

        # Providers with high total shift counts may have higher burnout/absence
        if provider.total_shift_count > 15:  # High workload threshold
            lambda_rate *= 1.1
        elif provider.total_shift_count < 8:  # Low commitment threshold
            lambda_rate *= 1.2

        # Convert to probability using Poisson CDF
        # P(at least 1 absence) = 1 - P(0 absences)
        # For daily probability, we use lambda_rate directly as it represents daily rate
        absence_probability = min(lambda_rate, 0.95)  # Cap at 95%

        return absence_probability

    def calculate_reliability_score(self, provider: Provider, day: int,
                                  shift_type: str, data: SchedulingData) -> float:
        """
        Calculate reliability score (inverse of absence probability).

        Returns:
            Reliability score from 0.05 to 1.0 (higher = more reliable)
        """
        p_absent = self.calculate_provider_absence_probability(provider, day, shift_type, data)
        reliability = 1.0 - p_absent
        return max(reliability, 0.05)  # Minimum 5% reliability

    def get_expected_available_replacements(self, candidates: List, day: int,
                                          shift_type: str, data: SchedulingData) -> float:
        """
        Calculate expected number of available replacements considering absence probabilities.

        Args:
            candidates: List of ReplacementCandidate objects
            day: Day index
            shift_type: Shift type
            data: SchedulingData object

        Returns:
            Expected number of actually available candidates
        """
        total_expected = 0.0
        for candidate in candidates:
            if candidate.viability_score > -1000:  # Only viable candidates
                provider = data.providers[candidate.provider_name]
                reliability = self.calculate_reliability_score(provider, day, shift_type, data)
                total_expected += reliability

        return total_expected


@dataclass
class ReplacementCandidate:
    """Represents a potential replacement physician with viability score"""
    provider_name: str
    viability_score: float
    constraint_violations: List[str]
    constraint_passes: List[str]
    additional_info: Dict[str, any]
    score_breakdown: Dict[str, float] = None
    absence_probability: float = 0.0
    reliability_score: float = 1.0


class ShiftReplacementFinder:
    """Finds and ranks possible replacements for a dropped shift"""

    def __init__(self, data: SchedulingData, current_schedule: Dict = None,
                 absence_calculator: AbsenceProbabilityCalculator = None):
        """
        Initialize the replacement finder.

        Args:
            data: SchedulingData object containing all scheduling information
            current_schedule: Current schedule dict {day: {shift_id: [provider_names]}}
            absence_calculator: AbsenceProbabilityCalculator for modeling p_a values
        """
        self.data = data
        self.current_schedule = current_schedule or {}
        self.absence_calculator = absence_calculator or AbsenceProbabilityCalculator()

        # Weights for scoring replacement candidates
        self.scoring_weights = {
            'credentialing_violation': -1000,  # Hard constraint - eliminates candidate
            'availability_violation': -100,    # High penalty
            'already_working_violation': -1000,  # Hard constraint
            'consecutive_days_violation': -50,
            'contract_violation': -30,
            'preference_mismatch': -20,
            'weekend_over_limit': -15,
            'pm_over_limit': -15,
            'volume_mismatch': -10,
            'high_absence_risk': -25,           # High absence probability penalty

            # Positive factors
            'preference_match': 20,
            'available': 10,
            'under_contracted_shifts': 15,
            'good_volume_fit': 10,
            'high_reliability': 25,             # High reliability bonus
        }

    def find_replacements(self, shift_id: str, day: int,
                         dropped_provider: str = None) -> List[ReplacementCandidate]:
        """
        Find all possible replacements for a specific shift on a specific day.

        Args:
            shift_id: ID of the shift that needs coverage
            day: Day index (0-based) when replacement is needed
            dropped_provider: Name of provider who dropped out (optional)

        Returns:
            List of ReplacementCandidate objects ranked by viability score
        """
        if shift_id not in self.data.shifts:
            raise ValueError(f"Shift '{shift_id}' not found in data")

        if day not in self.data.days:
            raise ValueError(f"Day {day} not in scheduling period")

        shift = self.data.shifts[shift_id]
        candidates = []

        print(f"\n{'='*80}")
        print(f"FINDING REPLACEMENTS FOR SHIFT: {shift_id}")
        print(f"Day: {day} ({self.data.day_index_to_date[day].strftime('%Y-%m-%d %A')})")
        print(f"Shift Type: {shift.shift_type}")
        print(f"Facilities: {', '.join(shift.facilities)}")
        if dropped_provider:
            print(f"Dropped Provider: {dropped_provider}")
        print(f"{'='*80}")

        # Analyze each provider as a potential replacement
        for provider_name, provider in self.data.providers.items():
            # Skip the provider who dropped out
            if provider_name == dropped_provider:
                continue

            candidate = self._evaluate_replacement_candidate(
                provider_name, provider, shift_id, shift, day
            )
            candidates.append(candidate)

        # Sort by viability score (highest first)
        candidates.sort(key=lambda x: x.viability_score, reverse=True)

        return candidates

    def _evaluate_replacement_candidate(self, provider_name: str, provider: Provider,
                                      shift_id: str, shift, day: int) -> ReplacementCandidate:
        """Evaluate a single provider as a replacement candidate"""

        violations = []
        passes = []
        score = 0.0
        additional_info = {}
        score_breakdown = {}  # Track how each component contributes to score

        # 1. HARD CONSTRAINT: Credentialing
        is_credentialed = all(
            facility in provider.credentialed_facilities
            for facility in shift.facilities
        )

        if not is_credentialed:
            violations.append("Not credentialed for required facilities")
            penalty = self.scoring_weights['credentialing_violation']
            score += penalty
            score_breakdown['credentialing_violation'] = penalty
            missing_creds = [f for f in shift.facilities if f not in provider.credentialed_facilities]
            additional_info['missing_credentials'] = missing_creds
        else:
            passes.append("Credentialed for all required facilities")
            score_breakdown['credentialing'] = 0  # No penalty

        # 2. HARD CONSTRAINT: Already working another shift on this day
        current_assignments = self._get_provider_assignments_on_day(provider_name, day)
        if current_assignments:
            violations.append(f"Already assigned to: {', '.join(current_assignments)}")
            penalty = self.scoring_weights['already_working_violation']
            score += penalty
            score_breakdown['already_working_violation'] = penalty
        else:
            passes.append("Available (not currently assigned on this day)")
            bonus = self.scoring_weights['available']
            score += bonus
            score_breakdown['available'] = bonus

        # 3. Availability
        is_available = provider.availability.get(day, True)
        if not is_available:
            violations.append("Marked as unavailable on this day")
            penalty = self.scoring_weights['availability_violation']
            score += penalty
            score_breakdown['availability_violation'] = penalty
        else:
            passes.append("Available on this day")
            score_breakdown['availability'] = 0  # No penalty, no bonus

        # 4. Shift preference
        if shift.shift_type in provider.shift_preference:
            passes.append(f"Prefers {shift.shift_type} shifts")
            bonus = self.scoring_weights['preference_match']
            score += bonus
            score_breakdown['preference_match'] = bonus
        else:
            violations.append(f"Does not prefer {shift.shift_type} shifts")
            penalty = self.scoring_weights['preference_mismatch']
            score += penalty
            score_breakdown['preference_mismatch'] = penalty

        # 5. Consecutive days constraint
        consecutive_violation = self._check_consecutive_days_violation(
            provider, shift.shift_type, day
        )
        if consecutive_violation:
            violations.append(consecutive_violation)
            penalty = self.scoring_weights['consecutive_days_violation']
            score += penalty
            score_breakdown['consecutive_days_violation'] = penalty
        else:
            passes.append("No consecutive days constraint violation")
            score_breakdown['consecutive_days'] = 0  # No penalty

        # 6. Contract constraints (shift count)
        current_shift_count = self._count_provider_shifts(provider_name)
        contract_status = self._check_contract_constraint(provider, current_shift_count)

        if contract_status['violation']:
            violations.append(contract_status['message'])
            penalty = self.scoring_weights['contract_violation']
            score += penalty
            score_breakdown['contract_violation'] = penalty
        elif contract_status['under_limit']:
            passes.append(contract_status['message'])
            bonus = self.scoring_weights['under_contracted_shifts']
            score += bonus
            score_breakdown['under_contracted_shifts'] = bonus
        else:
            passes.append(contract_status['message'])
            score_breakdown['contract'] = 0  # Meets exactly, no bonus/penalty

        additional_info['current_shifts'] = current_shift_count
        additional_info['contracted_shifts'] = provider.total_shift_count

        # 7. Weekend constraints
        if day in self.data.weekends:
            weekend_shifts = self._count_weekend_shifts(provider_name)
            if weekend_shifts >= provider.weekend_shift_count:
                violations.append(f"Would exceed weekend limit ({weekend_shifts + 1}/{provider.weekend_shift_count})")
                penalty = self.scoring_weights['weekend_over_limit']
                score += penalty
                score_breakdown['weekend_over_limit'] = penalty
            else:
                passes.append(f"Within weekend limit ({weekend_shifts + 1}/{provider.weekend_shift_count})")
                score_breakdown['weekend'] = 0  # No penalty
        else:
            score_breakdown['weekend'] = 0  # Not a weekend day

        # 8. PM shift constraints
        if shift.shift_type == 'PM':
            pm_shifts = self._count_pm_shifts(provider_name)
            if pm_shifts >= provider.pm_shift_count:
                violations.append(f"Would exceed PM limit ({pm_shifts + 1}/{provider.pm_shift_count})")
                penalty = self.scoring_weights['pm_over_limit']
                score += penalty
                score_breakdown['pm_over_limit'] = penalty
            else:
                passes.append(f"Within PM limit ({pm_shifts + 1}/{provider.pm_shift_count})")
                score_breakdown['pm'] = 0  # No penalty
        else:
            score_breakdown['pm'] = 0  # Not a PM shift

        # 9. Volume considerations
        volume_assessment = self._assess_volume_fit(provider, shift, day)
        if volume_assessment['good_fit']:
            passes.append(f"Good volume fit ({volume_assessment['expected_volume']:.1f} patients)")
            bonus = self.scoring_weights['good_volume_fit']
            score += bonus
            score_breakdown['good_volume_fit'] = bonus
        else:
            violations.append(f"Volume concern: {volume_assessment['concern']}")
            penalty = self.scoring_weights['volume_mismatch']
            score += penalty
            score_breakdown['volume_mismatch'] = penalty

        additional_info.update(volume_assessment)

        # 10. Absence probability assessment
        absence_prob = self.absence_calculator.calculate_provider_absence_probability(
            provider, day, shift.shift_type, self.data
        )
        reliability = self.absence_calculator.calculate_reliability_score(
            provider, day, shift.shift_type, self.data
        )

        # Score based on reliability
        if reliability >= 0.95:  # Very reliable (≤5% absence chance)
            passes.append(f"Very reliable ({(1-absence_prob)*100:.1f}% likely to show up)")
            bonus = self.scoring_weights['high_reliability']
            score += bonus
            score_breakdown['high_reliability'] = bonus
        elif absence_prob >= 0.15:  # High absence risk (≥15% chance)
            violations.append(f"High absence risk ({absence_prob*100:.1f}% chance of calling out)")
            penalty = self.scoring_weights['high_absence_risk']
            score += penalty
            score_breakdown['high_absence_risk'] = penalty
        else:
            passes.append(f"Moderate reliability ({(1-absence_prob)*100:.1f}% likely to show up)")
            score_breakdown['reliability'] = 0  # Neutral

        additional_info['absence_probability'] = absence_prob
        additional_info['reliability_score'] = reliability

        return ReplacementCandidate(
            provider_name=provider_name,
            viability_score=score,
            constraint_violations=violations,
            constraint_passes=passes,
            additional_info=additional_info,
            score_breakdown=score_breakdown,
            absence_probability=absence_prob,
            reliability_score=reliability
        )

    def _get_provider_assignments_on_day(self, provider_name: str, day: int) -> List[str]:
        """Get list of shift IDs the provider is assigned to on the given day"""
        assignments = []
        if day in self.current_schedule:
            for shift_id, assigned_providers in self.current_schedule[day].items():
                if provider_name in assigned_providers:
                    assignments.append(shift_id)
        return assignments

    def _check_consecutive_days_violation(self, provider: Provider, shift_type: str, target_day: int) -> Optional[str]:
        """Check if assigning provider to shift_type on target_day would violate consecutive days limit"""
        max_consecutive = provider.max_consecutive_days.get(shift_type, 7)

        # Get days when provider is working this shift type around target_day
        working_days = set()

        # Add target day
        working_days.add(target_day)

        # Check current schedule for this shift type
        for day, shifts in self.current_schedule.items():
            for shift_id, assigned_providers in shifts.items():
                if (provider.name in assigned_providers and
                    self.data.shifts[shift_id].shift_type == shift_type):
                    working_days.add(day)

        # Check if any consecutive sequence exceeds the limit
        sorted_days = sorted(working_days)
        consecutive_count = 1
        max_consecutive_found = 1

        for i in range(1, len(sorted_days)):
            if sorted_days[i] == sorted_days[i-1] + 1:  # Consecutive day
                consecutive_count += 1
                max_consecutive_found = max(max_consecutive_found, consecutive_count)
            else:
                consecutive_count = 1

        if max_consecutive_found > max_consecutive:
            return f"Would create {max_consecutive_found} consecutive {shift_type} days (limit: {max_consecutive})"

        return None

    def _count_provider_shifts(self, provider_name: str) -> int:
        """Count total shifts currently assigned to provider"""
        count = 0
        for day, shifts in self.current_schedule.items():
            for shift_id, assigned_providers in shifts.items():
                if provider_name in assigned_providers:
                    count += 1
        return count

    def _check_contract_constraint(self, provider: Provider, current_count: int) -> Dict:
        """Check contract constraints for additional shift"""
        new_count = current_count + 1

        if provider.contract_type == 'FT':
            if new_count > provider.total_shift_count:
                return {
                    'violation': True,
                    'under_limit': False,
                    'message': f"Would exceed FT contract ({new_count}/{provider.total_shift_count})"
                }
            elif new_count < provider.total_shift_count:
                return {
                    'violation': False,
                    'under_limit': True,
                    'message': f"Still under FT contract ({new_count}/{provider.total_shift_count})"
                }
            else:
                return {
                    'violation': False,
                    'under_limit': False,
                    'message': f"Would meet FT contract exactly ({new_count}/{provider.total_shift_count})"
                }
        else:  # IC
            if new_count > provider.total_shift_count:
                return {
                    'violation': True,
                    'under_limit': False,
                    'message': f"Would exceed IC contract ({new_count}/{provider.total_shift_count})"
                }
            else:
                return {
                    'violation': False,
                    'under_limit': new_count < provider.total_shift_count,
                    'message': f"Within IC contract ({new_count}/{provider.total_shift_count})"
                }

    def _count_weekend_shifts(self, provider_name: str) -> int:
        """Count weekend shifts currently assigned to provider"""
        count = 0
        for day, shifts in self.current_schedule.items():
            if day in self.data.weekends:
                for shift_id, assigned_providers in shifts.items():
                    if provider_name in assigned_providers:
                        count += 1
        return count

    def _count_pm_shifts(self, provider_name: str) -> int:
        """Count PM shifts currently assigned to provider"""
        count = 0
        for day, shifts in self.current_schedule.items():
            for shift_id, assigned_providers in shifts.items():
                if (provider_name in assigned_providers and
                    self.data.shifts[shift_id].shift_type == 'PM'):
                    count += 1
        return count

    def _assess_volume_fit(self, provider: Provider, shift, day: int) -> Dict:
        """Assess how well provider fits the volume requirements for this shift"""
        expected_volume = shift.expected_volume

        # Volume limits for shift types
        volume_limits = {
            'MD1': {'min': 6, 'max': 14},
            'MD2': {'min': 8, 'max': 16},
            'PM': {'min': 5, 'max': 10}
        }

        limits = volume_limits.get(shift.shift_type, {'min': 0, 'max': 20})

        if limits['min'] <= expected_volume <= limits['max']:
            return {
                'good_fit': True,
                'expected_volume': expected_volume,
                'volume_range': f"{limits['min']}-{limits['max']}",
                'concern': None
            }
        elif expected_volume < limits['min']:
            return {
                'good_fit': False,
                'expected_volume': expected_volume,
                'volume_range': f"{limits['min']}-{limits['max']}",
                'concern': f"Low volume ({expected_volume:.1f} < {limits['min']})"
            }
        else:
            return {
                'good_fit': False,
                'expected_volume': expected_volume,
                'volume_range': f"{limits['min']}-{limits['max']}",
                'concern': f"High volume ({expected_volume:.1f} > {limits['max']})"
            }

    def print_replacement_report(self, candidates: List[ReplacementCandidate],
                               max_candidates: int = 10,
                               show_eliminated: bool = True):
        """Print a detailed report of replacement candidates"""

        # Separate viable from eliminated candidates
        viable_candidates = [c for c in candidates if c.viability_score > -1000]
        eliminated_candidates = [c for c in candidates if c.viability_score <= -1000]

        print(f"\n{'='*80}")
        print("REPLACEMENT ANALYSIS SUMMARY")
        print(f"{'='*80}")
        print(f"Total providers analyzed: {len(candidates)}")
        print(f"Viable candidates: {len(viable_candidates)}")
        print(f"Eliminated (hard constraint violations): {len(eliminated_candidates)}")

        if viable_candidates:
            print(f"\n{'='*80}")
            print(f"TOP VIABLE REPLACEMENTS (showing top {min(max_candidates, len(viable_candidates))})")
            print(f"{'='*80}")

            for i, candidate in enumerate(viable_candidates[:max_candidates]):
                print(f"\n{i+1}. {candidate.provider_name}")
                print(f"   Viability Score: {candidate.viability_score:.1f}")
                print(f"   Current Shifts: {candidate.additional_info.get('current_shifts', '?')}"
                      f"/{candidate.additional_info.get('contracted_shifts', '?')}")

                # Show detailed score breakdown
                if candidate.score_breakdown:
                    print("   📊 SCORE BREAKDOWN:")
                    for component, points in sorted(candidate.score_breakdown.items(),
                                                  key=lambda x: x[1], reverse=True):
                        if points != 0:
                            symbol = "+" if points > 0 else ""
                            component_name = component.replace('_', ' ').title()
                            print(f"     {symbol}{points:+.1f} pts - {component_name}")

                if candidate.constraint_passes:
                    print("   ✓ PASSES:")
                    for pass_item in candidate.constraint_passes:
                        print(f"     • {pass_item}")

                if candidate.constraint_violations:
                    print("   ⚠ CONCERNS:")
                    for violation in candidate.constraint_violations:
                        print(f"     • {violation}")

                # Additional info
                if 'expected_volume' in candidate.additional_info:
                    vol = candidate.additional_info['expected_volume']
                    range_info = candidate.additional_info.get('volume_range', '')
                    print(f"   Expected Volume: {vol:.1f} patients (range: {range_info})")

                # Reliability information
                if candidate.absence_probability > 0:
                    reliability_pct = (1 - candidate.absence_probability) * 100
                    absence_pct = candidate.absence_probability * 100
                    print(f"   📊 Reliability: {reliability_pct:.1f}% likely to show up ({absence_pct:.1f}% absence risk)")

        if eliminated_candidates and show_eliminated:
            print(f"\n{'='*80}")
            print("ELIMINATED CANDIDATES (Hard Constraint Violations)")
            print(f"{'='*80}")

            for candidate in eliminated_candidates:
                hard_violations = [v for v in candidate.constraint_violations
                                 if 'credentialed' in v.lower() or 'already assigned' in v.lower()]
                if hard_violations:
                    print(f"\n❌ {candidate.provider_name}")
                    for violation in hard_violations:
                        print(f"   • {violation}")

    def generate_replacement_schedule_preview(self, shift_id: str, day: int,
                                            replacement_provider: str) -> Dict:
        """Generate a preview of what the schedule would look like with the replacement"""
        preview_schedule = {}

        # Copy existing schedule
        for d, shifts in self.current_schedule.items():
            preview_schedule[d] = {}
            for s_id, providers in shifts.items():
                preview_schedule[d][s_id] = providers.copy()

        # Add the replacement
        if day not in preview_schedule:
            preview_schedule[day] = {}

        preview_schedule[day][shift_id] = [replacement_provider]

        return preview_schedule

    def export_to_csv(self, candidates: List[ReplacementCandidate],
                     filename: str, shift_id: str, day: int) -> None:
        """Export replacement candidates to CSV file"""
        import csv
        from datetime import datetime as dt

        print(f"\n📊 Exporting results to {filename}...")

        # Prepare data for CSV
        csv_data = []

        # Add header information
        shift_info = {
            'provider_name': 'SHIFT_INFO',
            'viability_score': '',
            'rank': '',
            'shift_id': shift_id,
            'day': day,
            'date': self.data.day_index_to_date[day].strftime('%Y-%m-%d %A'),
            'shift_type': self.data.shifts[shift_id].shift_type,
            'facilities': ', '.join(self.data.shifts[shift_id].facilities),
            'expected_volume': self.data.shifts[shift_id].expected_volume,
            'contract_type': '',
            'current_shifts': '',
            'contracted_shifts': '',
            'absence_probability': '',
            'reliability_score': '',
            'credentialed': '',
            'available': '',
            'preferences_match': '',
            'constraint_violations': '',
            'constraint_passes': '',
            'score_breakdown': ''
        }
        csv_data.append(shift_info)

        # Add empty row for separation
        csv_data.append({k: '' for k in shift_info.keys()})

        # Sort candidates by viability score
        sorted_candidates = sorted(candidates, key=lambda x: x.viability_score, reverse=True)

        for rank, candidate in enumerate(sorted_candidates, 1):
            provider = self.data.providers[candidate.provider_name]

            # Determine status
            if candidate.viability_score <= -1000:
                status = 'ELIMINATED'
            elif candidate.viability_score > 0:
                status = 'EXCELLENT'
            elif candidate.viability_score > -50:
                status = 'GOOD'
            else:
                status = 'VIABLE_CONCERNS'

            # Format score breakdown
            breakdown_str = ''
            if candidate.score_breakdown:
                breakdown_parts = []
                for component, points in sorted(candidate.score_breakdown.items(),
                                              key=lambda x: x[1], reverse=True):
                    if points != 0:
                        breakdown_parts.append(f"{component}: {points:+.1f}")
                breakdown_str = '; '.join(breakdown_parts)

            row_data = {
                'provider_name': candidate.provider_name,
                'viability_score': f"{candidate.viability_score:.1f}",
                'rank': rank,
                'status': status,
                'shift_id': shift_id,
                'day': day,
                'date': self.data.day_index_to_date[day].strftime('%Y-%m-%d %A'),
                'shift_type': self.data.shifts[shift_id].shift_type,
                'facilities': ', '.join(self.data.shifts[shift_id].facilities),
                'expected_volume': f"{self.data.shifts[shift_id].expected_volume:.1f}",
                'contract_type': provider.contract_type,
                'current_shifts': candidate.additional_info.get('current_shifts', 0),
                'contracted_shifts': candidate.additional_info.get('contracted_shifts', 0),
                'absence_probability': f"{candidate.absence_probability:.3f}" if candidate.absence_probability > 0 else '',
                'reliability_score': f"{candidate.reliability_score:.3f}" if candidate.reliability_score < 1 else '',
                'credentialed': 'YES' if not any('credentialed' in v.lower() for v in candidate.constraint_violations) else 'NO',
                'available': 'YES' if not any('already assigned' in v.lower() for v in candidate.constraint_violations) else 'NO',
                'preferences_match': 'YES' if any('prefers' in p.lower() for p in candidate.constraint_passes) else 'NO',
                'constraint_violations': '; '.join(candidate.constraint_violations),
                'constraint_passes': '; '.join(candidate.constraint_passes),
                'score_breakdown': breakdown_str
            }
            csv_data.append(row_data)

        # Write to CSV
        if csv_data:
            fieldnames = csv_data[2].keys() if len(csv_data) > 2 else csv_data[0].keys()

            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)

            viable_count = len([c for c in candidates if c.viability_score > -1000])
            eliminated_count = len([c for c in candidates if c.viability_score <= -1000])

            print(f"✓ Exported {len(candidates)} candidates to {filename}")
            print(f"  - {viable_count} viable candidates")
            print(f"  - {eliminated_count} eliminated candidates")
            print(f"  - Top candidate: {sorted_candidates[0].provider_name} (score: {sorted_candidates[0].viability_score:.1f})")


def show_scoring_weights():
    """Display detailed scoring weights used in replacement analysis"""
    print("PHYSICIAN REPLACEMENT SCORING WEIGHTS")
    print("="*80)
    print()

    # Use the same weights as the ShiftReplacementFinder class
    scoring_weights = {
        'credentialing_violation': -1000,  # Hard constraint - eliminates candidate
        'availability_violation': -100,    # High penalty
        'already_working_violation': -1000,  # Hard constraint
        'consecutive_days_violation': -50,
        'contract_violation': -30,
        'high_absence_risk': -25,           # High absence probability penalty
        'preference_mismatch': -20,
        'weekend_over_limit': -15,
        'pm_over_limit': -15,
        'volume_mismatch': -10,

        # Positive factors
        'high_reliability': 25,             # High reliability bonus
        'preference_match': 20,
        'under_contracted_shifts': 15,
        'available': 10,
        'good_volume_fit': 10,
    }

    print("CONSTRAINT VIOLATIONS (Negative Points):")
    print("-" * 60)
    penalties = {k: v for k, v in scoring_weights.items() if v < 0}
    for constraint, penalty in sorted(penalties.items(), key=lambda x: x[1]):
        constraint_name = constraint.replace('_', ' ').title()
        if penalty <= -1000:
            print(f"  {penalty:+5.0f} pts - {constraint_name} (ELIMINATES CANDIDATE)")
        else:
            print(f"  {penalty:+5.0f} pts - {constraint_name}")

    print()
    print("POSITIVE FACTORS (Bonus Points):")
    print("-" * 60)
    bonuses = {k: v for k, v in scoring_weights.items() if v > 0}
    for factor, bonus in sorted(bonuses.items(), key=lambda x: x[1], reverse=True):
        factor_name = factor.replace('_', ' ').title()
        print(f"  {bonus:+5.0f} pts - {factor_name}")

    print()
    print("SCORE INTERPRETATION:")
    print("-" * 60)
    print("  Score > 0    : Excellent replacement candidate")
    print("  Score 0 to -50 : Good candidate with minor concerns")
    print("  Score -50 to -100 : Viable but multiple issues")
    print("  Score ≤ -1000 : ELIMINATED (hard constraint violations)")
    print()
    print("Total possible score range: -2025 to +80 points (with absence modeling)")
    print()


def load_current_schedule(schedule_file: str) -> Dict:
    """Load current schedule from Excel file"""
    try:
        import pandas as pd

        # This is a simplified loader - you may need to adjust based on your Excel format
        df = pd.read_excel(schedule_file)

        schedule = {}
        # Parse the Excel format and convert to our internal format
        # This would need to be customized based on your actual Excel structure

        return schedule

    except Exception as e:
        print(f"Warning: Could not load current schedule from {schedule_file}: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(
        description='Find replacement physicians for dropped shifts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find replacements for a specific shift on day 5
  python shift_replacement_finder.py --shift "MD1 - NHMC, NMMC" --day 5

  # Include current schedule for better analysis
  python shift_replacement_finder.py --shift "PM - NBAMC" --day 10 --schedule current_schedule.xlsx

  # Show more candidates including eliminated ones
  python shift_replacement_finder.py --shift "MD2 - Hospital A" --day 15 --max-candidates 15 --show-eliminated

  # Specify who dropped out
  python shift_replacement_finder.py --shift "MD1 - NHMC" --day 3 --dropped-provider "Dr. Smith"

  # Show detailed scoring weights
  python shift_replacement_finder.py --show-scoring

  # Use enhanced absence modeling for flu season
  python shift_replacement_finder.py --shift "PM - NBAMC" --day 10 --seasonal-factor 1.5 --base-absence-rate 0.05

  # Disable absence modeling for traditional scoring
  python shift_replacement_finder.py --shift "MD1 - Hospital A" --day 5 --disable-absence-modeling
        """
    )

    parser.add_argument(
        '--shift',
        help='Shift ID that needs replacement (e.g., "MD1 - NHMC, NMMC")'
    )

    parser.add_argument(
        '--day',
        type=int,
        help='Day index (0-based) when replacement is needed'
    )

    parser.add_argument(
        '--data-dir',
        default='../data',
        help='Directory containing input Excel files (default: ../data)'
    )

    parser.add_argument(
        '--schedule',
        help='Current schedule Excel file (optional)'
    )

    parser.add_argument(
        '--dropped-provider',
        help='Name of provider who dropped out (optional)'
    )

    parser.add_argument(
        '--max-candidates',
        type=int,
        default=10,
        help='Maximum number of candidates to show (default: 10)'
    )

    parser.add_argument(
        '--show-eliminated',
        action='store_true',
        help='Show eliminated candidates with hard constraint violations'
    )

    parser.add_argument(
        '--num-days',
        type=int,
        default=31,
        help='Number of days in scheduling period (default: 31)'
    )

    parser.add_argument(
        '--show-scoring',
        action='store_true',
        help='Show detailed scoring weights and exit'
    )

    # Absence probability modeling parameters
    parser.add_argument(
        '--base-absence-rate',
        type=float,
        default=0.03,
        help='Base daily absence rate (default: 0.03 = 3%% per day)'
    )

    parser.add_argument(
        '--seasonal-factor',
        type=float,
        default=1.0,
        help='Seasonal absence multiplier (default: 1.0, use 1.5 for flu season)'
    )

    parser.add_argument(
        '--weekend-multiplier',
        type=float,
        default=1.2,
        help='Weekend absence multiplier (default: 1.2)'
    )

    parser.add_argument(
        '--pm-multiplier',
        type=float,
        default=1.1,
        help='PM shift absence multiplier (default: 1.1)'
    )

    parser.add_argument(
        '--disable-absence-modeling',
        action='store_true',
        help='Disable absence probability modeling and use traditional scoring only'
    )

    parser.add_argument(
        '--export-csv',
        type=str,
        help='Export results to CSV file (e.g., replacements.csv)'
    )

    args = parser.parse_args()

    # Show scoring weights if requested
    if args.show_scoring:
        show_scoring_weights()
        sys.exit(0)

    # Validate required arguments
    if not args.shift:
        parser.error("--shift is required")
    if args.day is None:
        parser.error("--day is required")

    print("PHYSICIAN SHIFT REPLACEMENT FINDER")
    print("="*80)

    # Load data
    print("Loading scheduling data...")
    try:
        loader = DataLoader(data_dir=args.data_dir)
        data = loader.load_all_data(num_days=args.num_days)
        print(f"✓ Loaded {len(data.providers)} providers, {len(data.shifts)} shifts")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        sys.exit(1)

    # Load current schedule if provided
    current_schedule = {}
    if args.schedule:
        current_schedule = load_current_schedule(args.schedule)
        if current_schedule:
            print(f"✓ Loaded current schedule from {args.schedule}")
        else:
            print(f"⚠ Using empty schedule (could not load from {args.schedule})")

    # Validate shift ID
    if args.shift not in data.shifts:
        print(f"❌ Error: Shift '{args.shift}' not found in data")
        print(f"Available shifts:")
        for shift_id in sorted(data.shifts.keys())[:10]:
            print(f"  {shift_id}")
        if len(data.shifts) > 10:
            print(f"  ... and {len(data.shifts) - 10} more")
        sys.exit(1)

    # Validate day
    if args.day not in data.days:
        print(f"❌ Error: Day {args.day} not in scheduling period (0-{len(data.days)-1})")
        sys.exit(1)

    # Create absence probability calculator
    absence_calculator = None
    if not args.disable_absence_modeling:
        absence_calculator = AbsenceProbabilityCalculator(
            base_absence_rate=args.base_absence_rate,
            seasonal_factor=args.seasonal_factor,
            weekend_multiplier=args.weekend_multiplier,
            pm_shift_multiplier=args.pm_multiplier
        )
        print(f"✓ Absence probability modeling enabled:")
        print(f"  Base rate: {args.base_absence_rate*100:.1f}% per day")
        print(f"  Seasonal factor: {args.seasonal_factor:.2f}x")
        print(f"  Weekend multiplier: {args.weekend_multiplier:.2f}x")
        print(f"  PM shift multiplier: {args.pm_multiplier:.2f}x")
    else:
        print("⚠ Absence probability modeling disabled")

    # Create replacement finder and analyze
    finder = ShiftReplacementFinder(data, current_schedule, absence_calculator)

    try:
        candidates = finder.find_replacements(
            shift_id=args.shift,
            day=args.day,
            dropped_provider=args.dropped_provider
        )

        finder.print_replacement_report(
            candidates,
            max_candidates=args.max_candidates,
            show_eliminated=args.show_eliminated
        )

        # Export to CSV if requested
        if args.export_csv:
            finder.export_to_csv(candidates, args.export_csv, args.shift, args.day)

        # Provide actionable summary
        viable_candidates = [c for c in candidates if c.viability_score > -1000]

        if viable_candidates:
            best_candidate = viable_candidates[0]
            print(f"\n{'='*80}")
            print("RECOMMENDATION")
            print(f"{'='*80}")
            print(f"Best replacement: {best_candidate.provider_name}")
            print(f"Viability score: {best_candidate.viability_score:.1f}")
            print(f"\nNext steps:")
            print(f"1. Contact {best_candidate.provider_name} to confirm availability")
            print(f"2. Update schedule to assign {best_candidate.provider_name} to {args.shift} on day {args.day}")

            if best_candidate.constraint_violations:
                print(f"3. Review these concerns:")
                for violation in best_candidate.constraint_violations:
                    print(f"   • {violation}")
        else:
            print(f"\n❌ NO VIABLE REPLACEMENTS FOUND")
            print("All providers have hard constraint violations that prevent assignment.")
            print("Consider:")
            print("• Modifying shift requirements")
            print("• Finding coverage from external sources")
            print("• Adjusting the schedule structure")

    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        if '--debug' in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()