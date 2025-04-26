from __future__ import annotations

import base64
import logging
from io import BytesIO

import streamlit as st
from pages.utils.elastic import get_client
from pages.utils.elastic import search_data
from pages.utils.image_models import generate_image_vector
from pages.utils.image_models import generate_text_vector
from pages.utils.image_models import load_clip_model
from PIL import Image


LOGGER = logging.getLogger(__file__)


def search_engine(image_vector=None, text_query=None, text_vector=None, filters=None):
    """
    Function for the search engine that handles all search types
    Args:
            image_file: The uploaded image file (optional)
            text_query: The text query string (optional)
            filters: Dictionary containing filter parameters

    Returns:
            List of search results
    """
    if image_vector or text_query:
        return search_data(
            get_client(),
            "images",
            text_query=text_query,
            text_vector=text_vector,
            image_vector=image_vector,
        )
    else:
        return []


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
                st.write(f"Reciprocal Rank Similarity: {result['_rrf_score']}")
                st.write(f"Similarity: {result['_score']}")
                st.image(res_im, caption=document["title"], width=250)

            with col2:
                st.markdown(
                    f"**Generated Description**: {document['generated_description']}",
                )
                st.write(f"Description: {document['description']}")
                st.write(f"Tags: {', '.join(document['tags'] or [])}")
                st.write(f"Date: {document['date']}")
                st.write(f"Location: {document['location']}")

            st.divider()


ES_CLIENT = get_client()
st.title("Image Search Engine")
st.write("Search for images using image files, text queries, or both")

st.subheader("Image Search")
uploaded_file = st.file_uploader(
    "Upload an image (optional)",
    type=["jpg", "jpeg", "png"],
)

image = None
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", width=250)

st.subheader("Text Search")
text_query = st.text_input("Enter search text (optional)")

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

# Location filter
st.sidebar.subheader("Location Filter")
use_location_filter = st.sidebar.checkbox("Filter by location")
location = None
if use_location_filter:
    location = st.sidebar.text_input("Location")

# Person filter
st.sidebar.subheader("Person Filter")
use_person_filter = st.sidebar.checkbox("Filter by person")
person = None
if use_person_filter:
    person = st.sidebar.text_input("Person")

# Collect all filters
filters = {
    "date": {"enabled": use_date_filter, "start": start_date, "end": end_date},
    "location": {"enabled": use_location_filter, "value": location},
    "person": {"enabled": use_person_filter, "value": person},
}

# Search button
if st.button("Search"):
    if uploaded_file is None and not text_query:
        st.warning("Please provide either an image or text for search.")
    else:
        with st.spinner("Searching..."):
            # Call the placeholder function with whatever inputs are available
            # Load clip and generate vectors
            clip_model, clip_processor = load_clip_model()
            image_vector = text_vector = None
            if text_query:
                text_vector = (
                    generate_text_vector([text_query], clip_model).cpu().tolist()[0]
                )
            if image is not None:
                image_vector = (
                    generate_image_vector(image, clip_model, clip_processor)
                    .reshape(-1)
                    .cpu()
                    .tolist()
                )
            results = search_engine(
                image_vector=image_vector,
                text_query=text_query,
                text_vector=text_vector,
                filters=filters,
            )
            display_results(results)
