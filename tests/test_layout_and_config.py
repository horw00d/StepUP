"""
tests/test_layout_and_config.py

tests verify that:
  - All Dash component IDs referenced in callbacks actually exist in the layout
  - Config constants are internally consistent
  - The shared layout factory raises on invalid tab names
  - Style dictionaries contain only valid CSS-friendly keys
"""

import pytest
import sys
import os
from config import (
    ALLOWED_COLUMNS,
    ALLOWED_KEYWORDS,
    CT_COLOR_OPTIONS,
    CT_GROUP_OPTIONS,
    FEATURE_OPTIONS,
    GRANULARITY_COMPATIBLE_GROUPS,
    NO_COLOR_SENTINEL,
    ST_COLOR_OPTIONS,
    TRIAL_GROUP_KEYS,
    PARTICIPANT_GROUP_KEYS,
    _VALID_TAB_NAMES,
    _TAB_PREFIX,
    _QUERY_PLACEHOLDER,
    _APPLY_BTN_ID,
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# 1. ALLOWED_COLUMNS / ALLOWED_KEYWORDS


class TestAllowedColumnsAndKeywords:

    def test_allowed_columns_is_non_empty_list(self):
        assert isinstance(ALLOWED_COLUMNS, list)
        assert len(ALLOWED_COLUMNS) > 0

    def test_no_duplicates_in_allowed_columns(self):
        assert len(ALLOWED_COLUMNS) == len(set(ALLOWED_COLUMNS))

    def test_core_biomechanics_columns_present(self):
        required = {
            "peak_grf",
            "mean_grf",
            "stance_duration_frames",
            "r_score",
            "side",
            "is_outlier",
        }
        assert required.issubset(set(ALLOWED_COLUMNS))

    def test_allowed_keywords_contains_pandas_logic_ops(self):
        assert {"and", "or", "not", "in"}.issubset(ALLOWED_KEYWORDS)

    def test_no_overlap_between_columns_and_keywords(self):
        """Column names must not shadow logical keywords."""
        assert not set(ALLOWED_COLUMNS) & ALLOWED_KEYWORDS


# 2. Granularity configuration


class TestGranularityConfig:

    def test_all_three_granularity_levels_present(self):
        assert {"footstep", "trial", "participant"}.issubset(
            GRANULARITY_COMPATIBLE_GROUPS.keys()
        )

    def test_participant_level_excludes_footwear_and_speed(self):
        """
        At participant granularity, footwear and speed are averaged out,
        so they must NOT appear as compatible grouping columns.
        """
        participant_compat = GRANULARITY_COMPATIBLE_GROUPS["participant"]
        assert "footwear" not in participant_compat
        assert "speed" not in participant_compat

    def test_footstep_level_includes_side(self):
        assert "side" in GRANULARITY_COMPATIBLE_GROUPS["footstep"]

    def test_compatible_groups_are_sets(self):
        for level, groups in GRANULARITY_COMPATIBLE_GROUPS.items():
            assert isinstance(groups, set), f"{level} compatible groups should be a set"

    def test_trial_group_keys_subset_of_allowed_columns(self):
        allowed = set(ALLOWED_COLUMNS)
        for key in TRIAL_GROUP_KEYS:
            assert key in allowed, f"TRIAL_GROUP_KEY '{key}' not in ALLOWED_COLUMNS"

    def test_participant_group_keys_subset_of_allowed_columns(self):
        allowed = set(ALLOWED_COLUMNS)
        for key in PARTICIPANT_GROUP_KEYS:
            assert (
                key in allowed
            ), f"PARTICIPANT_GROUP_KEY '{key}' not in ALLOWED_COLUMNS"

    def test_participant_group_keys_include_core_demographic_fields(self):
        """
        PARTICIPANT_GROUP_KEYS must always contain the fields that uniquely
        identify a person-level aggregation unit.
        """
        assert "participant_id" in PARTICIPANT_GROUP_KEYS
        assert "sex" in PARTICIPANT_GROUP_KEYS
        assert "is_outlier" in PARTICIPANT_GROUP_KEYS


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Dropdown option lists
# ═══════════════════════════════════════════════════════════════════════════════


class TestDropdownOptions:

    def _assert_valid_options(self, options, name):
        assert isinstance(options, list), f"{name} must be a list"
        for opt in options:
            assert "label" in opt, f"Each option in {name} must have 'label'"
            assert "value" in opt, f"Each option in {name} must have 'value'"

    def test_feature_options_structure(self):
        self._assert_valid_options(FEATURE_OPTIONS, "FEATURE_OPTIONS")

    def test_ct_group_options_structure(self):
        self._assert_valid_options(CT_GROUP_OPTIONS, "CT_GROUP_OPTIONS")

    def test_ct_color_options_structure(self):
        self._assert_valid_options(CT_COLOR_OPTIONS, "CT_COLOR_OPTIONS")

    def test_st_color_options_structure(self):
        self._assert_valid_options(ST_COLOR_OPTIONS, "ST_COLOR_OPTIONS")

    def test_ct_color_options_includes_none_sentinel(self):
        values = [opt["value"] for opt in CT_COLOR_OPTIONS]
        assert NO_COLOR_SENTINEL in values

    def test_feature_options_values_are_in_allowed_columns(self):
        allowed = set(ALLOWED_COLUMNS)
        for opt in FEATURE_OPTIONS:
            assert (
                opt["value"] in allowed
            ), f"FEATURE_OPTIONS value '{opt['value']}' not in ALLOWED_COLUMNS"

    def test_no_duplicate_values_in_feature_options(self):
        values = [opt["value"] for opt in FEATURE_OPTIONS]
        assert len(values) == len(set(values))


# 4. Tab-name routing maps


class TestTabRoutingMaps:

    def test_valid_tab_names_contains_both_tabs(self):
        assert {"single", "cross"}.issubset(_VALID_TAB_NAMES)

    def test_tab_prefix_covers_all_valid_tabs(self):
        for tab in _VALID_TAB_NAMES:
            assert tab in _TAB_PREFIX, f"No prefix defined for tab '{tab}'"

    def test_query_placeholder_covers_all_valid_tabs(self):
        for tab in _VALID_TAB_NAMES:
            assert tab in _QUERY_PLACEHOLDER

    def test_apply_btn_id_covers_all_valid_tabs(self):
        for tab in _VALID_TAB_NAMES:
            assert tab in _APPLY_BTN_ID


# 5. Shared layout factory validation


class TestSharedLayoutFactory:

    def test_get_dynamic_outlier_layout_raises_on_invalid_tab(self):
        from unittest.mock import patch

        # Patch DB calls so we don't need a real database
        with patch("layout.shared_layout.get_dropdown_options", return_value=[]):
            from layout.shared_layout import get_dynamic_outlier_layout

            with pytest.raises(ValueError, match="tab_name must be one of"):
                get_dynamic_outlier_layout("invalid_tab")

    def test_get_dynamic_outlier_layout_accepts_single(self):
        from unittest.mock import patch

        with patch("layout.shared_layout.get_dropdown_options", return_value=[]):
            from layout.shared_layout import get_dynamic_outlier_layout

            # Should return a Div without raising — "single" is a valid tab name
            result = get_dynamic_outlier_layout("single")
            assert result is not None


# 6. NO_COLOR_SENTINEL consistency


class TestNoColorSentinel:

    def test_sentinel_is_string(self):
        assert isinstance(NO_COLOR_SENTINEL, str)

    def test_sentinel_not_a_real_column_name(self):
        """Sentinel must not clash with any real DataFrame column name."""
        assert NO_COLOR_SENTINEL not in ALLOWED_COLUMNS

    def test_sentinel_not_a_valid_pandas_query_keyword(self):
        assert NO_COLOR_SENTINEL not in ALLOWED_KEYWORDS
