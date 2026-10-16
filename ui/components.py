"""Custom CSS styles, theme tokens, and reusable visual UI components."""
import streamlit as st


def render_custom_css():
    """Inject modern typography, sleek gradients, glassmorphism, and responsive layout styling."""
    st.markdown(
        """
        <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        h1, h2, h3, h4, .brand-title {
            font-family: 'Outfit', sans-serif !important;
            letter-spacing: -0.02em;
        }

        /* Hero Header */
        .hero-container {
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 40%, #4338ca 100%);
            border-radius: 16px;
            padding: 2.2rem 2.5rem;
            color: #ffffff;
            margin-bottom: 2rem;
            box-shadow: 0 10px 25px -5px rgba(67, 56, 202, 0.3), 0 8px 10px -6px rgba(67, 56, 202, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.12);
        }

        .hero-badge {
            display: inline-block;
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(8px);
            padding: 4px 14px;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-bottom: 0.8rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .hero-title {
            font-size: 2.3rem;
            font-weight: 800;
            margin: 0;
            line-height: 1.2;
            background: linear-gradient(180deg, #ffffff 0%, #e0e7ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .hero-subtitle {
            font-size: 1.05rem;
            color: #c7d2fe;
            margin-top: 0.6rem;
            margin-bottom: 0;
            max-width: 650px;
            line-height: 1.5;
        }

        /* Metric Glass Card */
        .metric-card {
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 1.2rem 1.4rem;
            transition: all 0.2s ease-in-out;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .metric-card:hover {
            transform: translateY(-2px);
            border-color: rgba(99, 102, 241, 0.4);
            box-shadow: 0 8px 16px -2px rgba(99, 102, 241, 0.15);
        }

        .metric-label {
            font-size: 0.82rem;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.05em;
            color: #94a3b8;
            margin-bottom: 0.3rem;
        }

        .metric-value {
            font-family: 'Outfit', sans-serif;
            font-size: 1.9rem;
            font-weight: 700;
            color: #f8fafc;
            line-height: 1.1;
        }

        .metric-sub {
            font-size: 0.78rem;
            color: #64748b;
            margin-top: 0.3rem;
        }

        /* Quiz Question Card */
        .quiz-card {
            background: rgba(30, 41, 59, 0.5);
            border: 1px solid rgba(148, 163, 184, 0.15);
            border-radius: 14px;
            padding: 1.6rem 1.8rem;
            margin-bottom: 1.5rem;
        }

        .question-number-badge {
            background: #4f46e5;
            color: white;
            font-size: 0.8rem;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 6px;
            display: inline-block;
            margin-bottom: 0.8rem;
        }

        .question-topic-badge {
            background: rgba(14, 165, 233, 0.15);
            color: #38bdf8;
            border: 1px solid rgba(14, 165, 233, 0.3);
            font-size: 0.75rem;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 6px;
            display: inline-block;
            margin-left: 0.5rem;
            margin-bottom: 0.8rem;
        }

        .question-difficulty-badge {
            font-size: 0.75rem;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 6px;
            display: inline-block;
            margin-left: 0.5rem;
            margin-bottom: 0.8rem;
        }
        .diff-easy { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }
        .diff-medium { background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3); }
        .diff-hard { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }

        .question-text {
            font-size: 1.15rem;
            font-weight: 600;
            line-height: 1.5;
            margin-bottom: 1.2rem;
            color: #f1f5f9;
        }

        /* Review Pill Filters */
        .review-card {
            border-radius: 12px;
            padding: 1.2rem 1.4rem;
            margin-bottom: 1rem;
            border-left: 5px solid;
            background: rgba(15, 23, 42, 0.4);
        }
        .review-correct {
            border-left-color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.2);
            border-left-width: 5px;
        }
        .review-incorrect {
            border-left-color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.2);
            border-left-width: 5px;
        }
        .review-unanswered {
            border-left-color: #f59e0b;
            border: 1px solid rgba(245, 158, 11, 0.2);
            border-left-width: 5px;
        }

        /* Score Grade Badge */
        .grade-badge {
            font-size: 2.8rem;
            font-weight: 900;
            font-family: 'Outfit', sans-serif;
            display: inline-block;
            padding: 0.4rem 1.4rem;
            border-radius: 16px;
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            color: #ffffff;
            box-shadow: 0 8px 16px -4px rgba(79, 70, 229, 0.4);
        }

        /* Option cards in review */
        .option-item {
            padding: 8px 14px;
            border-radius: 8px;
            margin-bottom: 6px;
            font-size: 0.95rem;
        }
        .option-normal {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.05);
            color: #94a3b8;
        }
        .option-correct-highlight {
            background: rgba(34, 197, 94, 0.12);
            border: 1px solid rgba(34, 197, 94, 0.4);
            color: #86efac;
            font-weight: 600;
        }
        .option-wrong-highlight {
            background: rgba(239, 68, 68, 0.12);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: #fca5a5;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, subtext: str = "", icon: str = ""):
    """Render a modern glassmorphic dashboard metric card."""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{icon} {label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero_banner(title: str, subtitle: str, badge: str = "SMART ASSESSMENT"):
    """Render a hero gradient banner."""
    st.markdown(
        f"""
        <div class="hero-container">
            <div class="hero-badge">{badge}</div>
            <h1 class="hero-title">{title}</h1>
            <p class="hero-subtitle">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
