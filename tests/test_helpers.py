"""
tests/test_helpers.py

Covers:
  - validate_query_string   (security-critical allowlist enforcement)
  - apply_advanced_query    (pandas .query execution and error surfacing)
  - filter_dataframe        (compound UI-filter application)
  - apply_data_granularity  (footstep / trial / participant aggregation)
  - apply_dynamic_outliers  (vectorised reclassification)
"""

import numpy as np
import pandas as pd
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from helpers import (
    apply_advanced_query,
    apply_data_granularity,
    apply_dynamic_outliers,
    filter_dataframe,
    validate_query_string,
)

# 1. validate_query_string


class TestValidateQueryString:
    """Security and correctness of the query allowlist validator."""

    def test_empty_string_is_valid(self):
        ok, msg = validate_query_string("")
        assert ok is True
        assert msg == ""

    def test_none_is_valid(self):
        ok, msg = validate_query_string(None)
        assert ok is True

    def test_whitespace_only_is_valid(self):
        ok, msg = validate_query_string("   ")
        assert ok is True

    # approved columns

    def test_single_allowed_column_numeric(self):
        ok, msg = validate_query_string("peak_grf > 800")
        assert ok is True, msg

    def test_compound_allowed_query(self):
        ok, msg = validate_query_string("peak_grf > 800 and is_outlier == 'Normal'")
        assert ok is True, msg

    def test_logical_or_allowed(self):
        ok, msg = validate_query_string("side == 'Left' or side == 'Right'")
        assert ok is True, msg

    def test_not_keyword_allowed(self):
        ok, msg = validate_query_string("not is_outlier == 'Outlier'")
        assert ok is True, msg

    def test_in_keyword_allowed(self):
        ok, msg = validate_query_string("side in ['Left', 'Right']")
        assert ok is True, msg

    # disallowed content

    def test_arbitrary_python_builtins_rejected(self):
        ok, msg = validate_query_string("__import__('os').system('ls')")
        assert ok is False

    def test_unknown_column_rejected(self):
        ok, msg = validate_query_string("secret_column > 5")
        assert ok is False
        assert "secret_column" in msg

    def test_illegal_characters_rejected(self):
        """Semicolons are not in the allowed character set."""
        ok, msg = validate_query_string("peak_grf > 800; drop table footsteps")
        assert ok is False

    def test_backtick_rejected(self):
        ok, msg = validate_query_string("`peak_grf` > 800")
        assert ok is False

    def test_pipe_rejected(self):
        ok, msg = validate_query_string("peak_grf > 800 | peak_grf < 500")
        assert ok is False


# 2. apply_advanced_query


class TestApplyAdvancedQuery:
    """Query execution, result correctness, and error surfacing."""

    def test_numeric_filter_reduces_rows(self, raw_footstep_df):
        result, err = apply_advanced_query(raw_footstep_df, "peak_grf > 810")
        assert err == ""
        assert len(result) < len(raw_footstep_df)
        assert (result["peak_grf"] > 810).all()

    def test_string_equality_filter(self, raw_footstep_df):
        result, err = apply_advanced_query(raw_footstep_df, "side == 'Left'")
        assert err == ""
        assert set(result["side"]) == {"Left"}

    def test_compound_and_filter(self, raw_footstep_df):
        result, err = apply_advanced_query(
            raw_footstep_df, "side == 'Left' and is_outlier == 'Normal'"
        )
        assert err == ""
        assert (result["side"] == "Left").all()
        assert (result["is_outlier"] == "Normal").all()

    def test_empty_string_returns_original(self, raw_footstep_df):
        result, err = apply_advanced_query(raw_footstep_df, "")
        assert err == ""
        assert len(result) == len(raw_footstep_df)

    def test_none_query_returns_original(self, raw_footstep_df):
        result, err = apply_advanced_query(raw_footstep_df, None)
        assert err == ""
        assert len(result) == len(raw_footstep_df)

    def test_empty_dataframe_returns_early(self):
        result, err = apply_advanced_query(pd.DataFrame(), "peak_grf > 800")
        assert result.empty
        assert err == ""

    def test_invalid_column_returns_error_string(self, raw_footstep_df):
        """A query on a non-existent column should surface an error message."""
        _, err = apply_advanced_query(raw_footstep_df, "nonexistent_col > 5")
        assert err != ""

    def test_syntax_error_returns_error_string(self, raw_footstep_df):
        _, err = apply_advanced_query(raw_footstep_df, "peak_grf >>>>> 800")
        assert err != ""


# 3. filter_dataframe


class TestFilterDataframe:
    """Standard UI-filter combinations used by the single-trial tab."""

    def test_side_filter_left_only(self, single_trial_df):
        result, err = filter_dataframe(single_trial_df, ["Left"], None, None, None)
        assert err == ""
        assert set(result["side"]) == {"Left"}

    def test_outlier_filter_normal_only(self, single_trial_df):
        result, err = filter_dataframe(single_trial_df, None, ["Normal"], None, None)
        assert (result["is_outlier"] == "Normal").all()

    def test_tile_filter(self, single_trial_df):
        result, err = filter_dataframe(single_trial_df, None, None, [3], None)
        assert set(result["tile_id"]) == {3}

    def test_pass_filter(self, single_trial_df):
        result, err = filter_dataframe(single_trial_df, None, None, None, [1])
        assert set(result["pass_id"]) == {1}

    def test_compound_filters_are_ANDed(self, single_trial_df):
        result, err = filter_dataframe(
            single_trial_df, ["Left"], ["Normal"], None, None
        )
        assert (result["side"] == "Left").all()
        assert (result["is_outlier"] == "Normal").all()

    def test_none_filters_return_all_rows(self, single_trial_df):
        result, err = filter_dataframe(single_trial_df, None, None, None, None)
        assert len(result) == len(single_trial_df)
        assert err == ""

    def test_advanced_query_combined_with_ui_filters(self, single_trial_df):
        result, err = filter_dataframe(
            single_trial_df, ["Left"], None, None, None, "peak_grf > 800"
        )
        assert err == ""
        assert (result["side"] == "Left").all()
        assert (result["peak_grf"] > 800).all()

    def test_empty_dataframe_passes_through(self):
        result, err = filter_dataframe(pd.DataFrame(), ["Left"], ["Normal"], None, None)
        assert result.empty
        assert err == ""


