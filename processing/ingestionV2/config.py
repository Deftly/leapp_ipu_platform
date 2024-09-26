import os
from dotenv import load_dotenv


class Config:
    def __init__(self):
        load_dotenv()

        self.regions = ["amrs", "emea", "apac", "dmz"]
        self.run_interval = int(os.getenv("RUN_INTERVAL", 600))  # 10 min. default
        self.error_retry_interval = int(
            os.getenv("ERROR_RETRY_INTERVAL", 300)  # 5 min. default
        )

        self.aap_base_urls = {
            "amrs": os.getenv("AAP_BASE_URL_AMRS"),
            "emea": os.getenv("AAP_BASE_URL_EMEA"),
            "apac": os.getenv("AAP_BASE_URL_APAC"),
            "dmz": os.getenv("AAP_BASE_URL_DMZ"),
        }

        self.aap_cookies = {
            "amrs": os.getenv("AAP_COOKIE_AMRS"),
            "emea": os.getenv("AAP_COOKIE_EMEA"),
            "apac": os.getenv("AAP_COOKIE_APAC"),
            "dmz": os.getenv("AAP_COOKIE_DMZ"),
        }

        self.es_url = os.getenv("ELASTICSEARCH_URL")
        self.es_index = os.getenv("ELASTICSEARCH_INDEX", "rhel_upgrade_reporting")

        self.app_page_size = int(os.getenv("AAP_PAGE_SIZE", "200"))
