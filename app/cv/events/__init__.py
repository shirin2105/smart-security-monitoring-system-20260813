"""Lifecycle signal adapters for the unified CV event engine.

Adapters are imported from their modules so lightweight contract consumers do
not eagerly load the production CV dependency graph.
"""

from .event_signal import EventSignal

__all__ = ["EventSignal"]
