"""
This module collects playbooks and failed tasks from AAP.
Creates assumed workflows by grouping those playbooks.
Validates them and uploads them to Elasticsearch.
It now includes support for in-progress workflows and changes to data fetching logic.
"""

import json
from datetime import datetime, timedelta
import pytz

import requests
import urllib3
from elasticsearch import helpers, Elasticsearch
import pandas as pd

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_ES_INDEX = "rhel_upgrade_reporting_test_processing"

_PLAYBOOK_KEYS = set(
    [
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
    ]
)

_FAILED_TASKS_KEYS = set(
    [
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
    ]
)

_FAILED_TASKS_EVENT_DATA_KEYS = set(
    [
        "resolved_action",
        "task_args",
        "remote_addr",
        "host",
        "res",
        "duration",
        "start",
        "end",
    ]
)

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

_ENVIRONMENTS = {
    "amrs": {
        "tower": "https://asl-tower.bankofamerica.com",
        "elk": "http://ah-1006969-001.sdi.corp.bankofamerica.com:9200",
        "lane": "PROD",
    },
    "apac": {
        "tower": "https://asl-tower-apac.bankofamerica.com",
        "elk": "http://ah-1006969-001.sdi.corp.bankofamerica.com:9200",
        "lane": "PROD",
    },
    "emea": {
        "tower": "https://asl-tower-emea.bankofamerica.com",
        "elk": "http://ah-1006969-001.sdi.corp.bankofamerica.com:9200",
        "lane": "PROD",
    },
    "dmz": {
        "tower": "https://asl-towerb2d.bankofamerica.com",
        "elk": "http://ah-1006969-001.sdi.corp.bankofamerica.com:9200",
        "lane": "PROD",
    },
    "uat": {
        "tower": "https://asl-tower-uat.bankofamerica.com",
        "elk": "http://ah-1254727-001.sdi.corp.bankofamerica.com:9200",
        "lane": "UAT",
    },
    "sit": {
        "tower": "https://asl-tower-sit.bankofamerica.com",
        "elk": "http://ah-1280330-001.sdi.corp.bankofamerica.com:9200",
        "lane": "SIT",
    },
}

_PAGES = "200"


def _mode(l):
    """Calculates mode from a set of values."""

    res = {}
    for item in l:
        if item in res:
            res[item] += 1
        else:
            res[item] = 1
    m = max(res.values())
    ret = []
    for k in res:
        if res[k] == m:
            ret.append(k)
    return ret


def _get_auth(cookie):
    """Returns authentication token from cookie"""
    tmp = cookie.strip().split("=")
    auth = {tmp[0]: "=".join(tmp[1:])}
    return auth


def scrape(baseurl, endpoint, query, auth, data):
    """Generalized function for scraping paginated data from AAP"""
    print("Scrapping: {}{}{}".format(baseurl, endpoint, query))
    try:
        response = requests.get(
            "{}{}{}".format(baseurl, endpoint, query), cookies=auth, verify=False
        )
        tmp = response.json()
        if "results" in tmp:
            data.extend(tmp["results"])
        if "next" in tmp and tmp["next"]:
            if f"page={_PAGES}" not in tmp["next"]:
                scrape(baseurl, tmp["next"], "", auth, data)
    except Exception as e:
        print("Error: {}".format(e))


def get_playbooks(region, start_time, auth):
    """Gathers playbook information from AAP"""
    baseurl = _ENVIRONMENTS[region]["tower"]
    endpoint = "/api/v2/jobs/"
    query = (
        '?format=json&name__icontains=leapp&not__finished__isnull=true'
        '&type=job'
        f'&created__gt={start_time.strftime("%Y-%m-%dT%H:%M:%SZ")}'
    )
    data = []
    scrape(baseurl, endpoint, query, auth, data)
    return data


def get_failed_tasks(playbook, region, auth):
    """Gathers failed_task information from AAP"""
    if not playbook["failed"]:
        return []
    baseurl = _ENVIRONMENTS[region]["tower"]
    job_filter = "?failed=true"
    failed_tasks = []
    scrape(
        baseurl,
        f"/api/v2/jobs/{playbook['id']}/job_events/",
        job_filter,
        auth,
        failed_tasks,
    )
    failed_tasks = list(filter(lambda x: x["event_level"] in [0, 3], failed_tasks))
    return failed_tasks


