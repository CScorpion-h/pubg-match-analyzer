"""可复用的页面组件。"""

from __future__ import annotations

import base64
import html
from pathlib import Path
from textwrap import dedent
from typing import Iterable

import streamlit as st


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


def _emit(markup: str) -> None:
    """统一输出 HTML 片段。"""
    st.markdown(dedent(markup).strip(), unsafe_allow_html=True)


def badge(text: str) -> str:
    """返回统一 badge 样式。"""
    return f'<span class="pm-badge">{html.escape(text)}</span>'


def load_asset_data_uri(file_name: str) -> str:
    """读取本地素材并转成 data URI。"""
    asset_path = ASSETS_DIR / file_name
    if not asset_path.exists():
        return ""

    suffix = asset_path.suffix.lower()
    mime = "image/png"
    if suffix in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif suffix == ".webp":
        mime = "image/webp"

    encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def render_hero_banner(
    title: str,
    subtitle: str,
    eyebrow: str,
    background_image: str,
) -> str:
    """渲染首页 hero banner。"""
    hero_background = (
        f"background-image: url('{background_image}');"
        if background_image
        else "background: linear-gradient(180deg, #617180 0%, #485664 100%);"
    )
    return dedent(
        f"""
        <div class="pm-home-hero" style="{hero_background}">
            <div class="pm-home-hero__content">
                <div class="pm-home-hero__eyebrow">{html.escape(eyebrow)}</div>
                <h1 class="pm-home-hero__title">{html.escape(title)}</h1>
                <p class="pm-home-hero__subtitle">{html.escape(subtitle)}</p>
            </div>
        </div>
        """
    ).strip()


def render_stat_card(label: str, value: str, helper: str) -> str:
    """返回首页指标卡 HTML（紧凑无换行，避免 Markdown 把缩进行识别为代码块）。"""
    return (
        '<div class="pm-home-kpi-card">'
        f'<div class="pm-home-kpi-label">{html.escape(label)}</div>'
        f'<div class="pm-home-kpi-value">{html.escape(value)}</div>'
        f'<div class="pm-home-kpi-note">{html.escape(helper)}</div>'
        '</div>'
    )


def render_rule_item(index: int, html_content: str) -> str:
    """返回单条规则项结构（紧凑无换行）。"""
    return (
        '<div class="pm-home-rule-item">'
        '<div class="pm-home-rule-pin">'
        f'<div class="pm-home-rule-index">{index}</div>'
        '</div>'
        '<div class="pm-home-rule-body">'
        f'<div class="pm-home-rule-text">{html_content}</div>'
        '</div>'
        '</div>'
    )

def render_rule_panel(items: str) -> str:
    """返回首页规则面板 HTML（紧凑无换行）。"""
    return (
        '<div class="pm-home-rule-panel">'
        '<div class="pm-home-rule-panel__header">'
        '<h2 class="pm-home-rule-panel__title">当前规则说明</h2>'
        '</div>'
        f'<div class="pm-home-rule-list">{items}</div>'
        '</div>'
    )


def render_home_landing(
    eyebrow: str,
    title: str,
    subtitle: str,
    background_image: str,
    stat_cards: Iterable[str],
    rule_items: Iterable[str],
) -> None:
    """渲染首页整体舞台。"""
    cards_html = "".join(stat_cards)
    rules_html = "".join(rule_items)

    bg_val = f"url('{background_image}')" if background_image else "linear-gradient(180deg,#1a2433 0%,#0d1521 100%)"

    # Home-page-specific full-screen overrides (injected only when this page renders)
    # 首页专属覆盖：更亮的叠加层（让背景图更可见）+ 侧栏半透明（透出背景图）
    # 全局通用样式（sidebar 颜色层级、组件暗色主题等）已由 apply_global_styles() 处理
    home_css = (
        "<style>"
        ".stApp [data-testid='stAppViewContainer']{"
        "background:linear-gradient(180deg,rgba(5,9,16,.38) 0%,rgba(4,8,14,.56) 38%,"
        "rgba(3,6,12,.78) 72%,rgba(2,5,10,.92) 100%)!important;}"
        ".stApp [data-testid='stSidebar']{"
        "background:rgba(6,12,22,.56)!important;"
        "backdrop-filter:blur(18px)!important;-webkit-backdrop-filter:blur(18px)!important;}"
        "</style>"
    )

    # Build compact HTML (zero indentation) to prevent Markdown treating indented lines as code blocks
    html_body = (
        '<div class="pm-home-page">'
        '<div class="pm-home-scene">'
        '<div class="pm-home-hero-wrap">'
        '<div class="pm-home-hero">'
        '<div class="pm-home-hero__content">'
        f'<div class="pm-home-hero__eyebrow">{html.escape(eyebrow)}</div>'
        f'<h1 class="pm-home-hero__title">{html.escape(title)}</h1>'
        f'<p class="pm-home-hero__subtitle">{html.escape(subtitle)}</p>'
        '</div>'
        '</div>'
        '</div>'
        '<div class="pm-home-card-rail">'
        '<div class="pm-home-card-rail__inner">'
        f'{cards_html}'
        '</div>'
        '</div>'
        '<div class="pm-home-rule-wrap">'
        f'{render_rule_panel(rules_html)}'
        '</div>'
        '</div>'
        '</div>'
    )

    # Use st.markdown directly to bypass _emit's dedent (which mistakes indented HTML for code blocks)
    st.markdown(home_css + html_body, unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str) -> None:
    """渲染统一页面标题区。"""
    _emit(
        f"""
        <div class="pm-page-header">
            <h1 class="pm-page-header__title">{html.escape(title)}</h1>
            <p class="pm-page-header__subtitle">{html.escape(subtitle)}</p>
        </div>
        """
    )


def render_section_card(title: str | None = None, body: str | None = None) -> None:
    """渲染静态内容卡片。"""
    title_html = f'<h3 class="pm-section-card__title">{html.escape(title)}</h3>' if title else ""
    body_html = f'<div class="pm-section-card__body">{body or ""}</div>' if body else ""
    _emit(f'<div class="pm-section-card">{title_html}{body_html}</div>')


def render_info_banner(text: str, tone: str = "info") -> None:
    """渲染信息横幅。"""
    tone = tone if tone in {"info", "success", "danger"} else "info"
    _emit(f'<div class="pm-banner pm-banner--{tone}">{html.escape(text)}</div>')


def render_empty_state(text: str) -> None:
    """渲染空状态占位。"""
    _emit(f'<div class="pm-empty-state">{html.escape(text)}</div>')
