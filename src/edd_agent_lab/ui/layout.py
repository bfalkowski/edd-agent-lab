"""Shared dashboard layout helpers (matches eval-driven-design-platform console)."""

from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

_PILL_STATUSES = frozenset({"green", "yellow", "red", "blue"})


def load_css() -> None:
    css_path = Path(__file__).resolve().parent / "styles" / "dashboard.css"
    css = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def page_shell(title: str, subtitle: str | None = None) -> None:
    subtitle_html = (
        f'<div class="edd-hero-subtitle">{html.escape(subtitle)}</div>' if subtitle else ""
    )
    st.markdown(
        f"""
        <div class="edd-hero">
          <div class="edd-hero-title">{html.escape(title)}</div>
          {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, meta: str | None = None) -> None:
    meta_html = f'<div class="edd-page-meta">{html.escape(meta)}</div>' if meta else ""
    st.markdown(
        f"""
        <div class="edd-page-header">
          <div class="edd-page-title">{html.escape(title)}</div>
          {meta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_brand() -> None:
    st.sidebar.markdown(
        """
        <div class="edd-sidebar-brand">
          <div class="edd-sidebar-title">EDD Agent Lab</div>
          <div class="edd-sidebar-caption">Reference scenario workbench · port 8502</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_pill(label: str, status: str = "blue") -> str:
    safe_status = status if status in _PILL_STATUSES else "blue"
    return f'<span class="edd-pill edd-pill-{safe_status}">{html.escape(label)}</span>'
