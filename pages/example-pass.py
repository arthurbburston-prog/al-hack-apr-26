import streamlit as st

st.title("Example Pass")
st.subheader("This is an example check which always passes")

full_name = st.text_input("Full name")

if full_name != "":
    st.success("Verified!")
