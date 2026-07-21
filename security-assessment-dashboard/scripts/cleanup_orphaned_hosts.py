"""One-off cleanup: remove DiscoveredHost rows (and their cascaded children --
Service/Technology/OperatingSystem/Observation/NetworkInterface/ExecutionHost/
Fingerprint/Finding) whose owning Assessment has been soft-deleted.

Context: these rows are not produced by any fallback in the execution engine
(the planner requires a real, enabled Target scoped to the assessment and
raises if none exists -- verified directly against
backend/workers/planner.py). They are genuine historical scan results from
assessments that were later soft-deleted (``Assessment.deleted_at`` set),
left behind because soft-deleting an assessment intentionally does not
cascade-delete its scan history. Run this only when that leftover data is
unwanted noise (e.g. old dev/test assessments whose discovered hosts are
cluttering the inventory/dashboard for assessments that no longer exist from
the API's point of view).

Usage (from the repo root, with the backend's venv):
    .venv\\Scripts\\python.exe scripts\\cleanup_orphaned_hosts.py          # dry run
    .venv\\Scripts\\python.exe scripts\\cleanup_orphaned_hosts.py --apply  # actually deletes
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select

from backend.database.session import background_session
from backend.models.assessment import Assessment
from backend.models.discovered_host import DiscoveredHost


async def main(apply: bool) -> None:
    async with background_session() as session:
        deleted_assessment_ids = (
            await session.execute(select(Assessment.id).where(Assessment.deleted_at.is_not(None)))
        ).scalars().all()

        if not deleted_assessment_ids:
            print("No soft-deleted assessments found. Nothing to clean up.")
            return

        orphaned_hosts = (
            await session.execute(
                select(DiscoveredHost.id, DiscoveredHost.hostname, DiscoveredHost.ipv4, DiscoveredHost.assessment_id).where(
                    DiscoveredHost.assessment_id.in_(deleted_assessment_ids)
                )
            )
        ).all()

        print(f"Soft-deleted assessments: {len(deleted_assessment_ids)}")
        print(f"Orphaned DiscoveredHost rows: {len(orphaned_hosts)}")
        for host_id, hostname, ipv4, assessment_id in orphaned_hosts:
            print(f"  - {host_id}  {ipv4 or '-'}  ({hostname or 'no hostname'})  assessment={assessment_id}")

        if not orphaned_hosts:
            print("No orphaned hosts to remove.")
            return

        if not apply:
            print("\nDry run only -- re-run with --apply to delete these rows (and their cascaded children).")
            return

        host_ids = [row[0] for row in orphaned_hosts]
        result = await session.execute(delete(DiscoveredHost).where(DiscoveredHost.id.in_(host_ids)))
        print(f"\nDeleted {result.rowcount} DiscoveredHost row(s). Dependent rows removed via ON DELETE CASCADE.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Actually delete the rows (default is dry-run).")
    args = parser.parse_args()
    asyncio.run(main(args.apply))
