"""This is the RHEL Upgrade Automation Reporting ingestion module.

This module collects playbooks and failed tasks from AAP.
Creates assumed workflows by grouping those playbooks.
Validates them, and then uploads them to Elasticsearch.
"""

__all__ = ["gather_region_data"]
__version__ = "1.0"
__name__ = "RHEL Upgrade Reporting Ingestion"

from datetime import datetime, timedelta
import json
import pytz
import requests

from elasticsearch import helpers, Elasticsearch
import pandas as pd

requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)

_ES_INDEX = "rhel_upgrade_reporting"

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


def _get_auth(cookie):
    """Returns authentication token from cookie

    Helper function that takes a copied cookie string and returns
    the appropriate token from it.
    """

    tmp = cookie.strip().split("=")
    auth = {tmp[0]: "=".join(tmp[1:])}
    return auth


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


def scrape(baseurl, endpoint, query, auth, data):
    """Generalized function for scraping paginated data from AAP

    @Param: baseurl - string - baseurl of the AAP instance
    @Param: endpoint - string - endpoint appended to baseurl
    @Param: query - string - query section of uri
    @Param: auth - string - authentication token
    @Param: data - list - list which results will be appended to

    @Return - None
    """
    print("Scraping: {}{}{}".format(baseurl, endpoint, query))
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
    """Gathers playbook information from AAP

    Gathers playbooks from AAP given a specific start time.

    @Param: region - string - Used to get AAP instance
    @Param: start_time - datetime - start time
    @Param: auth - string - authentication token

    @Return: list[dict] - Dict of playbooks
    """

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
    """Gathers failed_task information from AAP

    Gathers playbooks from AAP given a specific start time.

    @Param: playbook - dict - Playbook associated with failed task
    @Param: region - string - Used to get AAP instance
    @Param: auth - string - authentication token

    @Return: list[dict] - Dict of failed_tasks
    """

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


def generate_workflows(playbooks, region, auth, ids):
    """Group playbooks into proposed workflows by txId and limit

    @Param: playbooks - list[dict] - Playbooks
    @Param: region - string - Used to get AAP instance
    @Param: auth - string - authentication token

    @Return: dict[list[dict]] - Dict of proposed workflows
    """

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

        if play_id not in ids:
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
    """Takes playbook groups and validates if they are complete and match standards.

    @Param: workflows - dict[list[dict]] - Playbook groups
    @Param: region - string - Used to get AAP instance
    @Param: latest_job - datetime - When the latest pulled job was retrieved

    @Return: list[dict] - list of workflows
    """

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
            "workflow_done": (not failed)
            or (
                latest_job.astimezone(tz=pytz.utc) - jobs[-1]["finished"]
                > timedelta(hours=8)
            ),
        }

        format_workflow(tentative_workflow)
        res[workflow] = tentative_workflow
        if failed:
            if tentative_workflow["workflow_done"]:
                print("Workflow is invalid.")
            else:
                print("Workflow is likely not ready.")
    return res


def format_failed_task(failed_task):
    """Filter fields for failed_tasks

    @Param: failed_task - dict - A failed_task object

    @Return: None
    """

    for key in set(failed_task.keys()) - _FAILED_TASKS_KEYS:
        del failed_task[key]

    if "event_data" in failed_task:
        for ed_key in (
            set(failed_task["event_data"].keys()) - _FAILED_TASKS_EVENT_DATA_KEYS
        ):
            del failed_task["event_data"][ed_key]


def format_playbook(playbook):
    """Filter fields for playbook

    @Param: playbook - dict - A playbook object

    @Return: None
    """

    for key in set(playbook.keys()) - _PLAYBOOK_KEYS:
        del playbook[key]

    for failed_task in playbook["failed_tasks"]:
        format_failed_task(failed_task)


def format_workflow(workflow):
    """Filters fields for workflow

    @Param: workflow - dict - A workflow object

    @Return: None
    """

    for playbook in workflow["jobs"]:
        format_playbook(playbook)


