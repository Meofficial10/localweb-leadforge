from __future__ import annotations

from app.config import settings
from app.core.settings_service import get_setting, is_channel_paused, is_system_paused


def effective_channel_mode(db, channel: str, campaign_mode: str = 'dry_run') -> str:
    """Return the EFFECTIVE mode for a channel: dry_run beats live always.

    Effective mode is LIVE only when ALL of these hold:
      - settings.force_dry_run is False (global kill of live)
      - the channel is not paused
      - campaign.mode == 'live' (or channel allowed via enable_live_modes)
    Otherwise it is 'dry_run'. The UI must show this value, never the raw
    campaign.mode, so a forced dry-run can never display as live."""
    if settings.force_dry_run:
        return 'dry_run'
    if is_system_paused(db):
        return 'dry_run'
    if is_channel_paused(db, channel):
        return 'dry_run'
    allowed = {c.strip() for c in (settings.enable_live_modes or '').split(',') if c.strip()}
    if channel not in allowed:
        return 'dry_run'
    return 'live' if campaign_mode == 'live' else 'dry_run'


def effective_campaign_modes(db, campaign) -> dict:
    """Per-channel effective modes for a campaign."""
    if campaign is None:
        return {
            'email': effective_channel_mode(db, 'email', 'dry_run'),
            'voice': effective_channel_mode(db, 'voice', 'dry_run'),
        }
    return {
        'email': effective_channel_mode(db, 'email', campaign.mode or 'dry_run'),
        'voice': effective_channel_mode(db, 'voice', campaign.mode or 'dry_run'),
    }