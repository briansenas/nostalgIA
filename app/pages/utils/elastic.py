from __future__ import annotations

import json
import os
from pathlib import Path

from elasticsearch import Elasticsearch

SCRIPT_PATH = Path(__file__).parent.absolute()


def get_client():
    es_host = os.environ.get("ELASTICSEARCH_HOST", "localhost")
    es_port = os.environ.get("ELASTICSEARCH_PORT", "9200")
    # TODO: this only applies for clusters created without security enabled (development purposes)
    es_url = f"http://{es_host}:{es_port}"
    es = Elasticsearch(es_url)
    return es


def create_index(es_client: Elasticsearch, index_name: str = "images"):
    if es_client is None or not isinstance(es_client, Elasticsearch):
        raise ValueError("The ElasticSearch client must be valid.")

    if es_client.indices.exists(index=index_name):
        return False
    else:
        with open(os.path.join(SCRIPT_PATH, "index-settings.json")) as f:
            configuration = json.load(f)
        es_client.indices.create(
            index=index_name,
            settings=configuration["settings"],
            mappings=configuration["mappings"],
        )
        return True


def delete_index(es_client: Elasticsearch, index_name: str = "images"):
    if es_client is None or not isinstance(es_client, Elasticsearch):
        raise ValueError("The ElasticSearch client must be valid.")

    if es_client.indices.exists(index=index_name):
        es_client.indices.delete(index=index_name)
        return True
    else:
        return False