def elk_search(es_client, body):
    """Generalized function to perform a search

    @Param: es_client - Elasticsearch - Elasticsearch client object
    @Param: body - string - Elasticsearch query

    @Return: dict - Hits returned
    """

    try:
        result = es_client.search(index=_ES_INDEX, body=body)
        data = []
        for hit in result["hits"]["hits"]:
            if hit:
                data.append(hit["fields"])
        return data
    except Exception as e:
        print(f"Error occurred: {e}")


def get_last_time(es_client, region):
    """Return last time data was uploaded for region

    @Param: es_client - Elasticsearch - Elasticsearch client object
    @Param: region - string - Region

    @Return: string - last time
    """

    body = {
        "size": 1,
        "sort": [{"finished": {"order": "desc"}}],
        "fields": ["finished"],
        "query": {"match": {"region": region}},
        "_source": False,
    }
    data = elk_search(es_client, body)
    if data and len(data):
        return data[0]["finished"][0]
    return None


def get_ids(es_client, region, start_time):
    """Return ids for last 24 hours before last data upload

    This helps prevent duplicates from being uploaded

    @Param: es_client - Elasticsearch - Elasticsearch client object
    @Param: region - string - Region
    @Param: start_time - string - When to start looking for ids

    @Return: list[string] - List of ids
    """

    body = {
        "size": 10000,
        "fields": ["id"],
        "query": {
            "bool": {
                "must": [
                    {"match": {"region": region}},
                    {
                        "range": {
                            "finished": {
                                "gte": start_time,
                                "lte": start_time + timedelta(hours=48),
                            }
                        }
                    },
                ]
            }
        },
        "_source": False,
    }
    data = elk_search(es_client, body)
    if data and len(data):
        return [i["id"][0] for i in data]
    return []


def gather_region_data(region, cookie):
    """Gathers data for a given region and uploads it to Elasticsearch.

    @Param: region - string - One of [amrs, emea, apac, sit, uat]
    @Param: cookie - string - Cookie to use for authentication while pulling data

    @Return: dict - Dictionary containing uploaded and non-uploaded workflows.
    """

    es_client = Elasticsearch(_ENVIRONMENTS[region]["elk"])
    last_record = get_last_time(es_client, region)
    if last_record is None:
        last_record = "2024-02-01T06:00:00.000000Z"  # First 1.14 job in AMRS
        # last_record = '2024-02-26T23:22:00.614287Z' #First 1.15.2 job in AMRS
    start_time = datetime.strptime(last_record, "%Y-%m-%dT%H:%M:%S.%f%z")
    print(f"The last {region} workflow was added at {last_record}.")
    ids = get_ids(es_client, region, start_time - timedelta(hours=24))
    if len(ids) >= 9000:
        raise Exception(
            (
                "Too many workflows have been run in the last 24 hours."
                "Configuration must be reviewed."
            )
        )
    print(f"The number of ids pulled is {len(ids)}")

    auth = _get_auth(cookie)
    playbooks = get_playbooks(region, start_time - timedelta(hours=12), auth)
    playbook_groups = generate_workflows(playbooks, region, auth, ids)
    workflows = validate_workflows(playbook_groups, region, playbooks[-1]["finished"])

    res = {"uploaded_workflows": [], "non_uploaded_workflows": []}
    for workflow_id, workflow in workflows.items():
        # if len(workflow_id) <= len('tx_3b47b3e6-cabf-4a3f-9735-5838e1ea2b3a'):
        # print('blah', workflow_id)
        if workflow_id in ids:
            # print(f"{workflow_id} is already in IDS")
            continue
        elif workflow["workflow_done"]:
            workflow["_index"] = _ES_INDEX
            res["uploaded_workflows"].append(workflow)
        else:
            res["non_uploaded_workflows"].append(workflow)

    try:
        # for i in res['uploaded_workflows']:
        #     print(i)
        #     res = es_client.index(index=_ES_INDEX, id=i['id'], document=i)
        helpers.bulk(es_client, res["uploaded_workflows"])
    except Exception as e:
        print(e)
    return res