def generate_workflows(playbooks, region, auth, existing_ids):
    """Group playbooks into proposed workflows by txId and limit"""
    workflows = {}

    for playbook in playbooks:
        playbook["created"] = datetime.strptime(
            playbook["created"], "%Y-%m-%dT%H:%M:%S.%f%z"
        )
        playbook["started"] = datetime.strptime(
            playbook["started"], "%Y-%m-%dT%H:%M:%S.%f%z"
        )
        playbook["finished"] = datetime.strptime(
            playbook["finished"], "%Y-%m-%dT%H:%M:%S.%f%z"
        )
        playbook["extra_vars"] = json.loads(playbook["extra_vars"])
        playbook["automation_failure"] = playbook["failed"]
        playbook["release"] = (playbook["name"].split("_")[-1],)
        playbook["timed_out"] = playbook["elapsed"] >= playbook["timeout"]

        try:
            play_id = "{}-{}".format(playbook["extra_vars"]["txId"], playbook["limit"])
        except Exception as e:
            print(e)
            print(playbook)
            continue

        if play_id not in existing_ids:
            playbook["failed_tasks"] = get_failed_tasks(playbook, region, auth)

            for failed_task in playbook["failed_tasks"]:
                if failed_task["task"] in _NON_AUTOMATION_FAILURES:
                    failed_task["automation_failure"] = False
                else:
                    failed_task["automation_failure"] = True

            if playbook["automation_failure"] and not any(
                [i["automation_failure"] for i in playbook["failed_tasks"]]
            ):
                playbook["automation_failure"] = False

        else:
            playbook["failed_tasks"] = []

        if play_id in workflows:
            workflows[play_id].append(playbook)
        else:
            workflows[play_id] = [playbook]

    return workflows


