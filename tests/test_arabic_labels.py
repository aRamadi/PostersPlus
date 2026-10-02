"""Arabic labels: joined letters, the Arabic label font, and original_labels."""
import dataclasses
import os
import unittest

import numpy as np
from PIL import Image

import fonts
import main
from i18n import (has_arabic, joined, load_languages, native_digits, translate_genre,
                  translate_sash, visual)
from main import RequestConfig, build_poster, build_request_config

INTER = os.path.join(fonts.FONTS_DIR, "Inter-Bold.ttf")
ALMARAI = os.path.join(fonts.FONTS_DIR, "Almarai-Bold.ttf")
TAJAWAL = os.path.join(fonts.FONTS_DIR, "Tajawal-Bold.ttf")


def _art(size=(500, 750)):
    return Image.new("RGBA", size, (16, 16, 24, 255))


class JoinedLettersTests(unittest.TestCase):
    def test_text_without_arabic_is_untouched(self):
        for text in ("", "Drama · 2019 ★ 87", "דרמה", "Ταινία"):
            self.assertEqual(joined(text), text)

    def test_each_letter_takes_the_form_its_place_in_the_word_needs(self):
        # دراما: dal, reh and alef never join the letter after them, so the
        # first three stand alone; meem starts a pair, the last alef ends it.
        self.assertEqual(joined("دراما"), "\uFEA9\uFEAD\uFE8D\uFEE3\uFE8E")

    def test_arabic_is_recognised_joined_or_not(self):
        self.assertTrue(has_arabic("عربي"))
        self.assertTrue(has_arabic(visual("عربي")))
        self.assertFalse(has_arabic("עברית"))
        self.assertFalse(has_arabic("Arabic"))
        self.assertFalse(has_arabic(""))

    def test_lam_alef_is_one_ligature(self):
        self.assertEqual(joined("لا"), "\uFEFB")

    def test_arabic_is_joined_then_drawn_right_to_left(self):
        self.assertEqual(visual("دراما"), "\uFE8E\uFEE3\uFE8D\uFEAD\uFEA9")
        # A right-to-left line: the genre that starts it is drawn at the
        # right, the numbers stay forwards.
        self.assertEqual(visual("دراما · 2026"), "2026 · \uFE8E\uFEE3\uFE8D\uFEAD\uFEA9")


class ArabicFontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_languages()

    def test_arabic_labels_are_drawn_in_almarai_unless_tajawal_is_chosen(self):
        for choice in ("inter", "rubik", "oswald", "almarai"):
            with self.subTest(choice):
                self.assertEqual(fonts.resolve_label_font(choice, "ar"), ALMARAI)
        self.assertEqual(fonts.resolve_label_font("inter", "ar-eg"), ALMARAI)
        self.assertEqual(fonts.resolve_label_font("tajawal", "ar"), TAJAWAL)

    def test_other_languages_keep_their_fonts(self):
        self.assertEqual(fonts.resolve_label_font("inter", "en"), INTER)
        self.assertEqual(fonts.resolve_label_font("inter", "fr"), INTER)

    def test_an_arabic_title_takes_the_arabic_font(self):
        bebas = os.path.join(fonts.FONTS_DIR, "BebasNeue-Bold.ttf")
        self.assertEqual(fonts.font_for_text(bebas, "حين لا يرانا أحد"), ALMARAI)

    def test_the_font_has_the_joined_forms(self):
        for path in (ALMARAI, TAJAWAL):
            self.assertTrue(fonts.covers(path, joined("حين لا يرانا أحد")))
        self.assertTrue(fonts.drawable("حين لا يرانا أحد"))
        self.assertFalse(fonts.drawable("기생충"))

    def test_arabic_labels_translate(self):
        self.assertEqual(translate_genre("Drama", "ar"), "دراما")
        self.assertEqual(translate_sash("Arabic", "ar"), "عربي")
        self.assertEqual(translate_sash("#3 Today", "ar"), "#٣ اليوم")
        self.assertEqual(translate_sash("#12 Today", "ar"), "#١٢ اليوم")
        self.assertEqual(translate_sash("Oct 16 Cinema", "ar"), "في السينما في ١٦ أكتوبر")


class PresentationFormTests(unittest.TestCase):
    """fontprep maps the joined forms a font reaches only through its
    OpenType features: Rubik has Arabic letters but none of the forms."""

    def test_forms_are_mapped_from_the_fonts_own_features(self):
        from fontTools.ttLib import TTFont
        import fontprep
        font = TTFont(os.path.join(fonts.FONTS_DIR, "Rubik-Bold.ttf"))
        cmap = font.getBestCmap()
        self.assertNotIn(0xFEE3, cmap)                      # meem, initial
        self.assertGreater(fontprep.add_arabic_presentation_forms(font), 0)
        cmap = font.getBestCmap()
        self.assertNotEqual(cmap[0xFEE3], cmap[0x0645])     # its own glyph
        self.assertEqual(cmap[0xFEE1], cmap[0x0645])        # isolated: the letter itself
        self.assertIn(0xFEFB, cmap)                          # lam-alef

    def test_a_font_without_arabic_is_left_alone(self):
        from fontTools.ttLib import TTFont
        import fontprep
        self.assertEqual(fontprep.add_arabic_presentation_forms(TTFont(INTER)), 0)


class NativeDigitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_languages()

    def test_rank_dates_and_seasons_take_arabic_digits(self):
        self.assertEqual(native_digits("12", "ar"), "١٢")
        self.assertEqual(native_digits("12", "en"), "12")
        self.assertEqual(native_digits("12", "he"), "12")
        self.assertEqual(translate_sash("Oct 16 Cinema", "ar"), "في السينما في ١٦ أكتوبر")
        self.assertEqual(translate_sash("Dec 2027 Cinema", "ar"), "في السينما في ديسمبر ٢٠٢٧")
        self.assertEqual(translate_sash("Mar 4 Season 3", "ar"), "الموسم ٣ في ٤ مارس")
        self.assertEqual(translate_sash("Oct 16 Cinema", "en"), "Oct 16 Cinema")
        self.assertEqual(translate_sash("#3 Today", "en"), "#3 Today")

    def test_the_year_takes_arabic_digits(self):
        cfg = RequestConfig(top_gradient="off", bottom_gradient="off", rating_display_mode=3)
        def render(year, lang):
            return np.array(build_poster(_art(), 87, "Drama", dataclasses.replace(cfg, label_language=lang),
                                         release_year=year))
        # An Arabic poster's year is drawn as if handed in Arabic digits.
        self.assertTrue(np.array_equal(render("2026", "ar"), render("٢٠٢٦", "ar")))


class OriginalLabelsConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_languages()

    def test_parses_to_sorted_base_languages(self):
        self.assertEqual(build_request_config({}).original_labels, "")
        self.assertEqual(build_request_config({"original_labels": "ar"}).original_labels, "ar")
        self.assertEqual(build_request_config({"original_labels": "HE, ar-EG,ar,x!"}).original_labels,
                         "ar,he")

    def test_the_default_leaves_cache_keys_alone(self):
        self.assertNotIn("original_labels", main._render_config_signature(build_request_config({})))
        self.assertIn("original_labels", main._render_config_signature(
            build_request_config({"original_labels": "ar"})))

    def test_the_per_render_language_is_not_in_the_cache_key(self):
        cfg = build_request_config({"original_labels": "ar"})
        self.assertEqual(main._render_config_signature(cfg),
                         main._render_config_signature(dataclasses.replace(cfg, label_language="ar")))

    def test_only_a_listed_language_with_a_translation_switches(self):
        cfg = build_request_config({"original_labels": "ar,ko"})
        self.assertEqual(main._own_label_language(cfg, "ar"), "ar")
        self.assertEqual(main._own_label_language(cfg, "en"), "")
        self.assertEqual(main._own_label_language(cfg, "ko"), "")    # no ko.json
        self.assertEqual(main._own_label_language(cfg, None), "")
        self.assertEqual(main._own_label_language(build_request_config({}), "ar"), "")

    def test_a_title_already_in_the_poster_language_needs_no_switch(self):
        cfg = build_request_config({"original_labels": "ar", "logo_language": "ar"})
        self.assertEqual(main._own_label_language(cfg, "ar"), "")

    def test_label_lang_follows_the_switch(self):
        cfg = build_request_config({"original_labels": "ar"})
        self.assertEqual(cfg.label_lang, "en")
        self.assertEqual(dataclasses.replace(cfg, label_language="ar").label_lang, "ar")

    def test_arabic_posters_cached_before_now_re_render(self):
        rev = next(r for r in main._RENDER_REVISIONS if r.rev == 20)
        self.assertTrue(rev.applies(build_request_config({"logo_language": "ar"})))
        self.assertTrue(rev.applies(build_request_config({"logo_language": "ar-sa"})))
        self.assertFalse(rev.applies(build_request_config({"logo_language": "en"})))


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_languages()

    def _render(self, title=None, **kwargs):
        cfg = RequestConfig(top_gradient="off", bottom_gradient="off", **kwargs)
        return np.array(build_poster(_art(), 87, "Drama", cfg, release_year="2026",
                                     fallback_title=title))

    def test_the_label_language_changes_the_labels(self):
        for mode in (1, 2, 3, 4):
            with self.subTest(mode=mode):
                self.assertFalse(np.array_equal(
                    self._render(rating_display_mode=mode),
                    self._render(rating_display_mode=mode, label_language="ar")))

    def test_switched_labels_draw_as_an_arabic_poster_does(self):
        for mode in (1, 2, 3, 4):
            with self.subTest(mode=mode):
                self.assertTrue(np.array_equal(
                    self._render(rating_display_mode=mode, label_language="ar"),
                    self._render(rating_display_mode=mode, logo_language="ar")))

    def test_an_arabic_title_is_drawn(self):
        blank = self._render(rating_display_mode=1)
        titled = self._render("حين لا يرانا أحد", rating_display_mode=1)
        self.assertFalse(np.array_equal(blank, titled))


if __name__ == "__main__":
    unittest.main()
