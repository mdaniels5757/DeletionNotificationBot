"""Pure orchestration for consuming and notifying deletion nominations."""

import logging
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from models import NominationCodec
from policies import SIGNATURE, category_policies, edit_summary, render_notice

logger = logging.getLogger(__name__)


class NotifierService:
    def __init__(self, transport, codec: NominationCodec, wiki, today=date.today):
        self.transport = transport
        self.codec = codec
        self.wiki = wiki
        self.today = today

    def _policies(self):
        # Dynamic categories can have been published just before midnight.
        day = self.today()
        current = category_policies(day)
        current.update(category_policies(day - timedelta(days=1)))
        return current

    def process_once(self) -> int:
        policies = self._policies()
        groups = defaultdict(list)
        for marker, _, key in self.transport.mature_markers():
            value = self.transport.get(key)
            if not value:
                continue
            nomination = self.codec.decode(value).with_marker(Path(marker))
            if nomination.deletion_category not in policies:
                continue
            groups[(nomination.deletion_category, nomination.uploader)].append(
                nomination
            )

        preferences = {
            uploader: self.wiki.notification_preferences(uploader)
            for uploader in {uploader for _, uploader in groups}
        }
        submissions = 0
        for (category, uploader), nominations in groups.items():
            policy = policies[category]
            settings = preferences[uploader]
            if not settings.notifications:
                for item in nominations:
                    self.transport.acknowledge(item.marker_path)
                continue
            eligible = [
                item
                for item in nominations
                if self.wiki.is_notifiable(item, policy.needs_subpage)
            ]
            # The legacy notifier removes markers for all explicitly suppressed items.
            for item in nominations:
                # AntiCompositeBot suppression intentionally leaves the marker for the
                # existing expiry pruner, matching the former notifier.
                if item not in eligible and item.nominator != "AntiCompositeBot":
                    self.transport.acknowledge(item.marker_path)
            if not eligible:
                continue
            if not settings.notify_redirects:
                try:
                    redirects = [item for item in eligible if self.wiki.is_redirect(item)]
                except Exception:
                    logger.exception(
                        "Could not check redirects for %s in %s", uploader, category
                    )
                    continue
                for item in redirects:
                    self.transport.acknowledge(item.marker_path)
                eligible = [item for item in eligible if item not in redirects]
                if not eligible:
                    continue
            notice = render_notice(policy, eligible) + SIGNATURE
            self.wiki.submit(uploader, notice, edit_summary(category, eligible))
            for item in eligible:
                self.transport.acknowledge(item.marker_path)
            submissions += 1
        return submissions
