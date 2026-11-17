"""Grouping must retain the exact member population and engineering distinctions."""
import unittest

from tbdy_next.member_groups import geometry_groups, material_member_groups, member_id_text


def member(identity, *, story="+9.00", section="B60x70", width="600", status="MEETS_SUBCONDITION"):
    return {"element_id": identity, "story": story, "section": section,
            "material_name": "C35/45", "material_classification": "RESOLVED_CONCRETE_USAGE",
            "width_mm": width, "depth_mm": "700", "limit": "300", "status": status}


class MemberGroupingTests(unittest.TestCase):
    def test_geometry_preserves_section_status_and_story(self):
        checks = [member("391"), member("392"), member("394"),
                  member("393", section="B30x70", width="300"),
                  member("400", status="NOT_PROVEN"), member("420", story="+4.50")]
        groups = geometry_groups(checks)
        self.assertEqual([group["member_count"] for group in groups], [4, 1, 1])
        self.assertEqual(groups[0]["members_by_story"], [
            {"story": "+9.00", "member_ids": ["391", "392", "394"], "member_ids_text": "391–392, 394"},
            {"story": "+4.50", "member_ids": ["420"], "member_ids_text": "420"},
        ])
        self.assertEqual(groups[1]["section"], "B30x70")
        self.assertEqual(groups[2]["status"], "NOT_PROVEN")

    def test_material_counts_each_beam_once(self):
        beam = member("1")
        native = [
            {"check_id": "column_rect_min", "items": [member("2", section="C80")]},
            *({"check_id": key, "items": [beam]} for key in (
                "beam_width_min", "beam_depth_min", "beam_depth_width")),
        ]
        self.assertEqual([(row["material_name"], row["member_type"], row["member_count"])
                          for row in material_member_groups(native)], [("C35/45", "Column", 1), ("C35/45", "Beam", 1)])

    def test_native_labels_and_gaps_are_preserved(self):
        self.assertEqual(member_id_text(["3", "1", "5", "2", "007", "B9"]), "1–3, 5, 007, B9")
