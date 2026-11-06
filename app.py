"""Streamlit entry point."""

from __future__ import annotations

import streamlit as st

from src.errors import AppError, user_message_for
from src.runtime import build_runtime
from src.ui import render_app


@st.cache_resource(show_spinner="Loading the troubleshooting guide and local models...")
def _get_runtime():
    return build_runtime()


def main() -> None:
    st.set_page_config(page_title="Bosch Rexroth Troubleshooting Assistant", layout="wide")
    try:
        runtime = _get_runtime()
    except AppError as exc:
        st.title("Bosch Rexroth Troubleshooting Assistant")
        st.error(user_message_for(exc))
        return
    except Exception:
        st.title("Bosch Rexroth Troubleshooting Assistant")
        st.error("The application could not be initialized. Check the PDF, local model setup, and configuration.")
        return
    render_app(runtime)


main()
