"""Build ticket panel embed + dynamic persistent view (dropdown + buttons)."""

from __future__ import annotations

import re
from typing import Any, Awaitable, Callable, Optional

import discord

PANEL_SELECT_CUSTOM_ID = "warrior_panel_sel_v3"
BTN_PREFIX = "warrior_pb:"

PanelOpenHandler = Callable[..., Awaitable[None]]


def _style(name: str | None) -> discord.ButtonStyle:
    n = (name or "secondary").lower()
    if n == "link":
        n = "secondary"
    return {
        "primary": discord.ButtonStyle.primary,
        "secondary": discord.ButtonStyle.secondary,
        "success": discord.ButtonStyle.success,
        "danger": discord.ButtonStyle.danger,
        "link": discord.ButtonStyle.link,
    }.get(n, discord.ButtonStyle.secondary)


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_\-]", "_", s.strip())[:32]
    return s or "opt"


def build_panel_embed(cfg: dict[str, Any]) -> discord.Embed:
    e = discord.Embed(
        title=str(cfg.get("panel_title", "WARRIOR TICKET"))[:256],
        description=str(cfg.get("panel_description", ""))[:4096] or None,
        color=int(cfg.get("panel_color", 0xC41E3A)),
    )
    foot = str(cfg.get("panel_footer", "")).strip()
    if foot:
        e.set_footer(text=foot[:2048])
    pe = cfg.get("panel_embed") if isinstance(cfg.get("panel_embed"), dict) else {}
    th = str(pe.get("thumbnail_url", "")).strip()
    im = str(pe.get("image_url", "")).strip()
    an = str(pe.get("author_name", "")).strip()
    ai = str(pe.get("author_icon_url", "")).strip()
    if th:
        e.set_thumbnail(url=th)
    if im:
        e.set_image(url=im)
    if an or ai:
        e.set_author(name=(an[:256] if an else "\u200b"), icon_url=ai or discord.utils.MISSING)
    return e


def _dropdown_options(cfg: dict[str, Any]) -> list[discord.SelectOption]:
    dd = cfg.get("panel_dropdown") if isinstance(cfg.get("panel_dropdown"), dict) else {}
    opts: list[discord.SelectOption] = []
    for i, row in enumerate(dd.get("options") or []):
        if not isinstance(row, dict):
            continue
        opts.append(
            discord.SelectOption(
                label=str(row.get("label", "Option"))[:100],
                value=str(row.get("id", f"opt_{i}"))[:100],
                description=(str(row.get("description", "")) or None)[:100],
                emoji=row.get("emoji") or None,
            )
        )
    return opts[:25]


def _flatten_buttons(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    pb = cfg.get("panel_buttons") if isinstance(cfg.get("panel_buttons"), dict) else {}
    out: list[dict[str, Any]] = []
    for row in pb.get("rows") or []:
        if not isinstance(row, list):
            continue
        for b in row:
            if isinstance(b, dict) and b.get("id"):
                out.append(b)
    return out[:25]


class PanelSelect(discord.ui.Select):
    def __init__(
        self,
        placeholder: str,
        options: list[discord.SelectOption],
        opener: PanelOpenHandler,
    ):
        super().__init__(
            custom_id=PANEL_SELECT_CUSTOM_ID,
            placeholder=placeholder[:150] or "Select…",
            min_values=1,
            max_values=1,
            options=options if options else [discord.SelectOption(label="Support", value="support")],
        )
        self._open = opener

    async def callback(self, interaction: discord.Interaction) -> None:
        await self._open(
            interaction,
            self.values[0],
            source="dropdown",
            category_id_override=None,
        )


def build_panel_view(cfg: dict[str, Any], opener: PanelOpenHandler) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    dd = cfg.get("panel_dropdown") if isinstance(cfg.get("panel_dropdown"), dict) else {}
    opts = _dropdown_options(cfg)
    if dd.get("enabled", True) and opts:
        ph = str(dd.get("placeholder") or "Select ticket type…")
        view.add_item(PanelSelect(ph, opts, opener))

    pb = cfg.get("panel_buttons") if isinstance(cfg.get("panel_buttons"), dict) else {}
    if pb.get("enabled", False):
        flat = _flatten_buttons(cfg)
        for b in flat:
            bbd = dict(b)
            bid = _slug(str(bbd.get("id", "btn")))
            label = str(bbd.get("label", "Open"))[:80]
            emoji = bbd.get("emoji") or None
            style = _style(str(bbd.get("style", "primary")))

            async def _cb(interaction: discord.Interaction, d: dict[str, Any] = bbd) -> None:
                tid = str(d.get("type_id") or d.get("id") or "support")[:100]
                cat = d.get("category_id")
                cat_i: Optional[int] = None
                try:
                    if cat is not None and str(cat).strip():
                        cat_i = int(cat)
                except (TypeError, ValueError):
                    cat_i = None
                await opener(
                    interaction,
                    tid,
                    source="button",
                    category_id_override=cat_i,
                )

            btn = discord.ui.Button(
                style=style,
                label=label,
                emoji=emoji,
                custom_id=f"{BTN_PREFIX}{bid}",
            )
            btn.callback = _cb  # type: ignore[method-assign]
            view.add_item(btn)
    return view
