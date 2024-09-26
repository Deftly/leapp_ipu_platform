from elasticsearch import Elasticsearch, helpers
from datetime import datetime, timezone
from logger import get_logger
from utils import retry_with_backoff

logger = get_logger(__name__)


class ElasticsearchClient:
    def __init__(self, config):
        self.config = config
        self.es = Elasticsearch([config.es_url])
        self.index = config.es_index

    @retry_with_backoff(max_retries=3, backoff_in_seconds=1)
    def get_last_processed_time(self, region):
        query = {
            "size": 1,
            "sort": [{"finished": {"order": "desc"}}],
            "query": {"match": {"region": region}},
        }

        result = self.es.search(index=self.index, body=query)

        if result["hits"]["hits"]:
            return datetime.fromisoformat(
                result["hits"]["hits"][0]["_source"]["finished"]
            )
        else:
            return datetime(2024, 2, 1, 6, 0, 0, tzinfo=timezone.utc)

    @retry_with_backoff(max_retries=3, backoff_in_seconds=1)
    def update_workflows(self, workflows):
        actions = []
        for workflow in workflows:
            action = {
                "_op_type": "update",
                "_index": self.index,
                "_id": workflow["id"],
                "doc": workflow,
                "doc_as_upsert": True,
            }
            actions.append(action)

        if actions:
            helpers.bulk(self.es, actions)
            logger.info(f"Updated {len(actions)} workflows in Elasticsearch")
