from __future__ import annotations

import datetime
import json
import logging
import os
from collections import defaultdict
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

from elasticsearch import Elasticsearch

SCRIPT_PATH = Path(__file__).parent.absolute()
LOGGER = logging.getLogger()


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


def index_data(es_client: Elasticsearch, index_name: str, payload: dict):
    if es_client is None or not isinstance(es_client, Elasticsearch):
        raise ValueError("The ElasticSearch client must be valid.")

    id = payload.get("id", None)
    if es_client.indices.exists(index=index_name):
        payload["date_indexed"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        es_client.index(index=index_name, id=id, document=payload)
        return True
    else:
        return False


def get_facets(
    es_client: Elasticsearch,
    index_name: str,
    fields: list[str],
    filters,
    size=20,
):
    payload: MutableMapping = {
        "size": 0,
        "query": {
            "bool": {
                "must": {
                    "match_all": {},
                },
                **generate_filters(filters),
            },
        },
        "aggs": {},
    }
    for field in fields:
        payload["aggs"][f"{field}_facet"] = {
            "terms": {"field": field, "size": size},
        }
    response = es_client.search(index=index_name, body=payload)
    results = {}
    for field in fields:
        results[field] = [
            bucket["key"]
            for bucket in response["aggregations"][f"{field}_facet"]["buckets"]
        ]
    return results


def generate_knn_search(query_vector, knn_k, top_n, filter_dict, window_size: int = 10):
    return [
        {
            "knn": {
                "field": field,
                "query_vector": query_vector,
                "k": knn_k,
                "num_candidates": top_n,
                **filter_dict,
            },
            # NOTE: we could also embed a query statement before knn and set weights for a hybrid "or"
            # NOTE: score = 0.9 * match_score + 0.1 * knn_score
            # NOTE: We could add a "rescore" with precise cosine similarity
        }
        for field in [
            "image_vector",
            "description_embedding",
            "description_generated_embedding",
        ]
    ]


def generate_filters(filters):
    filter_dict: dict[str, Any] = {"filter": []}
    if filters:
        for key, filter_ in filters.items():
            enabled = filter_["enabled"]
            if enabled:
                if "value" in filter_:
                    data = filter_["value"]
                    if data and isinstance(data, list):
                        filter_dict["filter"].append({"terms": {key: filter_["value"]}})
                    elif data:
                        filter_dict["filter"].append({"term": {key: filter_["value"]}})
                elif filter_["start"] or filter_["end"]:
                    range_ = {}
                    start_ = filter_["start"]
                    end_ = filter_["end"]
                    if start_:
                        range_["gte"] = start_
                    if end_:
                        range_["lte"] = end_
                    if range_:
                        filter_dict["filter"].append({"range": {key: range_}})
    return filter_dict


def search_data(
    es_client: Elasticsearch,
    index_name: str,
    image_vector=None,
    text_query=None,
    text_vector=None,
    filters=None,
    knn_k=5,
    rrf_k=60,
    top_n=100,
):
    queries = []
    filter_dict = generate_filters(filters)
    if image_vector:
        queries += generate_knn_search(image_vector, knn_k, top_n, filter_dict)
    if text_query:
        queries.append(
            {
                "query": {
                    "bool": {
                        "must": {
                            "multi_match": {
                                "query": text_query,
                                "type": "most_fields",
                                "fields": [
                                    "title^1",
                                    "description^3",
                                    "city^0.5",
                                    "country^0.5",
                                    "generated_description^2",
                                ],
                                "operator": "or",
                                "fuzziness": "auto",
                            },
                        },
                        **filter_dict,
                    },
                },
            },
        )
    if text_vector:
        queries += generate_knn_search(text_vector, knn_k, top_n, filter_dict)
    if queries:
        return reciprocal_rank_fusion(
            es_client=es_client,
            index_name=index_name,
            queries=queries,
            k=rrf_k,
            top_n=top_n,
        )
    else:
        query = {
            "query": {"bool": {**filter_dict}},
        }
        return es_client.search(index=index_name, size=top_n, body=query)["hits"][
            "hits"
        ]


def reciprocal_rank_fusion(
    es_client,
    index_name,
    queries,
    top_n=100,
    k=60,
):
    """
    Perform Reciprocal Rank Fusion (RRF) on multiple query results.

    Args:
        es_client: An instance of Elasticsearch client.
        index_name (str): The index name.
        queries (list of str): List of query strings.
        query_field (str): The field to match in the documents.
        top_n (int): Number of top results to retrieve from each query.
        k (int): RRF constant (typically 60).

    Returns:
        List of dicts: Documents with their RRF scores, sorted descending.
    """
    rrf_scores = defaultdict(float)
    doc_data = dict()  # To store document contents (optional)

    def run_query(q):
        response = es_client.search(
            index=index_name,
            size=top_n,
            **q,
        )
        hits = response["hits"]["hits"]
        return hits

    for query in queries:
        hits = run_query(query)
        for rank, hit in enumerate(hits):
            doc_id = hit["_id"]
            rrf_scores[doc_id] += 1 / (k + rank + 1)
            if doc_id not in doc_data:
                doc_data[doc_id] = hit

    fused_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    output = []
    for doc_id, score in fused_results:
        doc = doc_data[doc_id]
        doc["_id"] = doc_id
        doc["_rrf_score"] = score
        output.append(doc)

    return output