def validate_workflows(workflows, region, latest_job):
    """Takes playbook groups and validates if they are complete and match standards."""
    res = {}
    for workflow in workflows:
        jobs = workflows[workflow]
        workflow_determinator = _mode([i["extra_vars"]["major_workflow"] for i in jobs])
        if len(workflow_determinator) > 1:
            print(f"Non Determistic: {jobs[0]['id']} {jobs[0]['extra_vars']['txId']}")
        workflow_type = workflow_determinator[0]
        workflow_failed = any([i["failed"] for i in jobs])
        workflow_automation_failure = workflow_failed
        if workflow_automation_failure and not any(
            [i["automation_failure"] for i in jobs]
        ):
            workflow_automation_failure = False

        failed = False

        if workflow_type == "operational_check_7_to_8":
            if len(jobs) > 1:
                print(
                    (
                        "Invalid Operational Check 7 to 8 Workflow: "
                        f"{workflow_type} {jobs[0]['id']} {jobs[0]['extra_vars']['txId']}"
                    )
                )
                print([i["id"] for i in jobs])
                failed = True
            pass
        elif workflow_type == "operational_check_7_to_9":
            if len(jobs) > 1:
                print(
                    (
                        "Invalid Operational Check 7 to 9 Workflow: "
                        f"{workflow_type} {jobs[0]['id']} {jobs[0]['extra_vars']['txId']}"
                    )
                )
                print([i["id"] for i in jobs])
                failed = True
            pass
        elif workflow_type == "operational_check_8_to_9":
            if len(jobs) > 1:
                print(
                    (
                        "Invalid Operational Check 8 to 9 Workflow: "
                        f"{workflow_type} {jobs[0]['id']} {jobs[0]['extra_vars']['txId']}"
                    )
                )
                print([i["id"] for i in jobs])
                failed = True
            pass
        elif workflow_type == "inhibitor_check_7_to_8":
            if (
                len(jobs) == 1
                and ("operational" in jobs[0]["name"])
                and workflow_failed
            ):
                pass
            elif len(jobs) == 3 and (
                "rollback" in jobs[-1]["extra_vars"]["changefile_tasks_from"]
            ):
                pass
            else:
                print(
                    (
                        "Invalid Inhibitor Check 7 to 8 Workflow: "
                        f"{workflow_type} {jobs[0]['id']} {jobs[0]['extra_vars']['txId']}"
                    )
                )
                print([i["id"] for i in jobs])
                failed = True
        elif workflow_type == "inhibitor_check_8_to_9":
            if (
                len(jobs) == 1
                and ("operational" in jobs[0]["name"])
                and workflow_failed
            ):
                pass
            elif len(jobs) == 3 and (
                "rollback" in jobs[-1]["extra_vars"]["changefile_tasks_from"]
            ):
                pass
            else:
                print(
                    (
                        "Invalid Inhibitor Check 8 to 9 Workflow: "
                        f"{workflow_type} {jobs[0]['id']} {jobs[0]['extra_vars']['txId']}"
                    )
                )
                print([i["id"] for i in jobs])
                failed = True
        elif workflow_type == "upgrade_7_to_8":
            if workflow_failed and (
                "vastool_revert" in jobs[-1]["extra_vars"]["sub_workflow"]
            ):
                pass
            elif (
                (not workflow_failed)
                and ("changefile_included_role" in jobs[-1]["extra_vars"].keys())
                and (
                    "postupgrade_7_to_8"
                    in jobs[-1]["extra_vars"]["changefile_included_role"]
                )
            ):
                pass
            else:
                print(
                    (
                        "Invalid Invalid or Incomplete Upgrade 7 to 8 Workflow: "
                        f"{workflow_type} {jobs[0]['id']} {jobs[0]['extra_vars']['txId']}"
                    )
                )
                print([i["id"] for i in jobs])
                failed = True
        elif workflow_type == "upgrade_8_to_9":
            if workflow_failed and (
                "vastool_revert" in jobs[-1]["extra_vars"]["sub_workflow"]
            ):
                pass
            elif (
                (not workflow_failed)
                and ("changefile_included_role" in jobs[-1]["extra_vars"].keys())
                and (
                    "postupgrade_8_to_9"
                    in jobs[-1]["extra_vars"]["changefile_included_role"]
                )
            ):
                pass
            else:
                print(
                    (
                        "Invalid Invalid or Incomplete Upgrade 8 to 9 Workflow: "
                        f"{workflow_type} {jobs[0]['id']} {jobs[0]['extra_vars']['txId']}"
                    )
                )
                print(jobs[-1]["extra_vars"].keys())
                print([i["id"] for i in jobs])
                failed = True
        elif workflow_type == "upgrade_7_to_9":
            if workflow_failed and (
                "vastool_revert" in jobs[-1]["extra_vars"]["sub_workflow"]
            ):
                pass
            elif (
                (not workflow_failed)
                and ("changefile_included_role" in jobs[-1]["extra_vars"])
                and (
                    "postupgrade_8_to_9"
                    in jobs[-1]["extra_vars"]["changefile_included_role"]
                )
            ):
                pass
            else:
                print(
                    (
                        "Invalid Invalid or Incomplete Upgrade 7 to 9 Workflow: "
                        f"{workflow_type} {jobs[0]['id']} {jobs[0]['extra_vars']['txId']}"
                    )
                )
                print([i["id"] for i in jobs])
                failed = True
        else:
            print(
                (
                    "Invalid Workflow Type: "
                    f"{workflow_type} {jobs[0]['id']} {jobs[0]['extra_vars']['txId']}"
                )
            )
            failed = True

        workflow_status = "completed" if not failed else "in_progress"

        tentative_workflow = {
            "failed_validation": failed,
            "region": region,
            "id": workflow,
            "workflow_type": workflow_type,
            "jobs": jobs,
            "failed": workflow_failed,
            "type": "workflow",
            "release": jobs[0]["name"].split("_")[-1],
            "started": jobs[0]["created"],
            "finished": jobs[-1]["finished"],
            "limit": jobs[0]["limit"],
            "automation_failure": workflow_automation_failure,
            "workflow_status": workflow_status,
            "last_updated": jobs[-1]["finished"],
        }

        format_workflow(tentative_workflow)
        res[workflow] = tentative_workflow

    return res


def format_failed_task(failed_task):
    """Filter fields for failed_tasks"""
    for key in set(failed_task.keys()) - _FAILED_TASKS_KEYS:
        del failed_task[key]

    if "event_data" in failed_task:
        for ed_key in (
            set(failed_task["event_data"].keys()) - _FAILED_TASKS_EVENT_DATA_KEYS
        ):
            del failed_task["event_data"][ed_key]


def format_playbook(playbook):
    """Filter fields for playbook"""
    for key in set(playbook.keys()) - _PLAYBOOK_KEYS:
        del playbook[key]

    for failed_task in playbook["failed_tasks"]:
        format_failed_task(failed_task)


def format_workflow(workflow):
    """Filters fields for workflow"""
    for playbook in workflow["jobs"]:
        format_playbook(playbook)


