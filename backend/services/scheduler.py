"""
Wiki Scheduler - APScheduler daemon managing sync and maintenance jobs.
One IntervalTrigger job per ConnectorBinding.
One CronTrigger job per vault for weekly maintenance.
max_instances=1 prevents overlapping runs.
"""

import logging
import re
from typing import Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from .vault_manager import VaultManager

logger = logging.getLogger(__name__)


def _parse_interval(interval_str: str) -> Dict:
    """Parse '6h', '30m', '1d' into APScheduler IntervalTrigger kwargs."""
    match = re.match(r"^(\d+)([mhd])$", interval_str.strip())
    if not match:
        logger.warning("Could not parse interval '%s', defaulting to 6h", interval_str)
        return {"hours": 6}
    value = int(match.group(1))
    unit = match.group(2)
    if unit == "m":
        return {"minutes": value}
    if unit == "h":
        return {"hours": value}
    if unit == "d":
        return {"days": value}
    return {"hours": 6}


class WikiScheduler:
    def __init__(self, vault_manager: VaultManager, url_enricher=None, maintenance_cfg: Dict = None):
        self.vault_manager = vault_manager
        self.url_enricher = url_enricher
        self.maintenance_cfg = maintenance_cfg or {"enabled": True, "day_of_week": "sun", "hour": 2}
        self.scheduler = BackgroundScheduler(daemon=True)
        self._register_jobs()

    def _register_jobs(self):
        for binding in self.vault_manager.get_all_bindings():
            job_id = f"sync_{binding.vault_name}_{binding.source_name}"
            interval_kwargs = _parse_interval(binding.sync_interval)
            self.scheduler.add_job(
                func=self._sync_job,
                trigger=IntervalTrigger(**interval_kwargs),
                id=job_id,
                args=[binding.source_name, binding.vault_name],
                max_instances=1,
                replace_existing=True,
                misfire_grace_time=300,
            )
            logger.info("Registered sync job: %s (%s)", job_id, binding.sync_interval)

        if self.maintenance_cfg.get("enabled"):
            for vault_name in self.vault_manager.vaults:
                job_id = f"maintenance_{vault_name}"
                self.scheduler.add_job(
                    func=self._maintenance_job,
                    trigger=CronTrigger(
                        day_of_week=self.maintenance_cfg.get("day_of_week", "sun"),
                        hour=self.maintenance_cfg.get("hour", 2),
                    ),
                    id=job_id,
                    args=[vault_name],
                    max_instances=1,
                    replace_existing=True,
                )
                logger.info("Registered maintenance job: %s (weekly)", job_id)

    def _sync_job(self, source_name: str, vault_name: str):
        logger.info("Sync job starting: %s -> %s", source_name, vault_name)
        try:
            connector = self.vault_manager.get_connector(source_name)
            wiki_manager = self.vault_manager.get_wiki_manager(vault_name)
            binding = self._get_binding(source_name, vault_name)
            needs_enricher = binding and (binding.enrich_from_url or binding.enrich_from_content)
            enricher = self.url_enricher if needs_enricher else None
            result = connector.sync(wiki_manager, binding, enricher)
            logger.info(
                "Sync complete: %s -> %s | fetched=%d synced=%d updated=%d errors=%d",
                source_name,
                vault_name,
                result.items_fetched,
                result.items_synced,
                result.items_updated,
                len(result.errors),
            )
            if result.errors:
                for err in result.errors:
                    logger.warning("Sync error (%s -> %s): %s", source_name, vault_name, err)
        except Exception as e:
            logger.error("Sync job failed (%s -> %s): %s", source_name, vault_name, e)

    def _maintenance_job(self, vault_name: str):
        logger.info("Maintenance job starting: %s", vault_name)
        try:
            wiki_manager = self.vault_manager.get_wiki_manager(vault_name)
            result = wiki_manager.lint()
            logger.info(
                "Maintenance %s: orphaned=%d broken_links=%d",
                vault_name,
                len(result.get("orphaned_pages", [])),
                len(result.get("broken_links", [])),
            )
        except Exception as e:
            logger.error("Maintenance job failed (%s): %s", vault_name, e)

    def _get_binding(self, source_name: str, vault_name: str):
        for binding in self.vault_manager.get_all_bindings():
            if binding.source_name == source_name and binding.vault_name == vault_name:
                return binding
        return None

    def trigger_sync(self, source_name: str, vault_name: str) -> Dict:
        """Manually trigger a sync job and return the result synchronously."""
        logger.info("Manual sync triggered: %s -> %s", source_name, vault_name)
        try:
            connector = self.vault_manager.get_connector(source_name)
            wiki_manager = self.vault_manager.get_wiki_manager(vault_name)
            binding = self._get_binding(source_name, vault_name)
            if not binding:
                raise ValueError(
                    f"No binding found for source={source_name} vault={vault_name}"
                )
            needs_enricher = binding.enrich_from_url or binding.enrich_from_content
            enricher = self.url_enricher if needs_enricher else None
            result = connector.sync(wiki_manager, binding, enricher)
            return result.to_dict()
        except Exception as e:
            logger.error("Manual sync failed (%s -> %s): %s", source_name, vault_name, e)
            raise

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("WikiScheduler started with %d jobs", len(self.scheduler.get_jobs()))

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("WikiScheduler stopped")

    def get_status(self) -> Dict:
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            })
        return {
            "running": self.scheduler.running,
            "jobs": jobs,
        }
