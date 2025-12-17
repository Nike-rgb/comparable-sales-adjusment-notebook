from __future__ import annotations
from typing import Tuple, Dict

def external_market(subject, comp) -> Tuple[float, Dict]:
    # Placeholder for climate, job, walk/transit, unemployment, crime, sex offender
    # If not present from Datafiniti or similar, this returns 0 with explicit detail.
    return 0.0, {
        'climate': None, 'job': None, 'walk': None, 'transit': None, 'unemployment': None,
        'crime': None, 'sex_offender': None, 'note': 'no external market data provided'
    }

def exemptions(subject, comp) -> Tuple[float, Dict]:
    # Placeholder for Senior/Homestead/Veteran/Disability exemptions
    return 0.0, {'exemptions': None, 'note': 'no exemptions data provided'}
