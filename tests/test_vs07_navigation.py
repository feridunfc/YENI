"""Navigation ownership and the shared report context; no visual snapshots."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import unittest

from tbdy_next.quick_checks import check_registry


STATIC = Path(__file__).parents[1] / "src" / "tbdy_next" / "static"


class PageStructure(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.stack = []
        self.ids = Counter()
        self.ancestors = {}
        self.attrs = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        identity = attrs.get("id")
        if identity:
            self.ids[identity] += 1
            self.ancestors[identity] = tuple(self.stack)
            self.attrs[identity] = attrs
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img",
                       "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append((tag, identity, attrs.get("class", "")))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return


class NavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PageStructure((STATIC / "index.html").read_text(encoding="utf-8"))

    def test_each_check_belongs_to_its_engineering_subject(self):
        registry = {c["check_id"]: c for c in check_registry()}
        expected = {
            "concrete_fck_25": 1, "modal_mass_95": 7, "STORY_DRIFT": 8,
            "a1_torsion_x": 9, "a1_torsion_y": 9, "WEAK_STORY_B1": 9,
            "SOFT_STORY_B2": 9, "beam_width_min": 11, "beam_depth_min": 11,
            "beam_depth_width": 11, "column_rect_min": 12, "WALL_GEOMETRY_CHECK": 13,
        }
        self.assertEqual({key: row["tab_id"] for key, row in registry.items()}, expected)
        self.assertEqual(len(check_registry()), len(registry))
        self.assertNotIn("EFFECTIVE_DRIFT", registry, "C2 remains a STORY_DRIFT scenario")

    def test_registry_targets_exist_in_the_correct_content_region(self):
        for check in check_registry():
            target = check.get("panel_id")
            if not target:
                continue
            with self.subTest(check=check["check_id"]):
                self.assertEqual(self.page.ids[target], 1)
                self.assertEqual(self.page.attrs[target]["data-check-panel"], check["check_id"])
                region = {8: "systemcontent", 9: "extraContent", 13: "wallcontent"}[check["tab_id"]]
                self.assertIn(region, [item[1] for item in self.page.ancestors[target]])
        for identity in ("b1R", "b1WallType"):
            self.assertIn("vs06-b1-panel", [item[1] for item in self.page.ancestors[identity]])

    def test_unique_ids_global_export_and_compact_right_context(self):
        self.assertTrue(self.page.ids)
        self.assertEqual({key: count for key, count in self.page.ids.items() if count > 1}, {})
        quick_parents = [item[1] for item in self.page.ancestors["quick-panel"]]
        self.assertNotIn("activecontent", quick_parents)
        self.assertTrue(any(tag == "main" for tag, _, _ in self.page.ancestors["trail"]))
        self.assertTrue(any(tag == "aside" and "rail" in css.split()
                            for tag, _, css in self.page.ancestors["modeltree"]))
        self.assertFalse(any(tag == "aside" and "rail" in css.split()
                             for tag, _, css in self.page.ancestors["resulttree"]))


if __name__ == "__main__":
    unittest.main()
