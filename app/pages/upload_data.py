from __future__ import annotations

import re

import streamlit as st
from pages.utils.elastic import create_index
from pages.utils.elastic import delete_index
from pages.utils.elastic import get_client
from PIL import Image


def upload_data(**kwargs):
    pass


def generate_image_description():
    return "LLM things..."


ES_CLIENT = get_client()
st.title("Image Database")
page_desc, ping_es, create_index_es, delete_index_es = st.columns(4)
with page_desc:
    st.write("Upload new images to the index.")
with ping_es:
    if st.button("Ping Engine", use_container_width=True):
        ping = ES_CLIENT.ping()
        if ping:
            st.text("Perfectly connected to the engine!")
        else:
            st.text("Unable to establish the connection.")
            info = ES_CLIENT.info()
            st.error(info)
with create_index_es:
    if st.button("Create Index", use_container_width=True):
        result = create_index(ES_CLIENT)
        if result:
            st.text("The index already exists!")
        else:
            st.text("Index created succesfully!")
with delete_index_es:
    if st.button("Delete Index", use_container_width=True):
        result = delete_index(ES_CLIENT)
        if result:
            st.text("Index has been deleted!")
        else:
            st.text("Index doesn't exist!")


st.subheader("Image Search")
upload_col, preview_col = st.columns(2)
with upload_col:
    uploaded_file = st.file_uploader(
        "Upload an image",
        type=["jpg", "jpeg", "png"],
    )
with preview_col:
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", width=250)
if uploaded_file is not None:
    with st.spinner("Generating Description..."):
        st.subheader("Auto-generated Description (optional)")
        description = generate_image_description()
        generated_text_query = st.text_input(
            "Edit generated description (optional)",
            value=description,
        )

st.subheader("Description (optional)")
text_query = st.text_input("Enter description (optional)")

st.subheader("Tags (optional)")
tags_query = st.text_input(
    "Enter tags (optional, comma-separated-hastags, e.g #biking #germany)",
)
tags_regex = re.compile(r"^(#\w+)(\s#\w+)*$")
if tags_query:
    tags_valid = re.fullmatch(tags_regex, tags_query)

# Upload button
if st.button("Upload"):
    if uploaded_file is None:
        st.warning("Please provide an image.")
    if tags_query and not tags_valid:
        st.warning(
            "Please provide a valid set of tags. E.g #biking #lisbon",
        )
    else:
        with st.spinner("Uploading..."):
            # Call the placeholder function with whatever inputs are available
            results = upload_data(
                image_file=uploaded_file,
                text_query=text_query,
                tags=tags_query,
            )
            st.success("✅ Image Uploaded")
