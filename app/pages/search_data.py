from __future__ import annotations

import base64
import logging
from io import BytesIO

import streamlit as st
from elasticsearch import Elasticsearch
from pages.utils.elastic import get_client
from pages.utils.elastic import get_facets
from pages.utils.elastic import search_data
from pages.utils.image_models import generate_image_vector
from pages.utils.image_models import generate_text_vector
from pages.utils.image_models import load_clip_model
from PIL import Image


LOGGER = logging.getLogger(__file__)


def search_engine(
    es_client: Elasticsearch,
    image_vector=None,
    text_query=None,
    text_vector=None,
    filters=None,
):
    """
    Function for the search engine that handles all search types
    Args:
            image_file: The uploaded image file (optional)
            text_query: The text query string (optional)
            filters: Dictionary containing filter parameters

    Returns:
            List of search results
    """
    return search_data(
        es_client,
        "images",
        text_query=text_query,
        text_vector=text_vector,
        image_vector=image_vector,
        filters=filters,
    )


def fetch_facets(fields=["city", "country"], size: int = 20):
    return get_facets(get_client(), "images", fields, size=size)


def display_results(results):
    if not results:
        st.info("No results found.")
        return

    st.subheader(f"Found {len(results)} results")
    for i, result in enumerate(results):
        document = result["_source"]
        with st.container():
            col1, col2 = st.columns([1, 4])

            with col1:
                res_bites = BytesIO(base64.b64decode(document["base64"]))
                res_im = Image.open(res_bites)
                if "_rrf_score" in result:
                    st.write(f"Reciprocal Rank Similarity: {result['_rrf_score']}")
                st.write(f"Similarity: {result['_score']}")
                st.image(
                    res_im,
                    caption=document["title"],
                    width=250,
                    use_container_width=True,
                )

            with col2:
                st.markdown(
                    f"**Generated Description**: {document['generated_description']}",
                )
                st.write(f"**Description**: {document['description']}")
                st.write(f"**Tags**: {', '.join(document['tags'] or [])}")
                st.write(f"**Date**: {document['date']}")
                st.write(f"**City**: {document['city']}")
                st.write(f"**Country**: {document['country']}")

            st.divider()


ES_CLIENT = get_client()
st.title("Image Search Engine")
st.write("Search for images using image files, text queries, or both")

st.subheader("Image Search")
uploaded_file = st.file_uploader(
    "Upload an image (optional)",
    type=["jpg", "jpeg", "png", "heic"],
)

st_zero_keys = [
    "image_rotation",
]
for env in st_zero_keys:
    if env not in st.session_state:
        st.session_state[env] = 0

image = None
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    image = image.rotate(st.session_state["image_rotation"] or 0)
    st.image(image, caption="Uploaded Image", width=250)
    if st.button("rotate"):
        st.session_state["image_rotation"] = (
            (st.session_state["image_rotation"] or 0) + 90
        ) % 360
        st.rerun()

st.subheader("Text Search")
text_query = st.text_input("Enter search text (optional)", label_visibility="collapsed")

# Sidebar for filtering options
st.sidebar.header("Filter Options")

# Date filter
st.sidebar.subheader("Date Filter")
use_date_filter = st.sidebar.checkbox("Filter by date")
start_date = None
end_date = None
if use_date_filter:
    col1, col2 = st.sidebar.columns(2)
    start_date = col1.date_input("Start date")
    end_date = col2.date_input("End date")

facets = fetch_facets()
cities, countries = facets["city"], facets["country"]

st.sidebar.subheader("City Filter")
use_city_filter = st.sidebar.checkbox("Filter by city")
selected_cities = []
if use_city_filter:
    for city in cities:
        if st.sidebar.checkbox(city, key=f"city_{city}_facet"):
            selected_cities.append(city)

st.sidebar.subheader("Country Filter")
use_country_filter = st.sidebar.checkbox("Filter by country")
selected_countries = []
if use_country_filter:
    for country in countries:
        if st.sidebar.checkbox(country, key=f"country_{country}_facet"):
            selected_countries.append(country)

# Collect all filters
filters = {
    "date": {
        "enabled": use_date_filter,
        "start": start_date,
        "end": end_date,
        "type": "date-range",
    },
    "city": {"enabled": use_city_filter, "value": selected_cities, "type": "term"},
    "country": {
        "enabled": use_country_filter,
        "value": selected_countries,
        "type": "term",
    },
}

# Search button
if st.button("Search"):
    with st.spinner("Searching..."):
        # Call the placeholder function with whatever inputs are available
        # Load clip and generate vectors
        clip_model, clip_processor = load_clip_model()
        image_vector = text_vector = None
        if text_query:
            text_vector = (
                generate_text_vector([text_query], clip_model).cpu().tolist()[0]
            )
        if image:
            image_vector = (
                generate_image_vector(image, clip_model, clip_processor)
                .reshape(-1)
                .cpu()
                .tolist()
            )
        results = search_engine(
            ES_CLIENT,
            image_vector=image_vector,
            text_query=text_query,
            text_vector=text_vector,
            filters=filters,
        )
        display_results(results)
