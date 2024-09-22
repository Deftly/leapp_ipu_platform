import requests
from datetime import datetime, timedelta
from logger import get_logger

logger = get_logger(__name__)


class AAPClient:
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification
        requests.packages.urllib3.disable_warnings(
            requests.packages.urllib3.exceptions.InsecureRequestWarning
        )

    def get_new_jobs(self, region, last_processed_time):
        base_url = self.config.aap_base_urls[region]
        endpoint = "/api/v2/jobs/"

        # Add a 12-hour overlap to ensure we don't miss any jobs
        start_time = last_processed_time - timedelta(hours=12)

        query = (
            '?format=json&name__icontains=leapp&not__finished__isnull=true'
            '&type=job'
            f'&created__gt={start_time.strftime("%Y-%m-%dT%H:%M:%SZ")}'
        )

        url = f"{base_url}{endpoint}{query}"

        jobs = []
        while url:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            jobs.extend(data["results"])
            url = data["next"]

        logger.info(f"Fetched {len(jobs)} new jobs for region {region}")
        return jobs

    def get_failed_tasks(self, job_id, region):
        base_url = self.config.aap_base_urls[region]
        url = f"{base_url}/api/v2/jobs/{job_id}/job_events/?failed=true"

        response = self.session.get(url)
        response.raise_for_status()
        data = response.json()

        failed_tasks = [
            task for task in data["results"] if task["event_level"] in [0, 3]
        ]
        return failed_tasks
