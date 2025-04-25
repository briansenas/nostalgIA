from __future__ import annotations

from pathlib import Path

import streamlit as st
import torch
from dotenv import load_dotenv

# TODO: find a better way? It is only a warning but disturbs me
# https://github.com/VikParuchuri/marker/issues/442
torch.classes.__path__ = []  # add this line to manually set it to empty.

SCRIPT_PATH = Path(__file__).parent.absolute()
results = load_dotenv()
if not results:
    st.error("Unable to load environment variables!")


def main():
    search_page = st.Page("pages/search_data.py", title="Search Engine", icon="🔍")
    upload_page = st.Page(
        "pages/upload_data.py",
        title="Data Manipulation",
        icon=":material/add_circle:",
    )
    pg = st.navigation([search_page, upload_page])
    st.set_page_config(page_icon="🔍", page_title="Image Search Engine", layout="wide")
    pg.run()


if __name__ == "__main__":
    main()
