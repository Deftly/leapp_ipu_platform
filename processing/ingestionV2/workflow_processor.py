from datetime import datetime, timezone
from logger import get_logger

logger = get_logger(__name__)


class WorkflowProcessor:
    _NON_AUTOMATION_FAILURES = {
        "Check for NFS mounts": [],
        "Ensure Changefile Directory Exists": [],
        "Check for inhibitors": [],
        "Fail if any previous stage failed": [],
        "Call error in order to fail stage.": [],
        "Change the permission of bootloader file to 700": [],
        "Gathering Facts": [],
        "Run Setup Module": [],
        "Validating arguments against arg spec 'os_verification' - Verifies OS Version": [],
        "Backup /etc/bac.conf": [],
    }

    def __init__(self, config):
        self.config = config

    def process_jobs(self, jobs):
        workflows = {}

        for job in jobs:
            workflow_id = f"{job['extra_vars']['txId']}-{job['limit']}"

            if workflow_id not in workflows:
                workflows[workflow_id] = {
                    "id": workflow_id,
                    "region": job["region"],
                    "workflow_type": job["extra_vars"]["major_workflow"],
                    "jobs": [],
                    "status": "in_progress",
                    "started": job["created"],
                    "finished": None,
                    "failed": False,
                    "automation_failure": False,
                }

            workflows[workflow_id]["jobs"].append(job)

            # Update workflow status
            if job["status"] == "failed":
                workflows[workflow_id]["failed"] = True
                workflows[workflow_id]["automation_failure"] = (
                    self._check_automation_failure(job)
                )

            # Update finished time
            job_finished = self._parse_datetime(job["finished"])
            if job_finished and (
                not workflows[workflow_id]["finished"]
                or job_finished > workflows[workflow_id]["finished"]
            ):
                workflows[workflow_id]["finished"] = job_finished

        # Determine final workflow status
        for workflow in workflows.values():
            if all(job["status"] == "successful" for job in workflow["jobs"]):
                workflow["status"] = "completed"
            elif any(job["status"] == "failed" for job in workflow["jobs"]):
                workflow["status"] = "failed"

        logger.info(f"Processed {len(workflows)} workflows")
        return list(workflows.values())

    def _check_automation_failure(self, job):
        # Implement logic to determine if the failure is an automation failure
        # This might involve checking the failed tasks or other job details
        for failed_task in job.get("failed_tasks", []):
            if failed_task["task"] not in self._NON_AUTOMATION_FAILURES:
                return True
        return False

    def _parse_datetime(self, dt_string):
        if dt_string:
            return datetime.fromisoformat(dt_string).replace(tzinfo=timezone.utc)
        return None
