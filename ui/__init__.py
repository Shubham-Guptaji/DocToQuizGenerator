"""UI package containing Streamlit views and custom components."""
from ui.components import render_custom_css, render_metric_card
from ui.dashboard import render_dashboard_page
from ui.create_quiz import render_create_quiz_page
from ui.take_quiz import render_take_quiz_page
from ui.results import render_results_page
from ui.history import render_history_page
from ui.settings_page import render_settings_page

__all__ = [
    "render_custom_css",
    "render_metric_card",
    "render_dashboard_page",
    "render_create_quiz_page",
    "render_take_quiz_page",
    "render_results_page",
    "render_history_page",
    "render_settings_page",
]
