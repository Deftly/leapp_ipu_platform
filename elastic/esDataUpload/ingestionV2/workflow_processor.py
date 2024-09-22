from logger import get_logger

logger = get_logger(__name__)


class WorkflowProcessor:
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
            if job["finished"] > workflows[workflow_id]["finished"]:
                workflows[workflow_id]["finished"] = job["finished"]

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
        pass
