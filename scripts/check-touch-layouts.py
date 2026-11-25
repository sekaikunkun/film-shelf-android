#!/usr/bin/env python3
"""Verify TV actions keep D-pad focus without consuming a touch to take focus."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ANDROID = "{http://schemas.android.com/apk/res/android}"
RES = Path("app/src/leanback/res")


def node(layout, view_id=None):
    root = ET.parse(RES / "layout" / (layout + ".xml")).getroot()
    if view_id is None:
        return root
    nodes = [n for n in root.iter() if n.get(ANDROID + "id", "").split("/")[-1] == view_id]
    if len(nodes) != 1:
        raise ValueError(f"{layout}: expected exactly one {view_id}")
    return nodes[0]


def check_view(layout, view_id=None, touch="false"):
    view = node(layout, view_id)
    if view.get(ANDROID + "focusable") != "true" or view.get(ANDROID + "focusableInTouchMode") != touch:
        raise ValueError(f"{layout}/{view_id or 'row'}: D-pad focus or touch rule changed")


def check():
    for layout in ("adapter_func", "adapter_flag", "adapter_episode", "adapter_site_switch",
                   "adapter_site", "adapter_type", "adapter_vod", "adapter_vod_list", "adapter_vod_rect",
                   "adapter_vod_oval", "adapter_filter", "adapter_keyboard_icon", "adapter_keyboard_text", "adapter_search", "adapter_search_word",
                   "adapter_search_hot_word", "adapter_search_record", "adapter_quick"):
        check_view(layout)
    for layout, ids in {
        "activity_video": ("change1", "search", "keep"),
        "activity_setting": ("vod", "vodHome", "vodHistory"),
        "dialog_config": ("choose", "positive", "negative"),
    }.items():
        for view_id in ids:
            check_view(layout, view_id)
    check_view("adapter_config", "text")
    check_view("adapter_config", "delete", touch="true")
    for layout, view_id in (("activity_video", "video"), ("activity_search", "keyword")):
        check_view(layout, view_id, touch="true")
    style = ET.parse(RES / "values/styles.xml").find("./style[@name='Control']")
    values = {n.get("name"): n.text for n in style}
    if values.get("android:focusable") != "true" or values.get("android:focusableInTouchMode") != "false":
        raise ValueError("fullscreen playback controls lost click/focus contract")
    for kind in ("chip", "item", "site_item", "video_item", "keyboard", "vod", "vod_oval", "item_round", "search_hot_word"):
        selector = ET.parse(RES / "drawable" / f"selector_{kind}.xml").getroot()
        if not any(n.get(ANDROID + "state_pressed") == "true" for n in selector):
            raise ValueError(f"selector_{kind}: missing touch feedback")
    print("Touch/D-pad layout checks passed")


if __name__ == "__main__":
    try:
        check()
    except (ValueError, OSError, ET.ParseError) as exc:
        sys.exit(str(exc))
