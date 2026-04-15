import unittest

import pricer


class TestPricer(unittest.TestCase):
    def test_harbor_area_parser(self):
        self.assertAlmostEqual(pricer._parse_harbor_area_sqft("4' x 8' x .080"), 32.0)  # pylint: disable=protected-access
        self.assertAlmostEqual(pricer._parse_harbor_area_sqft('24" x 10 yd'), 60.0)  # pylint: disable=protected-access
        self.assertAlmostEqual(pricer._parse_harbor_area_sqft('54" x 164\''), 738.0)  # pylint: disable=protected-access

    def test_sign_quote(self):
        data, warnings = pricer.load_prices("prices.txt")
        self.assertIsInstance(warnings, list)
        quote = pricer.quote_sign(
            data,
            material_key="alum_040",
            process_type="PRINT",
            process_key="eco",
            width_in=24,
            height_in=18,
            quantity=2,
            markup_multiplier=1.0,
            discount_percent=0.0,
            waste_percent=0.0,
        )
        self.assertAlmostEqual(quote["sqft"], 3.0)
        self.assertAlmostEqual(quote["total"], 47.46)
        self.assertAlmostEqual(quote["my_cost"], 47.46)
        self.assertAlmostEqual(quote["profit"], 0.0)

    def test_decal_sign_quote_no_media_cost(self):
        data, _ = pricer.load_prices("prices.txt")
        quote = pricer.quote_sign(
            data,
            material_key="decal",
            process_type="PLOT",
            process_key="cast_vinyl",
            width_in=24,
            height_in=12,
            quantity=2,
            markup_multiplier=1.0,
            discount_percent=0.0,
            waste_percent=0.0,
        )
        # sqft = 2, cost = (0 + 1.16) * 2 * 2 = 4.64
        self.assertAlmostEqual(float(quote["my_cost"]), 4.64)
        self.assertAlmostEqual(float(quote["minimum_charge"]), 35.0)
        self.assertAlmostEqual(float(quote["customer_price"]), 35.0)
        self.assertGreater(float(quote["minimum_charge_applied"]), 0)
        self.assertIn("cost_breakdown", quote)

    def test_shirt_quote(self):
        data, _ = pricer.load_prices("prices.txt")
        quote = pricer.quote_shirt(
            data,
            blank_key="g2000",
            decoration_key="htv_basic",
            quantity=5,
        )
        self.assertAlmostEqual(quote["per_shirt"], 10.0)
        self.assertAlmostEqual(quote["total"], 50.0)

    def test_wholesale_subout_sqft_quote(self):
        data, _ = pricer.load_prices("prices.txt")
        quote = pricer.quote_wholesale_subout(
            data,
            item_key="rigid_aluminum_040",
            quantity=2,
            width_in=24,
            height_in=18,
        )
        self.assertEqual(quote["unit"], "sqft")
        self.assertAlmostEqual(float(quote["sqft_each"]), 3.0)
        self.assertAlmostEqual(float(quote["billable_units_total"]), 6.0)
        self.assertAlmostEqual(float(quote["total"]), 48.0)

    def test_wholesale_subout_each_quote(self):
        data, _ = pricer.load_prices("prices.txt")
        quote = pricer.quote_wholesale_subout(
            data,
            item_key="rigid_coroplast_18x24_ds_20_90",
            quantity=5,
        )
        self.assertEqual(quote["unit"], "each")
        self.assertAlmostEqual(float(quote["billable_units_total"]), 5.0)
        self.assertAlmostEqual(float(quote["total"]), 40.0)

    def test_malformed_falls_back_to_defaults(self):
        lines = [
            "MATERIAL,only_two_fields",
            "PRINT,bad,missing,field",
            "SHIRT,also,bad",
        ]
        data, warnings = pricer.parse_prices_lines(lines)
        self.assertTrue(warnings)
        self.assertIn("alum_040", data["MATERIAL"])
        self.assertIn("g2000", data["SHIRT"])

    def test_validation_errors(self):
        data, _ = pricer.load_prices("prices.txt")
        with self.assertRaises(ValueError):
            pricer.quote_sign(
                data,
                material_key="missing",
                process_type="PRINT",
                process_key="eco",
                width_in=10,
                height_in=10,
                quantity=1,
            )
        with self.assertRaises(ValueError):
            pricer.quote_shirt(data, "g2000", "htv_basic", 0)

    def test_garment_quote(self):
        data, _ = pricer.load_prices("prices.txt")
        quote = pricer.quote_garment(
            data,
            product_type="shirt",
            tier="premium",
            quantity=3,
            markup_multiplier=1.0,
            discount_percent=0.0,
            waste_percent=0.0,
        )
        self.assertEqual(quote["product_type"], "shirt")
        self.assertEqual(quote["tier"], "premium")
        self.assertAlmostEqual(float(quote["price_each"]), 14.0)
        self.assertAlmostEqual(float(quote["total"]), 42.0)

    def test_sign_quote_with_led_mods_rgb(self):
        data, _ = pricer.load_prices("prices.txt")
        quote = pricer.quote_sign(
            data,
            material_key="alum_040",
            process_type="PRINT",
            process_key="eco",
            width_in=24,
            height_in=18,
            quantity=1,
            markup_multiplier=1.0,
            discount_percent=0.0,
            waste_percent=0.0,
            led={
                "enabled": True,
                "led_type": "mods",
                "color_mode": "rgb",
                "linear_ft": 10,
                "controller_key": "eco",
            },
        )
        self.assertTrue(quote["led_included"])
        self.assertAlmostEqual(float(quote["led"]["required_watts"]), 38.0)
        self.assertAlmostEqual(float(quote["led"]["suggested_power_supply_watts"]), 60.0)
        self.assertAlmostEqual(float(quote["led_total"]), 105.0)
        self.assertAlmostEqual(float(quote["total"]), 128.73)

    def test_markup_and_discount_financials(self):
        data, _ = pricer.load_prices("prices.txt")
        quote = pricer.quote_garment(
            data,
            product_type="shirt",
            tier="premium",
            quantity=3,
            markup_multiplier=2.0,
            discount_percent=10.0,
            waste_percent=0.0,
        )
        self.assertAlmostEqual(float(quote["cost_total"]), 42.0)
        self.assertAlmostEqual(float(quote["customer_price_before_discount"]), 84.0)
        self.assertAlmostEqual(float(quote["discount_amount"]), 8.4)
        self.assertAlmostEqual(float(quote["customer_price"]), 75.6)
        self.assertAlmostEqual(float(quote["customer_price_each"]), 25.2)
        self.assertAlmostEqual(float(quote["profit"]), 33.6)

    def test_profile_based_markup(self):
        data, _ = pricer.load_prices("prices.txt")
        policy, _ = pricer.load_pricing_policy("pricing_policy.json")
        quote = pricer.quote_garment(
            data,
            product_type="shirt",
            tier="eco",
            quantity=2,
            pricing_policy=policy,
            pricing_profile="aggressive",
        )
        self.assertEqual(quote["pricing_profile"], "aggressive")
        self.assertAlmostEqual(float(quote["markup_multiplier"]), 3.0)

    def test_harbor_frequents_populate_sign_menus(self):
        data, _ = pricer.load_prices("prices.txt")
        self.assertIn("alum_040", data["MATERIAL"])
        self.assertEqual(data["MATERIAL"]["alum_040"]["label"], "040 Aluminum")
        self.assertIn("coro_4mm", data["MATERIAL"])
        self.assertEqual(data["MATERIAL"]["coro_4mm"]["label"], "4mm Coro")
        self.assertIn("coro_10mm", data["MATERIAL"])
        self.assertIn("calendar_vinyl", data["PLOT"])
        self.assertIn("cast_vinyl", data["PLOT"])
        self.assertFalse(any(k.startswith("hf_") for k in data["MATERIAL"]))

    def test_garment_graphics_pricing(self):
        data, _ = pricer.load_prices("prices.txt")
        quote = pricer.quote_garment(
            data,
            product_type="shirt",
            tier="eco",
            quantity=2,
            markup_multiplier=1.0,
            discount_percent=0.0,
            waste_percent=0.0,
            graphics={
                "enabled": True,
                "front_key": "front_full",
                "back_key": "back_full",
                "colors": "2",
            },
        )
        self.assertAlmostEqual(float(quote["base_cost_total"]), 20.0)
        self.assertAlmostEqual(float(quote["graphics_cost_total"]), 20.24)
        self.assertAlmostEqual(float(quote["cost_total"]), 40.24)
        self.assertEqual(quote["graphics"]["colors"], "2")

    def test_labor_rounding_to_half_hour(self):
        data, _ = pricer.load_prices("prices.txt")
        quote = pricer.quote_sign(
            data,
            material_key="decal",
            process_type="PRINT",
            process_key="eco",
            width_in=12,
            height_in=12,
            quantity=1,
            markup_multiplier=1.0,
            discount_percent=0.0,
            labor_hours=1,
            labor_minutes=20,
            labor_rate_per_hour=65,
            waste_percent=0.0,
        )
        self.assertAlmostEqual(float(quote["cost_breakdown"]["manual_labor_hours_rounded"]), 1.5)
        self.assertAlmostEqual(float(quote["cost_breakdown"]["manual_labor"]), 97.5)


if __name__ == "__main__":
    unittest.main()