def elk_search(es_client, body):
    """Generalized function to perform a search"""
    try:
        result = es_client.search(index=_ES_INDEX, body=body)
        data = []
        for hit in result["hits"]["hits"]:
            if hit:
                data.append(hit["_source"])
        return data
    except Exception as e:
        print(f"Error occurred: {e}")


def get_data_fetch_start_time(es_client, region):
    """Determine the start time for data fetching"""
    # Find the oldest in-progress workflow
    in_progress_body = {
        "size": 1,
        "sort": [{"started": {"order": "asc"}}],
        "query": {
            "bool": {
                "must": [
                    {"match": {"region": region}},
                    {"match": {"workflow_status": "in_progress"}},
                ]
            }
        },
    }
    in_progress_data = elk_search(es_client, in_progress_body)

    if in_progress_data:
        return datetime.strptime(
            in_progress_data[0]["started"], "%Y-%m-%dT%H:%M:%S.%f%z"
        )

    # If no in-progress workflows, find the most recent completed workflow
    completed_body = {
        "size": 1,
        "sort": [{"finished": {"order": "desc"}}],
        "query": {
            "bool": {
                "must": [
                    {"match": {"region": region}},
                    {"match": {"workflow_status": "completed"}},
                ]
            }
        },
    }
    completed_data = elk_search(es_client, completed_body)

    if completed_data:
        return datetime.strptime(
            completed_data[0]["finished"], "%Y-%m-%dT%H:%M:%S.%f%z"
        )

    # If no data at all, use a default start time
    return datetime.strptime("2024-02-01T06:00:00.000000Z", "%Y-%m-%dT%H:%M:%S.%f%z")


def get_existing_workflow_ids(es_client, region, start_time):
    """Get existing workflow IDs to avoid duplicates"""
    body = {
        "size": 10000,
        "query": {
            "bool": {
                "must": [
                    {"match": {"region": region}},
                    {"range": {"started": {"gte": start_time.isoformat()}}},
                ]
            }
        },
        "_source": ["id"],
    }
    results = elk_search(es_client, body)

    if results is None or not results:
        print(f"No existing workflows found for region {region} since {start_time}")
        return set()

    try:
        return set(hit["id"] for hit in results if "id" in hit)
    except Exception as e:
        print(f"Error processing workflow IDs: {e}")
        return set()


def gather_region_data(region, cookie):
    """Gathers data for a given region and uploads it to Elasticsearch."""
    es_client = Elasticsearch(_ENVIRONMENTS[region]["elk"])

    # Get the start time for data fetching
    start_time = get_data_fetch_start_time(es_client, region)

    # Add 6-hour buffer
    start_time -= timedelta(hours=6)

    print(f"Fetching data for {region} from {start_time}")

    auth = _get_auth(cookie)
    playbooks = get_playbooks(region, start_time, auth)

    # Get existing workflow IDs to avoid duplicates
    existing_ids = get_existing_workflow_ids(es_client, region, start_time)

    playbook_groups = generate_workflows(playbooks, region, auth, existing_ids)
    workflows = validate_workflows(
        playbook_groups, region, playbooks[-1]["finished"] if playbooks else None
    )

    res = {"uploaded_workflows": [], "updated_workflows": []}
    for workflow_id, workflow in workflows.items():
        if workflow_id in existing_ids:
            res["updated_workflows"].append(
                {
                    "_op_type": "update",
                    "_index": _ES_INDEX,
                    "_id": workflow_id,
                    "doc": workflow,
                }
            )
        else:
            res["uploaded_workflows"].append(
                {
                    "_op_type": "index",
                    "_index": _ES_INDEX,
                    "_id": workflow_id,
                    "_source": workflow,
                }
            )

    # Perform bulk operation for both updates and new inserts
    if res["updated_workflows"] or res["uploaded_workflows"]:
        actions = res["updated_workflows"] + res["uploaded_workflows"]
        success, failed = helpers.bulk(es_client, actions, stats_only=True)
        print(f"Bulk operation completed. Successful: {success}, Failed: {failed}")

    return res


# Main execution
if __name__ == "__main__":
    # Example usage
    region = "amrs"  # Replace with actual region
    cookie = "your_cookie_here"  # Replace with actual cookie
    result = gather_region_data(region, cookie)
    print(f"Uploaded workflows: {len(result['uploaded_workflows'])}")
    print(f"Updated workflows: {len(result['updated_workflows'])}")
