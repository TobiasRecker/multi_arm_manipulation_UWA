"""Explicit selection of the new, separately commissioned hardware runtime."""
import os


def minimal_enabled():
    value = os.environ.get('UWA_PROTECTION_BACKEND', 'legacy')
    if value not in ('legacy', 'minimal'):
        raise ValueError('UWA_PROTECTION_BACKEND must be legacy or minimal')
    return value == 'minimal'
