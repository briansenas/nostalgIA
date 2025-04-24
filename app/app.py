import streamlit as st


def main():
    search_page = st.Page("pages/search_data.py", title="Search Engine", icon="🔍")
    upload_page = st.Page("pages/upload_data.py", title="Data Manipulation", icon=":material/add_circle:")
    pg = st.navigation([search_page, upload_page])
    st.set_page_config(page_icon="🔍", page_title="Image Search Engine", layout="wide")
    pg.run()

if __name__ == "__main__":
    main()
