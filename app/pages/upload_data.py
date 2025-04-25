from __future__ import annotations

import base64
import datetime
import hashlib
import os
import re
from io import BytesIO

import streamlit as st
from pages.utils import journal
from pages.utils.elastic import create_index
from pages.utils.elastic import delete_index
from pages.utils.elastic import get_client
from pages.utils.elastic import index_data
from pages.utils.image_exif import get_location_name
from pages.utils.image_models import generate_image_description
from pages.utils.image_models import load_model
from PIL import Image


@st.cache_resource
def cache_load_model(model_id=None):
    model, processor = load_model(model_id)
    st.session_state["model"] = True
    st.session_state["processor"] = True
    return model, processor


@st.cache_resource
def cache_generate_image_description(_image, _model, _processor):
    return generate_image_description(_image, _model, _processor)


def get_exif_data(_image):
    try:
        exif_data = _image._getexif()
        if exif_data is not None:
            # Retrieve date and GPS coordinates
            date = None
            gps_info = None
            for tag, value in exif_data.items():
                if tag == 36867:  # DateTimeOriginal
                    date = value
                if tag == 34853:  # GPSInfo
                    gps_info = value
            res = "Unable to retrieve some metadata from the image."
            if date:
                date_obj = datetime.datetime.strptime(date, "%Y:%m:%d %H:%M:%S")
                date = date_obj.strftime("%Y-%m-%dT%H:%M:%SZ")
            if not date or not gps_info:
                st.warning(res)
            return date, gps_info
    # TODO: Should use specific exceptions
    except Exception:
        return None, None


def validate_datetime_from_input(input):
    try:
        if input:
            if "T" in input:
                datetime.datetime.strptime(input, "%Y-%m-%dT%H:%M:%SZ")
            else:
                datetime.datetime.strptime(input, "%Y-%m-%d")
        return True
    # TODO: Should use specific exceptions
    except Exception:
        return False


def generate_file_id(file):
    # Create a sha256 hash object
    hash_sha256 = hashlib.sha256()

    # Read the file in chunks and update the hash
    while chunk := file.read(8192):
        hash_sha256.update(chunk)

    # Return the hexadecimal representation of the hash
    return hash_sha256.hexdigest()


def upload_data(
    payload: journal.Image,
):
    if not ES_CLIENT:
        st.error("Unable to stablish connection with the search engine")
    return index_data(ES_CLIENT, "images", payload.model_dump())


model = processor = None
st_env_keys = ["model", "processor", "llm_description", "filename"]
for env in st_env_keys:
    if env not in st.session_state:
        st.session_state[env] = None

ES_CLIENT = get_client()
st.title("Image Database")
page_desc, load_model_col, ping_es, create_index_es, delete_index_es = st.columns(5)
with page_desc:
    st.write("Upload new images to the index.")
    if not (st.session_state.model and st.session_state.processor):
        st.warning("The description model is not loaded yet!")
    else:
        st.success("The model is loaded!")
with load_model_col:
    if st.button("Load Model", use_container_width=True):
        model, processor = cache_load_model()
        st.text("Model loaded Successfully!")
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
        if uploaded_file.name != st.session_state["filename"]:
            st.session_state["filename"] = uploaded_file.name
            cache_generate_image_description.clear()
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", width=250)
if uploaded_file is not None:
    image_date, image_gps_info = get_exif_data(image)
    title_col, location_col, date_col = st.columns(3)
    with title_col:
        st.subheader("Title")
        title = st.text_input("Title", value=os.path.basename(uploaded_file.name))
    with location_col:
        st.subheader("Location")
        image_location = None
        if image_gps_info:
            image_location = get_location_name(image_gps_info)
        location = st.text_input("Location", value=image_location)
    with date_col:
        st.subheader("Date")
        date = st.text_input("Date", value=image_date)
    st.subheader("Auto-generated Description (optional)")
    model, processor = cache_load_model()
    llm_description = cache_generate_image_description(image, model, processor)
    generated_text_query = st.text_input(
        "Edit generated description (optional)",
        value=llm_description,
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
    if not validate_datetime_from_input(date):
        st.error(
            "Please provide a valid date in the following format:"
            "yyyy-MM-dd'T'HH:mm:ss.SSSZ or yyyy-MM-dd (E.g 2024-01-01T14:00:00.000Z)",
        )
    elif uploaded_file:
        with st.spinner("Uploading..."):
            # Call the placeholder function with whatever inputs are available
            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue())
            results = upload_data(
                journal.Image(
                    id=generate_file_id(uploaded_file),
                    base64=img_str,
                    title=title,
                    location=location,
                    date=date,
                    description=text_query,
                    generated_description=generated_text_query,
                    tags=tags_query.split(" "),
                ),
            )
            if results:
                st.success("✅ Image Uploaded")
            else:
                st.warning("❌ Unable to upload the image")
