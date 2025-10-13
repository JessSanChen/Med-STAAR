"""
Data Loader for Physician Scheduling System
Loads and parses Excel files containing constraint data
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field


@dataclass
class Provider:
    """Represents a healthcare provider"""
    name: str
    contract_type: str  # 'FT' or 'IC'
    shift_preference: List[str]  # e.g., ['MD1', 'PM']
    total_shift_count: int
    weekend_shift_count: int
    pm_shift_count: int
    credentialed_facilities: Set[str]
    availability: Dict[int, bool]  # day_index -> is_available
    max_consecutive_days: Dict[str, int] = field(default_factory=dict)  # shift_type -> max_days
    max_daily_hours: float = 12.0


@dataclass
class Shift:
    """Represents a shift with facility grouping"""
    id: str
    shift_type: str  # 'MD1', 'MD2', or 'PM'
    facilities: List[str]
    min_volume: float
    max_volume: float
    expected_volume: float
    shift_hours: float = 12.0


@dataclass
class SchedulingData:
    """Container for all scheduling data"""
    providers: Dict[str, Provider]
    shifts: Dict[str, Shift]
    days: List[int]  # day indices
    date_to_day_index: Dict[datetime, int]
    day_index_to_date: Dict[int, datetime]
    weekends: Set[int]  # day indices that are weekends
    facility_volumes: Dict[Tuple[str, str], float]  # (facility, shift_type) -> avg_volume
    coverage_required: Set[Tuple[str, int]]  # (shift_id, day_index) pairs that MUST be covered


class DataLoader:
    """Loads and processes scheduling data from Excel files"""

    def __init__(self, data_dir: str = '../data'):
        self.data_dir = data_dir

    def load_all_data(self, num_days: int = 31, start_date: datetime = None) -> SchedulingData:
        """Load all data required for scheduling"""
        if start_date is None:
            start_date = datetime(2025, 1, 1)

        print("Loading provider contracts...")
        providers_df = self._load_provider_contracts()

        print("Loading provider credentialing...")
        credentialing_df = self._load_provider_credentialing()

        print("Loading provider availability...")
        availability_df = self._load_provider_availability()

        print("Loading facility volumes...")
        volumes_df = self._load_facility_volumes()

        print("Loading facility coverage...")
        coverage_df = self._load_facility_coverage()

        print("Loading sample schedule for shift structure...")
        shifts_df = self._load_sample_schedule()

        print("Building data structures...")

        # Create date mappings
        days = list(range(num_days))
        date_to_day_index = {}
        day_index_to_date = {}
        weekends = set()

        for day_idx in days:
            date = start_date + timedelta(days=day_idx)
            date_to_day_index[date] = day_idx
            day_index_to_date[day_idx] = date
            if date.weekday() >= 5:  # Saturday=5, Sunday=6
                weekends.add(day_idx)

        # Build provider objects
        providers = {}
        for _, row in providers_df.iterrows():
            provider_name = row['Provider Name']

            # Get credentialing
            cred_row = credentialing_df[credentialing_df['Provider'] == provider_name]
            if len(cred_row) > 0:
                facilities_str = cred_row.iloc[0]['Credentialed Facilities']
                credentialed = set(f.strip() for f in str(facilities_str).split(','))
            else:
                credentialed = set()

            # Get availability
            availability = {}
            if provider_name in availability_df.columns:
                for day_idx in days:
                    if day_idx < len(availability_df):
                        val = availability_df[provider_name].iloc[day_idx]
                        # Available if not marked as 'Unavailable'
                        availability[day_idx] = (pd.isna(val) or str(val).strip() == '' or
                                                str(val).strip() == '\xa0')
                    else:
                        availability[day_idx] = True
            else:
                # Default to available all days
                availability = {day_idx: True for day_idx in days}

            # Parse shift preferences
            pref_str = str(row['Shift preference'])
            if pd.isna(pref_str) or pref_str.lower() == 'nan':
                shift_prefs = []
            else:
                shift_prefs = [s.strip() for s in pref_str.split(',')]

            # Default max consecutive days (can be overridden per provider)
            max_consecutive = {
                'MD1': 4,
                'MD2': 7,
                'PM': 3
            }

            # Scale shift counts based on scheduling period
            # Contract file has monthly totals (assumes 31 days)
            # Scale proportionally for the actual scheduling period
            REFERENCE_DAYS = 31  # Contract file assumes 31-day month
            scale_factor = num_days / REFERENCE_DAYS

            total_shifts_scaled = int(round(row['Total shift count'] * scale_factor))
            weekend_shifts_scaled = int(round(row['Weekend shift count'] * scale_factor))
            pm_shifts_scaled = int(round(row['PM shift count'] * scale_factor))

            provider = Provider(
                name=provider_name,
                contract_type=row['Contract type'],
                shift_preference=shift_prefs,
                total_shift_count=total_shifts_scaled,
                weekend_shift_count=weekend_shifts_scaled,
                pm_shift_count=pm_shifts_scaled,
                credentialed_facilities=credentialed,
                availability=availability,
                max_consecutive_days=max_consecutive
            )
            providers[provider_name] = provider

        # Build facility volumes mapping FIRST (needed for shift creation)
        facility_volumes = {}
        for _, row in volumes_df.iterrows():
            facility = row['facility_name']
            for shift_type in ['MD1', 'MD2', 'PM']:
                vol_col = f'Volume {shift_type}'
                if vol_col in row and pd.notna(row[vol_col]):
                    try:
                        # Try to convert to float, skip if it's 'NC' or other non-numeric
                        facility_volumes[(facility, shift_type)] = float(row[vol_col])
                    except (ValueError, TypeError):
                        # Skip non-numeric values like 'NC'
                        pass

        # Build shift objects from sample schedule structure (now with volumes available)
        shifts = self._build_shifts_from_sample(shifts_df, facility_volumes)

        # Build coverage requirements based on Facility Coverage file
        coverage_required = set()
        uncoverable_shifts = []

        # Parse coverage dates for each facility-shift combination
        facility_coverage_map = {}  # (facility, shift_type) -> set of required days

        for _, row in coverage_df.iterrows():
            facility = row['Facility']
            shift_type = str(row['Shift']).strip()
            coverage_dates = row['Coverage dates']

            # Parse coverage dates
            required_days = set()
            if pd.notna(coverage_dates):
                date_str = str(coverage_dates).strip()
                # Parse formats like "1--31", "4-5, 11-12, 18-19", "5--12", etc.
                if date_str:
                    parts = date_str.split(',')
                    for part in parts:
                        part = part.strip()
                        if '--' in part:
                            # Range like "1--31"
                            start, end = part.split('--')
                            start_day = int(start.strip())
                            end_day = int(end.strip())
                            required_days.update(range(start_day, end_day + 1))
                        elif '-' in part:
                            # Range like "4-5"
                            start, end = part.split('-')
                            start_day = int(start.strip())
                            end_day = int(end.strip())
                            required_days.update(range(start_day, end_day + 1))
                        else:
                            # Single day
                            try:
                                day = int(part.strip())
                                required_days.add(day)
                            except ValueError:
                                pass

            # If no coverage dates specified, assume all days
            if not required_days:
                required_days = set(range(1, num_days + 1))

            facility_coverage_map[(facility, shift_type)] = required_days

        # Now build coverage_required based on shifts and their facility coverage
        for shift_id, shift in shifts.items():
            # Check if ANY provider is credentialed for this shift
            has_eligible_provider = False
            for provider in providers.values():
                is_credentialed = all(
                    facility in provider.credentialed_facilities
                    for facility in shift.facilities
                )
                if is_credentialed:
                    has_eligible_provider = True
                    break

            if not has_eligible_provider:
                # No provider can work this shift - don't require coverage
                uncoverable_shifts.append(shift_id)
                continue

            # Determine which days this shift needs coverage
            # A shift needs coverage on a day if ANY of its facilities needs coverage that day
            for day_idx in days:
                day_of_month = day_idx + 1  # Convert 0-indexed to 1-indexed
                needs_coverage = False

                for facility in shift.facilities:
                    # Check if this facility needs coverage for this shift type on this day
                    coverage_days = facility_coverage_map.get((facility, shift.shift_type), set())
                    if day_of_month in coverage_days:
                        needs_coverage = True
                        break

                if needs_coverage:
                    coverage_required.add((shift_id, day_idx))

        print(f"  Coverage requirement: {len(coverage_required)} shift-day combinations must be filled")
        if uncoverable_shifts:
            print(f"  ⚠️  WARNING: {len(uncoverable_shifts)} shifts have NO credentialed providers (will not be scheduled):")
            for shift_id in uncoverable_shifts[:5]:
                print(f"      - {shift_id[:70]}")

        return SchedulingData(
            providers=providers,
            shifts=shifts,
            days=days,
            date_to_day_index=date_to_day_index,
            day_index_to_date=day_index_to_date,
            weekends=weekends,
            facility_volumes=facility_volumes,
            coverage_required=coverage_required
        )

    def _load_provider_contracts(self) -> pd.DataFrame:
        """Load provider contract information"""
        df = pd.read_excel(f'{self.data_dir}/Provider contract.xlsx')
        return df

    def _load_provider_credentialing(self) -> pd.DataFrame:
        """Load provider credentialing information"""
        df = pd.read_excel(f'{self.data_dir}/Provider Credentialing.xlsx')
        return df

    def _load_provider_availability(self) -> pd.DataFrame:
        """Load provider availability calendar"""
        df = pd.read_excel(f'{self.data_dir}/Provider Availability.xlsx')
        return df

    def _load_facility_volumes(self) -> pd.DataFrame:
        """Load facility volume information"""
        df = pd.read_excel(f'{self.data_dir}/Facility Volume.xlsx')
        return df

    def _load_facility_coverage(self) -> pd.DataFrame:
        """Load facility coverage requirements"""
        df = pd.read_excel(f'{self.data_dir}/Facility Coverage.xlsx')
        # Forward fill facility names
        df['Facility'] = df['Facility'].ffill()
        return df

    def _load_sample_schedule(self) -> pd.DataFrame:
        """Load sample schedule to extract shift structure"""
        df = pd.read_excel(f'{self.data_dir}/Sample Schedule.xlsx')
        return df

    def _build_shifts_from_sample(self, sample_df: pd.DataFrame,
                                  facility_volumes: Dict[Tuple[str, str], float]) -> Dict[str, Shift]:
        """Build shift objects from sample schedule structure"""
        shifts = {}

        # Get all shift columns (skip first 2 columns which are dates)
        shift_columns = sample_df.columns[2:]

        # Volume constraints by shift type
        volume_constraints = {
            'MD1': {'min': 6, 'max': 14},
            'MD2': {'min': 8, 'max': 16},
            'PM': {'min': 5, 'max': 10}
        }

        for col_name in shift_columns:
            # Parse shift column name: "MD1 - facility1, facility2, ..."
            if ' - ' in col_name:
                parts = col_name.split(' - ', 1)
                shift_type = parts[0].strip()
                facilities_str = parts[1].strip()
                facilities = [f.strip() for f in facilities_str.split(',')]

                # Calculate expected volume for this shift
                expected_vol = 0.0
                for facility in facilities:
                    # Look up volume in the facility_volumes dictionary
                    volume_key = (facility, shift_type)
                    if volume_key in facility_volumes:
                        expected_vol += facility_volumes[volume_key]

                # Get volume constraints
                constraints = volume_constraints.get(shift_type, {'min': 0, 'max': 20})

                # Create shift ID (unique identifier)
                shift_id = col_name

                shift = Shift(
                    id=shift_id,
                    shift_type=shift_type,
                    facilities=facilities,
                    min_volume=constraints['min'],
                    max_volume=constraints['max'],
                    expected_volume=expected_vol,
                    shift_hours=12.0
                )

                shifts[shift_id] = shift

        return shifts

    def get_shift_grouping_restrictions(self) -> List[Tuple[Set[str], Set[str]]]:
        """
        Get MD2 site grouping restrictions.
        Returns list of (group1, group2) tuples that should NOT be grouped together.
        """
        restrictions = [
            # "NHMC, NMHMC" and "NMMC, NBAMC" should not be grouped
            ({'NHMC', 'NMHMC'}, {'NMMC', 'NBAMC'})
        ]
        return restrictions


if __name__ == '__main__':
    # Test data loading
    loader = DataLoader()
    data = loader.load_all_data(num_days=31)

    print(f"\nLoaded {len(data.providers)} providers")
    print(f"Loaded {len(data.shifts)} shifts")
    print(f"Scheduling for {len(data.days)} days")
    print(f"Weekend days: {len(data.weekends)}")

    # Show sample provider
    sample_provider = list(data.providers.values())[0]
    print(f"\nSample Provider: {sample_provider.name}")
    print(f"  Contract: {sample_provider.contract_type}")
    print(f"  Preferences: {sample_provider.shift_preference}")
    print(f"  Total shifts: {sample_provider.total_shift_count}")
    print(f"  Credentialed facilities: {len(sample_provider.credentialed_facilities)}")

    # Show sample shift
    sample_shift = list(data.shifts.values())[0]
    print(f"\nSample Shift: {sample_shift.id}")
    print(f"  Type: {sample_shift.shift_type}")
    print(f"  Facilities: {sample_shift.facilities[:3]}...")
    print(f"  Volume range: {sample_shift.min_volume}-{sample_shift.max_volume}")
