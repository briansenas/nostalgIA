from PIL import Image
import re
import streamlit as st

def upload_data(**kwargs):
    pass

def generate_image_description():
    return "LLM things..."

st.title("Image Database")
st.write("Upload new images to the index.")

st.subheader("Image Search")
uploaded_file = st.file_uploader(
    "Upload an image", type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", width=250)
    with st.spinner("Generating Description..."):
        st.subheader("Auto-generated Description (optional)")
        description = generate_image_description()
        generated_text_query = st.text_input("Edit generated description (optional)", value=description)

st.subheader("Description (optional)")
text_query = st.text_input("Enter description (optional)")

st.subheader("Tags (optional, comma-separated-hastags)")
tags_query = st.text_input("Enter tags (optional, e.g #biking)")
tags_regex = re.compile(r"^(#\w+)(\s#\w+)*$")
if tags_query:
    tags_valid = re.fullmatch(tags_regex, tags_query)

# Search button
if st.button("Upload"):
    if uploaded_file is None:
        st.warning("Please provide an image.")
    if tags_query and not tags_valid:
        st.warning("Please provide a valid set of tags. E.g #biking #lisbon #fun")
    else:
        with st.spinner("Uploading..."):
            # Call the placeholder function with whatever inputs are available
            results = upload_data(
                image_file=uploaded_file, text_query=text_query, tags=tags_query 
            )
            st.success("✅ Image Uploaded")