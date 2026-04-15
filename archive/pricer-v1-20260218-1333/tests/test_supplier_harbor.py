import unittest

import supplier_harbor


class TestSupplierHarbor(unittest.TestCase):
    def test_extract_price(self):
        html = "<div>Our Price: $52.93</div>"
        price = supplier_harbor.extract_price(
            html, r"Our Price[^$]*\$\s*([0-9]+(?:\.[0-9]{2})?)"
        )
        self.assertAlmostEqual(price, 52.93)

    def test_update_prices_lines(self):
        lines = [
            "MATERIAL,pvc_3mm,3mm PVC,2.50",
            "LED_MODS,mods_rgb,Modules RGB,rgb,12,3.8,9.00",
        ]
        updated = supplier_harbor._update_prices_lines(  # pylint: disable=protected-access
            lines,
            {
                ("MATERIAL", "pvc_3mm"): (3, 3.14),
                ("LED_MODS", "mods_rgb"): (6, 8.75),
            },
        )
        self.assertEqual(updated[0], "MATERIAL,pvc_3mm,3mm PVC,3.14")
        self.assertEqual(updated[1], "LED_MODS,mods_rgb,Modules RGB,rgb,12,3.8,8.75")

    def test_upsert_frequents(self):
        lines = [
            "MATERIAL,alum_040,.040 Aluminum,3.91",
            "HARBOR_FREQUENT,old_key,Old Item,Type,OLD001,10.00",
        ]
        frequents = [
            supplier_harbor.FrequentItem(
                key="new_item",
                label="New Item",
                product_type="Aluminum Sheets",
                code="NEW001",
                price=12.34,
            )
        ]
        updated = supplier_harbor._upsert_frequents(  # pylint: disable=protected-access
            lines, frequents
        )
        self.assertTrue(any(x.startswith("HARBOR_FREQUENT,new_item,") for x in updated))
        self.assertFalse(any("old_key" in x for x in updated))


if __name__ == "__main__":
    unittest.main()
