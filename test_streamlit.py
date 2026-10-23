import streamlit as st

st.set_page_config(page_title="MediInsight Test", layout="wide")

st.title("MediInsight Rendering Test")
st.success("Streamlit is rendering correctly!")
st.write("If you can see this message, the basic rendering works.")

st.sidebar.title("Test Sidebar")
st.sidebar.write("Sidebar is working.")