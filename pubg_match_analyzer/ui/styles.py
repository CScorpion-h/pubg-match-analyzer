"""全站样式注入 — 暗色沉浸主题。"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st


APP_FONT_FAMILY = '"Microsoft YaHei", "PingFang SC", sans-serif'
SIDEBAR_WIDTH_PX = 200
CONTENT_MAX_WIDTH_PX = 1320

_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
_bg_data_uri: str = ""


def _get_bg_uri() -> str:
    global _bg_data_uri
    if not _bg_data_uri:
        p = _ASSETS_DIR / "hero_banner.png"
        if p.exists():
            _bg_data_uri = "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
    return _bg_data_uri


def apply_global_styles() -> None:
    """注入全站暗色设计系统样式（所有页面共享背景与组件风格）。"""
    bg = _get_bg_uri()
    bg_css = f"url('{bg}')" if bg else "linear-gradient(165deg,#0c1828 0%,#080f1c 100%)"

    st.markdown(
        f"""
        <style>
        :root {{
            --pm-font-family: {APP_FONT_FAMILY};
            --pm-sidebar-width: {SIDEBAR_WIDTH_PX}px;
            --pm-content-width: {CONTENT_MAX_WIDTH_PX}px;
            --pm-bg: #070d18;
            --pm-surface: rgba(14,22,38,.84);
            --pm-surface-hi: rgba(20,30,50,.92);
            --pm-border: rgba(255,255,255,.08);
            --pm-border-strong: rgba(255,255,255,.14);
            --pm-title: #d8ecff;
            --pm-text: rgba(195,218,248,.86);
            --pm-muted: rgba(140,168,210,.58);
            --pm-blue: #4a8fd4;
            --pm-blue-soft: rgba(74,143,212,.16);
            --pm-green-soft: rgba(88,184,118,.14);
            --pm-red-soft: rgba(220,90,90,.14);
            --pm-badge-bg: rgba(88,184,118,.14);
            --pm-badge-text: #8dd4a4;
            --pm-shadow: 0 12px 32px rgba(0,0,0,.52);
            --pm-shadow-soft: 0 6px 20px rgba(0,0,0,.38);
        }}

        html, body, [class*="css"] {{
            font-family: var(--pm-font-family) !important;
            font-synthesis: none !important;
        }}

        body {{
            background: var(--pm-bg);
            color: var(--pm-text);
        }}

        /* ── 全局页面背景（所有页面共享战地氛围背景）── */
        .stApp {{
            background: #060c16;
            background-image: {bg_css};
            background-size: cover;
            background-position: center top;
            background-repeat: no-repeat;
            background-attachment: fixed;
            color: var(--pm-text);
        }}

        .stApp [data-testid="stAppViewContainer"] {{
            background: linear-gradient(
                180deg,
                rgba(6,11,20,.48) 0%,
                rgba(5,9,17,.62) 35%,
                rgba(4,7,14,.76) 70%,
                rgba(3,6,12,.86) 100%
            );
        }}

        /* ── 顶部 Header/Toolbar ── */
        .stApp header[data-testid="stHeader"] {{
            background: rgba(6,12,22,.88) !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            border-bottom: 1px solid rgba(255,255,255,.06) !important;
            box-shadow: 0 1px 8px rgba(0,0,0,.4) !important;
        }}

        .stApp [data-testid="stDecoration"] {{
            display: none !important;
        }}

        .stApp [data-testid="stToolbar"] {{
            background: transparent !important;
        }}

        /* ── 内容区容器 ── */
        .stApp section.main > div.block-container {{
            max-width: var(--pm-content-width);
            padding-top: 1.6rem;
            padding-bottom: 4rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }}

        /* ── Sidebar ── */
        .stApp [data-testid="stSidebar"] {{
            min-width: var(--pm-sidebar-width) !important;
            max-width: var(--pm-sidebar-width) !important;
            background: linear-gradient(
                180deg,
                rgba(10,18,34,.96) 0%,
                rgba(7,14,26,.98) 100%
            ) !important;
            border-right: 1px solid rgba(70,110,175,.14) !important;
            backdrop-filter: blur(24px) !important;
            -webkit-backdrop-filter: blur(24px) !important;
        }}

        .stApp [data-testid="stSidebar"] > div:first-child {{
            width: var(--pm-sidebar-width) !important;
        }}

        .stApp [data-testid="stSidebarNav"] {{
            padding-top: 0.85rem;
        }}

        /* 非激活项：中灰白，在深色背景上清晰可读 */
        .stApp [data-testid="stSidebarNav"] a {{
            border-radius: 10px;
            margin: 0.18rem 0;
            color: rgba(185,205,235,.70) !important;
            font-weight: 500;
            letter-spacing: 0.01em;
            transition: background 130ms ease, color 130ms ease;
        }}

        .stApp [data-testid="stSidebarNav"] a:hover {{
            background: rgba(255,255,255,.07) !important;
            color: rgba(220,235,255,.88) !important;
        }}

        /* 激活项：亮度对比（近白加粗），不依赖色相区分，任何背景下可读 */
        .stApp [data-testid="stSidebarNav"] a[aria-current="page"] {{
            background: rgba(255,255,255,.10) !important;
            color: rgba(232,245,255,.96) !important;
            font-weight: 700 !important;
            box-shadow: none !important;
        }}

        /* ── 字体层级 ── */
        .stApp h1, .stApp h2, .stApp h3 {{
            color: var(--pm-title) !important;
            font-weight: 800 !important;
            letter-spacing: -0.02em;
        }}

        .stApp p, .stApp li, .stApp label,
        .stApp [data-testid="stMarkdownContainer"] {{
            color: var(--pm-text);
            line-height: 1.72;
        }}

        /* ── Metric 卡片 ── */
        .stApp [data-testid="stMetric"] {{
            background: linear-gradient(
                180deg,
                rgba(20,30,50,.88) 0%,
                rgba(14,22,40,.78) 100%
            ) !important;
            border: 1px solid rgba(255,255,255,.09) !important;
            border-radius: 18px !important;
            padding: 0.72rem 1rem !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            box-shadow: 0 6px 20px rgba(0,0,0,.40) !important;
            min-height: 0 !important;
        }}

        .stApp [data-testid="stMetricLabel"] {{
            color: rgba(170,198,238,.78) !important;
            font-size: 0.84rem !important;
            font-weight: 600 !important;
        }}

        .stApp [data-testid="stMetricValue"] {{
            color: #d8ecff !important;
            font-size: 1.72rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.02em;
        }}

        .stApp [data-testid="stMetricDelta"] {{
            color: rgba(130,210,158,.90) !important;
        }}

        /* ── DataFrame ── */
        .stApp [data-testid="stDataFrame"] {{
            background: rgba(10,18,34,.90) !important;
            border: 1px solid rgba(255,255,255,.08) !important;
            border-radius: 18px !important;
            box-shadow: var(--pm-shadow-soft) !important;
            padding: 0.4rem !important;
        }}

        /* ── Expander ── */
        .stApp [data-testid="stExpander"] {{
            background: rgba(12,20,36,.84) !important;
            border: 1px solid rgba(255,255,255,.08) !important;
            border-radius: 18px !important;
            box-shadow: var(--pm-shadow-soft) !important;
        }}

        .stApp [data-testid="stExpander"] summary,
        .stApp [data-testid="stExpander"] p {{
            color: var(--pm-text) !important;
        }}

        /* ── 输入框 ── */
        .stApp .stTextInput > div > div > input,
        .stApp .stTextArea textarea,
        .stApp .stNumberInput input,
        .stApp div[data-baseweb="select"] > div,
        .stApp .stDateInput input,
        .stApp .stTimeInput input {{
            background: rgba(8,16,30,.92) !important;
            border: 1px solid rgba(255,255,255,.14) !important;
            border-radius: 12px !important;
            color: rgba(205,225,252,.92) !important;
            caret-color: #7ab8f0;
            box-shadow: inset 0 1px 2px rgba(0,0,0,.3);
        }}

        .stApp .stTextInput > div > div > input:focus,
        .stApp .stTextArea textarea:focus,
        .stApp .stNumberInput input:focus,
        .stApp div[data-baseweb="select"] > div:focus-within {{
            border-color: rgba(74,143,212,.55) !important;
            box-shadow: 0 0 0 3px rgba(74,143,212,.12) !important;
        }}

        .stApp input::placeholder, .stApp textarea::placeholder {{
            color: rgba(130,160,205,.42) !important;
        }}

        /* 标签文字 */
        .stApp .stTextInput label, .stApp .stTextArea label,
        .stApp .stNumberInput label, .stApp .stSelectbox label,
        .stApp .stMultiselect label, .stApp .stFileUploader label,
        .stApp .stRadio > label, .stApp .stCheckbox > label {{
            color: rgba(182,205,240,.82) !important;
            font-weight: 600 !important;
        }}

        /* 下拉弹出层 */
        .stApp [data-baseweb="popover"],
        .stApp [data-baseweb="menu"] ul {{
            background: rgba(10,18,34,.98) !important;
            border: 1px solid rgba(255,255,255,.12) !important;
            border-radius: 12px !important;
        }}

        /* ── 按钮 ── */
        .stApp .stButton > button,
        .stApp .stDownloadButton > button,
        .stApp [data-testid="stBaseButton-primary"] {{
            border-radius: 12px;
            min-height: 2.7rem;
            font-weight: 700;
            border: 1px solid rgba(75,138,215,.42) !important;
            background: linear-gradient(
                180deg,
                rgba(56,106,185,.95) 0%,
                rgba(42,82,158,.95) 100%
            ) !important;
            color: #d8ecff !important;
            box-shadow: 0 5px 16px rgba(42,82,158,.30) !important;
            transition: box-shadow 140ms ease, background 140ms ease;
        }}

        .stApp .stButton > button:hover,
        .stApp .stDownloadButton > button:hover,
        .stApp [data-testid="stBaseButton-primary"]:hover {{
            background: linear-gradient(
                180deg,
                rgba(66,118,198,.96) 0%,
                rgba(50,94,170,.96) 100%
            ) !important;
            box-shadow: 0 7px 20px rgba(50,94,170,.36) !important;
        }}

        .stApp .stButton > button[kind="secondary"],
        .stApp [data-testid="stBaseButton-secondary"] {{
            background: rgba(16,26,46,.84) !important;
            color: rgba(185,212,248,.88) !important;
            border: 1px solid rgba(255,255,255,.14) !important;
            box-shadow: none !important;
        }}

        /* ── Tabs ── */
        .stApp [data-baseweb="tab-list"] {{
            gap: 0.4rem;
            padding: 0.3rem;
            background: rgba(8,16,30,.82) !important;
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,.08) !important;
        }}

        .stApp button[role="tab"] {{
            border-radius: 10px;
            min-height: 2.4rem;
            color: rgba(168,196,238,.70) !important;
            font-weight: 600;
        }}

        .stApp button[role="tab"][aria-selected="true"] {{
            background: rgba(18,30,52,.96) !important;
            color: var(--pm-title) !important;
            box-shadow: 0 2px 10px rgba(0,0,0,.32) !important;
        }}

        /* ── 提示条 (Alert) ── */
        .stApp [data-testid="stAlert"] {{
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,.08);
            box-shadow: var(--pm-shadow-soft);
        }}

        .stApp div[data-testid="stInfo"] {{
            background: rgba(50,100,185,.14) !important;
            border-color: rgba(74,140,220,.22) !important;
            color: rgba(160,205,255,.92) !important;
        }}

        .stApp div[data-testid="stSuccess"] {{
            background: rgba(55,155,95,.14) !important;
            border-color: rgba(75,185,115,.22) !important;
            color: rgba(130,215,160,.92) !important;
        }}

        .stApp div[data-testid="stWarning"] {{
            background: rgba(195,150,38,.14) !important;
            border-color: rgba(220,170,58,.22) !important;
            color: rgba(238,192,98,.92) !important;
        }}

        .stApp div[data-testid="stError"] {{
            background: rgba(195,58,58,.14) !important;
            border-color: rgba(218,75,75,.22) !important;
            color: rgba(255,148,148,.92) !important;
        }}

        /* ── File uploader ── */
        .stApp [data-testid="stFileUploader"] section {{
            background: rgba(10,18,32,.72) !important;
            border: 1px dashed rgba(255,255,255,.16) !important;
            border-radius: 16px !important;
        }}

        /* ── Progress bar ── */
        .stApp [data-testid="stProgressBar"] > div {{
            background: rgba(255,255,255,.08) !important;
            border-radius: 999px !important;
        }}

        .stApp [data-testid="stProgressBar"] > div > div {{
            background: linear-gradient(90deg, #3a6cb5, #5a9ae0) !important;
            border-radius: 999px !important;
        }}

        /* ── Divider ── */
        .stApp hr {{
            border-color: rgba(255,255,255,.08) !important;
        }}

        /* ── Caption ── */
        .stApp [data-testid="stCaptionContainer"],
        .stApp .stCaption,
        .stApp small {{
            color: var(--pm-muted) !important;
        }}

        /* ── Code ── */
        .stApp pre {{
            background: rgba(6,12,24,.95) !important;
            border: 1px solid rgba(255,255,255,.08) !important;
            border-radius: 14px !important;
        }}

        .stApp code {{
            background: rgba(255,255,255,.08) !important;
            color: rgba(175,215,255,.88) !important;
            border-radius: 4px !important;
            padding: 0.1em 0.3em;
        }}

        /* ── Radio / Checkbox ── */
        .stApp [data-testid="stRadio"] p,
        .stApp [data-testid="stCheckbox"] p {{
            color: rgba(182,208,242,.82) !important;
        }}

        /* ── Subheader ── */
        .stApp .stSubheader {{
            color: var(--pm-title) !important;
        }}

        /* ── Badge ── */
        .stApp .pm-badge {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            vertical-align: baseline;
            padding: 0.16rem 0.52rem;
            margin: 0 0.1rem;
            border-radius: 999px;
            background: var(--pm-badge-bg);
            color: var(--pm-badge-text);
            font-size: 0.88rem;
            line-height: 1.2;
            font-weight: 600;
            border: 1px solid rgba(88,184,118,.14);
            white-space: nowrap;
        }}

        /* ── 页面标题区 ── */
        .stApp .pm-page-header {{
            margin-bottom: 1.4rem;
        }}

        .stApp .pm-page-header__title {{
            margin: 0;
            font-size: 2.1rem;
            line-height: 1.12;
            color: var(--pm-title);
            font-weight: 800;
        }}

        .stApp .pm-page-header__subtitle {{
            margin: 0.4rem 0 0;
            color: var(--pm-muted);
            font-size: 0.98rem;
        }}

        /* ── Section 卡片 ── */
        .stApp .pm-section-card {{
            background: rgba(12,20,36,.84);
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 18px;
            box-shadow: var(--pm-shadow-soft);
            padding: 1.1rem 1.2rem;
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
        }}

        .stApp .pm-section-card__title {{
            margin: 0 0 0.5rem;
            color: var(--pm-title);
            font-size: 1.1rem;
            font-weight: 800;
        }}

        .stApp .pm-section-card__body {{
            color: var(--pm-text);
            font-size: 0.96rem;
            line-height: 1.72;
        }}

        /* ── 横幅提示条 ── */
        .stApp .pm-banner {{
            border-radius: 14px;
            padding: 0.9rem 1.05rem;
            border: 1px solid rgba(255,255,255,.08);
            box-shadow: var(--pm-shadow-soft);
            font-size: 0.96rem;
            line-height: 1.68;
            backdrop-filter: blur(10px);
        }}

        .stApp .pm-banner--info {{
            background: rgba(50,100,185,.14);
            color: rgba(155,205,255,.90);
            border-color: rgba(74,140,220,.22);
        }}

        .stApp .pm-banner--success {{
            background: rgba(55,155,95,.14);
            color: rgba(125,212,158,.90);
            border-color: rgba(75,185,115,.22);
        }}

        .stApp .pm-banner--danger {{
            background: rgba(195,58,58,.14);
            color: rgba(255,145,145,.90);
            border-color: rgba(218,75,75,.22);
        }}

        /* ── 空状态 ── */
        .stApp .pm-empty-state {{
            padding: 1.15rem 1.2rem;
            background: rgba(12,20,36,.66);
            border: 1px dashed rgba(255,255,255,.14);
            border-radius: 18px;
            color: var(--pm-muted);
            text-align: center;
            font-size: 0.96rem;
        }}

        /* ── HOME PAGE 专属布局（首页注入覆盖部分样式） ── */
        .stApp .pm-home-page {{
            position: relative;
            left: 50%;
            width: 100vw;
            margin-left: -50vw;
            padding: 0.5rem 0 3rem;
            isolation: isolate;
            overflow: clip;
        }}

        .stApp .pm-home-scene {{
            position: relative;
            z-index: 1;
            width: min({CONTENT_MAX_WIDTH_PX}px, calc(100vw - 4rem));
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 0;
        }}

        .stApp .pm-home-hero {{
            position: relative;
            border-radius: 0;
            overflow: visible;
        }}

        .stApp .pm-home-hero__content {{
            position: relative;
            z-index: 2;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            text-align: center;
            padding: 1.6rem 1.7rem 2rem;
        }}

        .stApp .pm-home-hero__eyebrow {{
            margin-bottom: 0.64rem;
            color: rgba(210,228,250,.70);
            font-size: 0.88rem;
            font-weight: 500;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }}

        .stApp .pm-home-hero__title {{
            margin: 0;
            max-width: 780px;
            color: #ffffff;
            font-size: clamp(2.4rem, 3.82vw, 3.48rem);
            line-height: 1.05;
            letter-spacing: -0.04em;
            font-weight: 800;
            text-shadow: 0 8px 22px rgba(4,10,18,.40);
        }}

        .stApp .pm-home-hero__subtitle {{
            max-width: 640px;
            margin: 1.1rem auto 0;
            color: rgba(218,235,252,.82);
            font-size: clamp(0.95rem, 1.1vw, 1.02rem);
            line-height: 1.7;
            text-shadow: 0 2px 10px rgba(4,10,18,.28);
        }}

        .stApp .pm-home-card-rail {{
            margin: 1.2rem 0 0;
            padding: 0;
        }}

        .stApp .pm-home-card-rail__inner {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.95rem;
        }}

        .stApp .pm-home-kpi-card {{
            position: relative;
            display: flex;
            flex-direction: column;
            min-height: 152px;
            padding: 1.2rem 1.4rem 1.2rem;
            border-radius: 18px;
            background: linear-gradient(
                180deg,
                rgba(28,38,54,.72) 0%,
                rgba(18,26,40,.58) 100%
            );
            border: 1px solid rgba(255,255,255,.10);
            box-shadow: 0 8px 24px rgba(0,0,0,.32);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
        }}

        .stApp .pm-home-kpi-label {{
            color: rgba(195,212,232,.84);
            font-size: .88rem;
            font-weight: 500;
        }}

        .stApp .pm-home-kpi-value {{
            margin-top: 0.32rem;
            color: #f4f9ff;
            font-size: clamp(1.9rem, 2.9vw, 2.55rem);
            line-height: 1.02;
            font-weight: 800;
            letter-spacing: -0.04em;
        }}

        .stApp .pm-home-kpi-note {{
            margin-top: 0.36rem;
            color: rgba(175,198,228,.62);
            font-size: .82rem;
            line-height: 1.4;
        }}

        .stApp .pm-home-rule-wrap {{
            margin-top: 2.2rem;
        }}

        .stApp .pm-home-rule-panel {{
            background: rgba(8,14,24,.60);
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 20px;
            padding: 1.5rem 1.7rem 1.8rem;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            box-shadow: 0 10px 32px rgba(0,0,0,.28);
        }}

        .stApp .pm-home-rule-panel__header {{
            padding: 0 0 0.9rem;
            border-bottom: 1px solid rgba(255,255,255,.08);
        }}

        .stApp .pm-home-rule-panel__title {{
            margin: 0;
            color: rgba(220,238,255,.88);
            font-size: 1.3rem;
            font-weight: 800;
            letter-spacing: -0.02em;
        }}

        .stApp .pm-home-rule-list {{
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            margin-top: 1rem;
            padding-left: 0.3rem;
        }}

        .stApp .pm-home-rule-item {{
            display: grid;
            grid-template-columns: 36px minmax(0,1fr);
            gap: 0.72rem;
            align-items: start;
        }}

        .stApp .pm-home-rule-pin {{
            display: flex;
            justify-content: center;
            padding-top: 0.2rem;
        }}

        .stApp .pm-home-rule-body {{
            padding: 0.85rem 1rem;
            border-radius: 14px;
            background: rgba(255,255,255,.028);
            border: 1px solid rgba(255,255,255,.05);
        }}

        .stApp .pm-home-rule-index {{
            width: 30px;
            height: 30px;
            border-radius: 999px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: #e8f4ff;
            font-size: 0.82rem;
            font-weight: 800;
            background: linear-gradient(180deg,rgba(62,106,168,.94) 0%,rgba(44,82,134,.94) 100%);
            box-shadow: inset 0 1px 0 rgba(255,255,255,.12);
        }}

        .stApp .pm-home-rule-text {{
            color: rgba(220,238,252,.86);
            font-size: 0.88rem;
            line-height: 1.68;
        }}

        .stApp .pm-home-rule-text .pm-badge {{
            background: rgba(140,210,175,.12);
            border-color: rgba(140,210,175,.14);
            color: #9ed4b8;
            font-size: 0.76rem;
            padding: 0.08rem 0.34rem;
        }}

        @media (max-width: 1100px) {{
            .stApp .pm-home-card-rail__inner {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
        }}

        @media (max-width: 768px) {{
            .stApp section.main > div.block-container {{
                padding-left: 1rem;
                padding-right: 1rem;
            }}

            .stApp .pm-home-hero__content {{
                padding: 1.2rem 1.1rem 1.6rem;
            }}

            .stApp .pm-home-card-rail__inner {{
                grid-template-columns: 1fr;
            }}

            .stApp .pm-home-rule-item {{
                grid-template-columns: 30px minmax(0,1fr);
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
