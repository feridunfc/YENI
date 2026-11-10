"""Hand-calculated scalar envelopes, independent of the production replay."""
from column_demand_fixture import DesignBank


class SpectralBank(DesignBank):
    def __init__(self):
        super().__init__()
        self.cases["SECOND_SPECTRUM"] = 4
        self.combos["RS_SUM"] = (0, [(0, "G", 1), (0, "Q", -.5), (0, "RS", 1), (0, "SECOND_SPECTRUM", .3)])
        self.combos["CAPTURED_HIGH"] = (0, [(0, "G", 1), (0, "Q", -.5), (0, "RS", 2.5), (0, "SECOND_SPECTRUM", .75)])
        # First-cut center: [-87.5,4,-5.5,7,8.5,-10]; signed Q coefficient.
        # First-cut radii: [11.5,23,34.5,46,57.5,69], or 2.5 times these.
        self.base_values = {
            ("G", "Single Value"): [-100, 2, -3, 4, 5, -6],
            ("Q", "Single Value"): [-25, -4, 5, -6, -7, 8],
            ("SUM", "Single Value"): [-180, -3.6, 3.8, -4, -4.2, 4.4],
            ("RS", "Max"): [10, 20, 30, 40, 50, 60],
            ("SECOND_SPECTRUM", "Max"): [5, 10, 15, 20, 25, 30],
            ("RS_SUM", "Max"): [-76, 27, 29, 53, 66, 59],
            ("RS_SUM", "Min"): [-99, -19, -40, -39, -49, -79],
            ("CAPTURED_HIGH", "Max"): [-58.75, 61.5, 80.75, 122, 152.25, 162.5],
            ("CAPTURED_HIGH", "Min"): [-116.25, -53.5, -91.75, -108, -135.25, -182.5],
        }
        for i, member in enumerate(self.members):
            self.forces[member] = []
            for (case, step), values in self.base_values.items():
                for j, (station, element, elm_station) in enumerate(((0, "A", 0), (2, "A", 2), (2, "B", 0), (3.3, "B", 1.3))):
                    scale = (i + 1) * (j + 1)
                    self.forces[member].append([member, station, member + element, elm_station, case, step, 0, *[v * scale for v in values]])
        for name, direction in (("RS", "U1"), ("SECOND_SPECTRUM", "U2")):
            self.call("LoadCases.ResponseSpectrum.GetLoads", "case", name, "NumberLoads LoadName Func SF CSys Ang pRetVal",
                [1, [direction], ["SYNTHETIC_FUNCTION"], [10], ["Global"], [0], 0])

    def source_row(self, case, step="Max", member_index=0, station=0):
        return next(r for r in self.forces[self.members[member_index]] if r[4] == case and r[5] == step and r[1] == station)
