import time
from config import Config
from aap_client import AAPClient
from elasticsearch_client import ElasticsearchClient
from workflow_processor import WorkflowProcessor
from logger import setup_logger

logger = setup_logger()


def main():
    config = Config()
    aap_client = AAPClient(config)
    es_client = ElasticsearchClient(config)
    workflow_processor = WorkflowProcessor(config)

    while True:
        try:
            for region in config.regions:
                logger.info(f"Starting data collection for region: {region}")

                # Get the timestamp of the last processed job
                last_processed_time = es_client.get_last_processed_time(region)

                # Fetch new jobs from AAP
                new_jobs = aap_client.get_new_jobs(region, last_processed_time)

                if not new_jobs:
                    logger.info(f"No new jobs found for region: {region}")
                    continue

                # Process jobs into workflows
                workflows = workflow_processor.process_jobs(new_jobs)

                # Update Elasticsearch
                es_client.update_workflows(workflows)

                logger.info(f"Completed processing for region: {region}")

            # Wait for the configured interval before the next run
            time.sleep(config.run_interval)

        except Exception as e:
            logger.error(f"An error occured: {str(e)}")
            time.sleep(config.error_retry_interval)


if __name__ == "__main__":
    main()
