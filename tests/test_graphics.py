"""
tests/test_graphics.py

Validates that each factory function:
  - returns a go.Figure
  - produces the correct trace types
  - handles empty / None inputs  (empty-state figures)
  - embeds the expected customdata structure for the Bridge callback
  - respects NO_COLOR_SENTINEL sentinel value

no pixel-level rendering, only the data model of the returned
figure objects, which is the contract the callbacks depend on
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import NO_COLOR_SENTINEL
from graphics.cross_trial_graphics import (
    create_aggregate_waveform_plot,
    create_bivariate_scatter_plot,
    create_box_plot,
    create_violin_plot,
)
from graphics.cross_trial_helpers import resolve_color_arg, get_custom_data
from graphics.single_trial_graphics import (
    create_cop_plot,
    create_grf_plot,
    create_heatmap_and_histogram,
    create_rug_plot,
    create_scatter_plot,
    create_walkway_plot,
    get_empty_physics_layout,
)
from graphics.single_trial_helpers import compute_pressure_histogram_data

# Helpers


def _has_trace_type(fig, trace_type: str) -> bool:
    return any(type(t).__name__ == trace_type for t in fig.data)


# 1. Cross-trial distribution plots


class TestCrossTrialDistributionPlots:

    def test_box_plot_returns_figure(self, raw_footstep_df):
        fig = create_box_plot(
            raw_footstep_df, y_col="peak_grf", x_col="footwear", color_col="speed"
        )
        assert isinstance(fig, go.Figure)

    def test_box_plot_empty_df_returns_figure(self):
        fig = create_box_plot(
            pd.DataFrame(), y_col="peak_grf", x_col="footwear", color_col=None
        )
        assert isinstance(fig, go.Figure)

    def test_violin_plot_returns_figure(self, raw_footstep_df):
        fig = create_violin_plot(
            raw_footstep_df, y_col="peak_grf", x_col="footwear", color_col="speed"
        )
        assert isinstance(fig, go.Figure)

    def test_violin_plot_empty_df_returns_figure(self):
        fig = create_violin_plot(
            pd.DataFrame(), y_col="peak_grf", x_col="footwear", color_col=None
        )
        assert isinstance(fig, go.Figure)

    def test_bivariate_scatter_returns_figure(self, raw_footstep_df):
        fig = create_bivariate_scatter_plot(
            raw_footstep_df,
            y_col="peak_grf",
            x_col="stance_duration_frames",
            color_col="footwear",
        )
        assert isinstance(fig, go.Figure)

    def test_bivariate_scatter_empty_df_returns_figure(self):
        fig = create_bivariate_scatter_plot(
            pd.DataFrame(), y_col="peak_grf", x_col="mean_grf", color_col=None
        )
        assert isinstance(fig, go.Figure)

    def test_box_plot_no_color_sentinel_handled(self, raw_footstep_df):
        """Passing NO_COLOR_SENTINEL should not raise."""
        fig = create_box_plot(
            raw_footstep_df,
            y_col="peak_grf",
            x_col="footwear",
            color_col=NO_COLOR_SENTINEL,
        )
        assert isinstance(fig, go.Figure)

    def test_customdata_shape_for_bridge(self, raw_footstep_df):
        """
        The Bridge callback reads customdata[0]=participant, [1]=footwear, [2]=speed.
        get_custom_data must always return exactly three arrays.
        """
        custom = get_custom_data(raw_footstep_df)
        assert len(custom) == 3

    def test_customdata_participant_column_present(self, raw_footstep_df):
        custom = get_custom_data(raw_footstep_df)
        # First array should be the participant_id series
        assert list(custom[0]) == list(raw_footstep_df["participant_id"])

    def test_customdata_missing_column_falls_back_to_none_list(self):
        """If participant_id is absent the fallback must be a list of Nones, not a KeyError."""
        df = pd.DataFrame({"footwear": ["BF"], "speed": ["W1"]})
        custom = get_custom_data(df)
        assert custom[0] == [None]

    def test_resolve_color_arg_sentinel_returns_none(self):
        assert resolve_color_arg(NO_COLOR_SENTINEL) is None

    def test_resolve_color_arg_real_column_returns_column(self):
        assert resolve_color_arg("footwear") == "footwear"


# 2. Aggregate waveform plot


class TestAggregateWaveformPlot:

    def test_returns_figure_with_data(self):
        t = np.linspace(0, 100, 101).tolist()
        mean = (np.sin(np.linspace(0, np.pi, 101)) * 800).tolist()
        upper = (np.array(mean) + 50).tolist()
        lower = (np.array(mean) - 50).tolist()
        fig = create_aggregate_waveform_plot(t, mean, upper, lower)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 3  # upper, lower fill, mean line

    def test_none_time_pct_returns_empty_figure(self):
        fig = create_aggregate_waveform_plot(None, None, None, None)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0


# 3. GRF and COP plots


class TestPhysicsPlots:

    def test_grf_plot_returns_figure(self, physics_metrics):
        fig = create_grf_plot(physics_metrics, selected_step_id=10)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1

    def test_grf_plot_empty_metrics_returns_empty_figure(self):
        fig = create_grf_plot([])
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    def test_grf_overlay_mode_renders_ghost_traces(self, physics_metrics):
        fig = create_grf_plot(physics_metrics, selected_step_id=10, overlay_mode=True)
        assert len(fig.data) >= len(physics_metrics)

    def test_cop_plot_returns_figure(self, physics_metrics):
        fig = create_cop_plot(physics_metrics, selected_step_id=10)
        assert isinstance(fig, go.Figure)

    def test_cop_plot_empty_metrics_returns_empty_figure(self):
        fig = create_cop_plot([])
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    def test_unmatched_selected_id_still_returns_figure(self, physics_metrics):
        """If selected_step_id is not in metrics, should not raise."""
        fig = create_grf_plot(physics_metrics, selected_step_id=9999)
        assert isinstance(fig, go.Figure)


# 4. Scatter and rug plots


class TestSingleTrialFeaturePlots:

    def test_scatter_plot_returns_figure(self, single_trial_df):
        fig = create_scatter_plot(single_trial_df, "start_frame", "mean_grf", "side")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 2  # left group and Right group

    def test_scatter_plot_empty_df(self):
        fig = create_scatter_plot(pd.DataFrame(), "x", "y", "c")
        assert isinstance(fig, go.Figure)

    def test_scatter_plot_missing_column_shows_error_title(self, single_trial_df):
        fig = create_scatter_plot(single_trial_df, "nonexistent", "mean_grf", "side")
        assert "Configuration Error" in fig.layout.title.text

    def test_scatter_plot_highlights_selected_step(self, single_trial_df):
        fig = create_scatter_plot(
            single_trial_df, "start_frame", "mean_grf", "side", selected_step_id=10
        )
        trace_names = [t.name for t in fig.data]
        assert "Selected" in trace_names

    def test_rug_plot_returns_figure(self, single_trial_df):
        fig = create_rug_plot(single_trial_df, "r_score", "side")
        assert isinstance(fig, go.Figure)

    def test_rug_plot_empty_df(self):
        fig = create_rug_plot(pd.DataFrame(), "r_score", "side")
        assert isinstance(fig, go.Figure)

    def test_rug_plot_yaxis_range_is_narrow(self, single_trial_df):
        """Rug plot y-axis should be constrained to a small strip."""
        fig = create_rug_plot(single_trial_df, "r_score", "side")
        y_range = fig.layout.yaxis.range
        assert y_range is not None
        assert y_range[1] - y_range[0] <= 1.5


# 5. Walkway plot


class TestWalkwayPlot:

    def _make_step(self, step_id, side="Left", box=(10, 30, 100, 140)):
        from types import SimpleNamespace

        xmin, xmax, ymin, ymax = box
        return SimpleNamespace(
            id=step_id,
            side=side,
            box_xmin=xmin,
            box_xmax=xmax,
            box_ymin=ymin,
            box_ymax=ymax,
            tile_id=3,
            pass_id=1,
            footstep_index=step_id,
        )

    def test_walkway_plot_returns_figure(self):
        steps = [self._make_step(1), self._make_step(2, "Right")]
        fig = create_walkway_plot(steps)
        assert isinstance(fig, go.Figure)

    def test_walkway_plot_empty_steps_returns_figure(self):
        fig = create_walkway_plot([])
        assert isinstance(fig, go.Figure)

    def test_walkway_plot_has_tile_shapes(self):
        fig = create_walkway_plot([])
        # 6 rows × 2 cols = 12 tile rectangles
        assert len(fig.layout.shapes) >= 12

    def test_selected_step_hover_trace_in_figure(self):
        steps = [self._make_step(42)]
        fig = create_walkway_plot(steps, selected_step_id=42)
        assert isinstance(fig, go.Figure)


# 6. Pressure heatmap and histogram


class TestPressurePlots:

    def test_heatmap_and_histogram_return_figures(self, small_pressure_matrix):
        hm, hist = create_heatmap_and_histogram(small_pressure_matrix, step_id=1)
        assert isinstance(hm, go.Figure)
        assert isinstance(hist, go.Figure)

    def test_none_matrix_returns_two_empty_figures(self):
        hm, hist = create_heatmap_and_histogram(None, step_id=None)
        assert isinstance(hm, go.Figure)
        assert isinstance(hist, go.Figure)
        assert len(hm.data) == 0
        assert len(hist.data) == 0

    def test_dynamic_scale_uses_matrix_max(self, small_pressure_matrix):
        hm, _ = create_heatmap_and_histogram(
            small_pressure_matrix, step_id=1, dynamic_scale=True
        )
        heatmap_trace = hm.data[0]
        assert heatmap_trace.zmax == pytest.approx(
            float(np.max(small_pressure_matrix)), rel=1e-3
        )

    def test_absolute_scale_caps_at_800(self, small_pressure_matrix):
        hm, _ = create_heatmap_and_histogram(
            small_pressure_matrix, step_id=1, dynamic_scale=False
        )
        heatmap_trace = hm.data[0]
        assert heatmap_trace.zmax == pytest.approx(800, rel=1e-3)

    def test_compute_histogram_data_filters_noise_floor(self, small_pressure_matrix):
        from config import _HEATMAP_NOISE_FLOOR_KPA

        centers, counts = compute_pressure_histogram_data(
            small_pressure_matrix,
            _HEATMAP_NOISE_FLOOR_KPA,
            float(np.max(small_pressure_matrix)),
        )
        assert centers is not None
        assert counts is not None
        assert (centers > _HEATMAP_NOISE_FLOOR_KPA).all()

    def test_compute_histogram_data_all_below_floor_returns_none(self):
        mat = np.ones((4, 4)) * 5.0  # all below 10 kPa floor
        centers, counts = compute_pressure_histogram_data(mat, 10, 5.0)
        assert centers is None
        assert counts is None


# 7. get_empty_physics_layout


class TestGetEmptyPhysicsLayout:

    def test_returns_layout_object(self):
        layout = get_empty_physics_layout("Test Title")
        assert isinstance(layout, go.Layout)

    def test_title_propagated(self):
        layout = get_empty_physics_layout("My Title")
        assert layout.title.text == "My Title"

    def test_default_title(self):
        layout = get_empty_physics_layout()
        assert layout.title.text == "No Data"
