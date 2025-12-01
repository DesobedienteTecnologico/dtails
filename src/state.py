from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Dict, List, Optional, Tuple, Any, Iterable


OPTIONS_PATH = (Path(__file__).resolve().parents[1] / "options.json").resolve()

def load_options(parent=None) -> Dict[str, Any]:
    from PyQt5.QtWidgets import QMessageBox
    if not OPTIONS_PATH.exists():
        QMessageBox.critical(parent, "Missing options.json", f"File not found:\n{OPTIONS_PATH}")
        return {}
    try:
        return json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        QMessageBox.critical(parent, "Invalid options.json", f"Failed to parse JSON:\n{e}\n\nPath: {OPTIONS_PATH}")
        return {}

def save_options(data: Dict[str, Any], parent=None) -> None:
    from PyQt5.QtWidgets import QMessageBox
    try:
        OPTIONS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        QMessageBox.critical(parent, "Write error", f"Failed to write options.json:\n{e}\n\nPath: {OPTIONS_PATH}")


@dataclass
class AppState:
    dark_mode: bool = False
    selected_image: str = ""
    selected_device: Optional[Dict] = None
    selected_additions: List[str] = field(default_factory=list)
    selected_deletions: List[str] = field(default_factory=list)
    options_json: Optional[dict] = None
    version_overrides: Dict[str, str] = field(default_factory=dict)

    # ---------- size helpers ----------

    @staticmethod
    def _parse_size_to_bytes(val: Any) -> Optional[int]:
        try:
            if isinstance(val, (int, float)):
                return int(val)
            if isinstance(val, str):
                s = val.strip().lower()
                if s.endswith("gb"):
                    return int(float(s[:-2].strip()) * 1024 * 1024 * 1024)
                if s.endswith("mb"):
                    return int(float(s[:-2].strip()) * 1024 * 1024)
                if s.endswith("kb"):
                    return int(float(s[:-2].strip()) * 1024)
                if s.endswith("b"):
                    return int(float(s[:-1].strip()))
                return int(float(s) * 1024 * 1024)
        except Exception:
            return None
        return None

    @staticmethod
    def _fmt_bytes(n: Optional[int]) -> str:
        if not isinstance(n, int) or n < 0:
            return "unknown"
        gb = 1024 ** 3
        mb = 1024 ** 2
        kb = 1024
        if n >= gb:
            return f"{n / gb:.2f} GB"
        if n >= mb:
            return f"{n / mb:.1f} MB"
        if n >= kb:
            return f"{n / kb:.0f} KB"
        return f"{n} B"

    @staticmethod
    def _size_from_item(obj: dict) -> Optional[int]:
        if "size_bytes" in obj:
            return AppState._parse_size_to_bytes(obj.get("size_bytes"))
        if "size_mb" in obj:
            return int(float(obj["size_mb"]) * 1024 * 1024)
        if "size_gb" in obj:
            return int(float(obj["size_gb"]) * 1024 * 1024 * 1024)
        return AppState._parse_size_to_bytes(obj.get("size"))

    # ---------- item access over options.json ----------

    def _add_categories_iter(self) -> Iterable[Tuple[str, str, dict]]:
        """
        Yields (category_key, category_title, category_obj)
        Supports both 'new format' (add_software.categories[...]) and legacy dict format.
        """
        data = self.options_json or {}
        add = data.get("add_software", {})
        if isinstance(add, dict) and isinstance(add.get("categories"), list):
            for cat in add["categories"]:
                key = (cat.get("key") or "").strip().lower()
                title = cat.get("title") or key.title() or "Category"
                if key:
                    yield key, title, cat
            return
        if isinstance(add, dict):
            meta = data.get("add_software_meta", {})
            for key, items in add.items():
                k = (key or "").strip().lower()
                if not k:
                    continue
                title = (meta.get(k, {}) or {}).get("title") or k.title()
                cat = {"key": k, "title": title, "items": items or []}
                yield k, title, cat

    def _add_items_iter(self) -> Iterable[Tuple[str, dict]]:
        """
        Yields (category_key, item_obj)
        """
        for cat_key, _title, cat in self._add_categories_iter():
            for it in cat.get("items", []) if "items" in cat else (cat or {}).get("items", []):
                if isinstance(it, dict):
                    yield cat_key, it

    def find_add_item(self, name: str) -> Optional[dict]:
        """
        Finds an item by its name (case-insensitive) in add_software.
        Returns the raw item dict (with commands, sizes, etc) or None.
        """
        n = (name or "").strip().lower()
        if not n:
            return None
        for _cat_key, it in self._add_items_iter():
            it_name = (it.get("name") or "").strip().lower()
            if it_name == n:
                return it
        return None

    def install_command_plan(self) -> List[dict]:
        """
        Builds a command plan for the currently selected additions.
        Each entry: { "name": str, "internal_commands": [str], "external_commands": [str] }
        Missing fields default to empty lists.
        """
        plan: List[dict] = []
        for sel in self.selected_additions:
            it = self.find_add_item(sel) or {}
            plan.append(
                {
                    "name": sel,
                    "internal_commands": [c for c in it.get("internal_commands", []) if isinstance(c, str) and c.strip()],
                    "external_commands": [c for c in it.get("external_commands", []) if isinstance(c, str) and c.strip()],
                }
            )
        return plan

    # ---------- size aggregation for summary ----------

    def _all_items_map(self) -> Dict[str, int]:
        mapped: Dict[str, int] = {}
        for _cat_key, it in self._add_items_iter():
            name = (it.get("name") or "").strip()
            if not name:
                continue
            size = self._size_from_item(it)
            if size is not None:
                mapped[name] = size
        data = self.options_json or {}
        rem = data.get("remove_software", [])
        if isinstance(rem, list):
            for it in rem:
                name = (it.get("name") or "").strip()
                if not name:
                    continue
                size = self._size_from_item(it)
                if size is not None:
                    mapped[name] = size
        return mapped

    def _sizes_for_names(self, names: List[str]) -> List[Tuple[str, Optional[int]]]:
        mp = self._all_items_map()
        return [(n, mp.get(n)) for n in names]

    # ---------- UI-facing bits ----------

    @property
    def device_label(self) -> str:
        if not self.selected_device:
            return "— not selected —"
        vendor = self.selected_device.get("vendor") or ""
        model = self.selected_device.get("model") or self.selected_device.get("name", "")
        size = self.selected_device.get("size") or ""
        txt = " ".join(x for x in (vendor, size, model) if x).strip()
        return txt or "— not selected —"

    @property
    def image_label(self) -> str:
        return Path(self.selected_image).name if self.selected_image else "— not selected —"

    def summary_html(self) -> str:
        add_pairs = self._sizes_for_names(self.selected_additions)
        total_add = sum((sz or 0) for _, sz in add_pairs)
        
        if add_pairs:
            add_lines = [f"<li>{n} — <strong>{self._fmt_bytes(sz)}</strong></li>" for n, sz in add_pairs]
            adds_html = "<ul>" + "".join(add_lines) + f"</ul><b>Total install size:</b> {self._fmt_bytes(total_add)}"
        else:
            adds_html = "— none —"
            
        del_pairs = self._sizes_for_names(self.selected_deletions)
        total_del = sum((sz or 0) for _, sz in del_pairs)
        
        if del_pairs:
            del_lines = [f"<li>{n} — <strong>{self._fmt_bytes(sz)}</strong></li>" for n, sz in del_pairs]
            dels_html = "<ul>" + "".join(del_lines) + f"</ul><b>Total remove size:</b> {self._fmt_bytes(total_del)}"
        else:
            dels_html = "— none —"

        img_bytes = self._image_size_bytes() or 0
        approx_bytes = img_bytes + total_add - total_del

        tail = (
            "<br><hr>"
            f"<b>Image file size:</b> {self._fmt_bytes(img_bytes)} "
            f"(<i>{self._fmt_gb(img_bytes)}</i>)<br>"
            f"<b>Install total:</b> {self._fmt_bytes(total_add)} "
            f"(<i>{self._fmt_gb(total_add)}</i>)<br>"
            f"<b>Remove total:</b> {self._fmt_bytes(total_del)} "
            f"(<i>{self._fmt_gb(total_del)}</i>)<br>"
            f"<b>Approx. final size:</b> <u>{self._fmt_gb(approx_bytes)}</u>"
        )

        return (
            f"<div style='font-family: Arial, sans-serif; color: #333;'>"
            f"<h2>Summary</h2>"
            f"<p><b>Image:</b> {self.image_label}</p>"
            f"<p><b>Device:</b> {self.device_label}</p><br>"
            f"<h3>Will install:</h3>{adds_html}<br>"
            f"<h3>Will remove:</h3>{dels_html}<br>"
            f"{tail}"
            f"</div>"
        )


    def ready_to_write(self) -> bool:
        return bool(self.selected_image and self.selected_device)

    def _image_size_bytes(self) -> Optional[int]:
        try:
            p = Path(self.selected_image)
            if p.is_file():
                return p.stat().st_size
        except Exception:
            return None
        return None

    @staticmethod
    def _fmt_gb(n_bytes: Optional[int]) -> str:
        if not isinstance(n_bytes, int) or n_bytes < 0:
            return "unknown"
        return f"{n_bytes / (1024 ** 3):.2f} GB"

    def get_effective_version(self, name: str) -> Optional[str]:
        """
        Return version override if present; otherwise the JSON 'version' for that item.
        """
        if not name:
            return None
        if name in self.version_overrides and self.version_overrides[name].strip():
            return self.version_overrides[name].strip()
        it = self.find_add_item(name) or {}
        v = (it.get("version") or "").strip()
        return v or None

    def set_version_override(self, name: str, version: str) -> None:
        if not name:
            return
        version = (version or "").strip()
        if version:
            self.version_overrides[name] = version
        else:
            self.version_overrides.pop(name, None)