# 4. apply_data_granularity


class TestApplyDataGranularity:
    """Aggregation correctness and edge-case handling."""

    def test_footstep_granularity_preserves_all_rows(self, raw_footstep_df):
        result = apply_data_granularity(raw_footstep_df, "footstep")
        assert len(result) == len(raw_footstep_df)

    def test_footstep_granularity_adds_n_footsteps_column(self, raw_footstep_df):
        result = apply_data_granularity(raw_footstep_df, "footstep")
        assert "n_footsteps" in result.columns
        assert (result["n_footsteps"] == 1).all()

    def test_trial_granularity_reduces_row_count(self, raw_footstep_df):
        result = apply_data_granularity(raw_footstep_df, "trial")
        # Fixture: 8 footstep rows → 2 participants × 2 sides = 4 trial groups
        assert len(result) < len(raw_footstep_df)
        assert len(result) == 4

    def test_trial_granularity_n_footsteps_sums_correctly(self, raw_footstep_df):
        result = apply_data_granularity(raw_footstep_df, "trial")
        assert result["n_footsteps"].sum() == len(raw_footstep_df)

    def test_participant_granularity_aggregates_across_sides(self, raw_footstep_df):
        result = apply_data_granularity(raw_footstep_df, "participant")
        assert len(result) < len(raw_footstep_df)

    def test_participant_granularity_n_footsteps_sums_correctly(self, raw_footstep_df):
        result = apply_data_granularity(raw_footstep_df, "participant")
        assert result["n_footsteps"].sum() == len(raw_footstep_df)

    def test_numeric_means_are_within_source_range(self, raw_footstep_df):
        result = apply_data_granularity(raw_footstep_df, "trial")
        src_min = raw_footstep_df["peak_grf"].min()
        src_max = raw_footstep_df["peak_grf"].max()
        assert result["peak_grf"].between(src_min, src_max).all()

    def test_unknown_granularity_returns_original(self, raw_footstep_df):
        result = apply_data_granularity(raw_footstep_df, "decade")
        # should warn and fall back rather than raise
        assert len(result) == len(raw_footstep_df)

    def test_empty_dataframe_returns_empty(self):
        result = apply_data_granularity(pd.DataFrame(), "trial")
        assert result.empty


# 5. apply_dynamic_outliers


class TestApplyDynamicOutliers:
    def test_less_than_operator_marks_low_r_score_as_outlier(self, raw_footstep_df):
        result = apply_dynamic_outliers(raw_footstep_df, "r_score", "<", 0.85)
        low_r = raw_footstep_df["r_score"] < 0.85
        assert (result.loc[low_r, "is_outlier"] == "Outlier").all()
        assert (result.loc[~low_r, "is_outlier"] == "Normal").all()

    def test_greater_than_operator_marks_high_peak_grf_as_outlier(
        self, raw_footstep_df
    ):
        result = apply_dynamic_outliers(raw_footstep_df, "peak_grf", ">", 840)
        high_grf = raw_footstep_df["peak_grf"] > 840
        assert (result.loc[high_grf, "is_outlier"] == "Outlier").all()

    def test_overwrites_existing_is_outlier_values(self, raw_footstep_df):
        """Dynamic reclassification must replace whatever is in is_outlier."""
        df = raw_footstep_df.copy()
        df["is_outlier"] = "Outlier"
        result = apply_dynamic_outliers(df, "r_score", "<", 0.5)
        # r_score threshold of 0.5
        assert (result["is_outlier"] == "Normal").all()

    def test_missing_metric_column_returns_unchanged_df(self, raw_footstep_df):
        original = raw_footstep_df["is_outlier"].copy()
        result = apply_dynamic_outliers(raw_footstep_df, "nonexistent_metric", "<", 0.5)
        pd.testing.assert_series_equal(result["is_outlier"], original)

    def test_none_threshold_returns_unchanged_df(self, raw_footstep_df):
        original = raw_footstep_df["is_outlier"].copy()
        result = apply_dynamic_outliers(raw_footstep_df, "r_score", "<", None)
        pd.testing.assert_series_equal(result["is_outlier"], original)

    def test_invalid_operator_returns_unchanged_df(self, raw_footstep_df):
        original = raw_footstep_df["is_outlier"].copy()
        result = apply_dynamic_outliers(raw_footstep_df, "r_score", "!=", 0.85)
        pd.testing.assert_series_equal(result["is_outlier"], original)

    def test_empty_metric_returns_unchanged_df(self, raw_footstep_df):
        original = raw_footstep_df["is_outlier"].copy()
        result = apply_dynamic_outliers(raw_footstep_df, "", "<", 0.85)
        pd.testing.assert_series_equal(result["is_outlier"], original)

    def test_empty_dataframe_returns_empty(self):
        result = apply_dynamic_outliers(pd.DataFrame(), "r_score", "<", 0.85)
        assert result.empty
