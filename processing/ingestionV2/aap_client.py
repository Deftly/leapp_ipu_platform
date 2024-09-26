import requests
from datetime import datetime, timedelta
from logger import get_logger
from utils import retry_with_backoff

logger = get_logger(__name__)


class AAPClient:
    _PLAYBOOK_KEYS = {
        "id",
        "type",
        "created",
        "name",
        "status",
        "failed",
        "started",
        "finished",
        "timeout",
        "elapsed",
        "timed_out",
        "limit",
        "extra_vars",
        "failed_tasks",
        "release",
    }

    _FAILED_TASKS_KEYS = {
        "id",
        "type",
        "created",
        "modified",
        "job",
        "event",
        "event_display",
        "event_data",
        "event_level",
        "failed",
        "changed",
        "task",
        "role",
        "stdout",
    }

    _FAILED_TASKS_EVENT_DATA_KEYS = {
        "resolved_action",
        "task_args",
        "remote_addr",
        "host",
        "res",
        "duration",
        "start",
        "end",
    }

    def __init__(self, config):
        self.config = config
        self.sessions = {}
        for region in self.config.regions:
            session = requests.Session()
            session.verify = False
            session.cookies.update(self._parse_cookie(self.config.aap_cookies[region]))
            self.sessions[region] = session
        requests.packages.urllib3.disable_warnings(
            requests.packages.urllib3.exceptions.InsecureRequestWarning
        )

    def _parse_cookie(self, cookie_string):
        cookie_parts = cookie_string.split("=", 1)
        return {cookie_parts[0]: cookie_parts[1]}

    @retry_with_backoff(max_retries=3, backoff_in_seconds=1)
    def get_new_jobs(self, region, last_processed_time):
        base_url = self.config.aap_base_urls[region]
        endpoint = "/api/v2/jobs/"

        start_time = last_processed_time - timedelta(hours=12)

        query = (
            f"?format=json&name__icontains=leapp&not__finished__isnull=true"
            f"&type=job"
            f"&created__gt={start_time.isoformat()}"
            f"&page_size={self.config.aap_page_size}"
        )

        url = f"{base_url}{endpoint}{query}"

        jobs = []
        while url:
            response = self.sessions[region].get(url)
            response.raise_for_status()
            data = response.json()
            filtered_jobs = [self._filter_job_data(job) for job in data["results"]]
            for job in filtered_jobs:
                if job["failed"]:
                    job["failed_tasks"] = self.get_failed_tasks(job["id"], region)
            jobs.extend(filtered_jobs)
            url = data["next"]

        logger.info(f"Fetched {len(jobs)} new jobs for region {region}")
        return jobs

    @retry_with_backoff(max_retries=3, backoff_in_seconds=1)
    def get_failed_tasks(self, job_id, region):
        base_url = self.config.aap_base_urls[region]
        url = f"{base_url}/api/v2/jobs/{job_id}/job_events/?failed=true"

        response = self.sessions[region].get(url)
        response.raise_for_status()
        data = response.json()

        failed_tasks = [
            self._filter_failed_task_data(task)
            for task in data["results"]
            if task["event_level"] in [0, 3]
        ]
        return failed_tasks

    def _filter_job_data(self, job):
        return {k: v for k, v in job.items() if k in self._PLAYBOOK_KEYS}

    def _filter_failed_task_data(self, task):
        filtered_task = {k: v for k, v in task.items() if k in self._FAILED_TASKS_KEYS}
        if "event_data" in filtered_task:
            filtered_task["event_data"] = {
                k: v
                for k, v in filtered_task["event_data"].items()
                if k in self._FAILED_TASKS_EVENT_DATA_KEYS
            }
        return filtered_task
