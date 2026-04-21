"""
tests/test_physics.py

Covers compute_tensor_physics which is the pure function called during
data ingestion.  No database I/O is required; everything runs on
synthetically constructed pressure tensors

tensor shape: (Frames, Height, Width)
"""

import numpy as np
import pytest
import sys
import os
from physics import compute_tensor_physics, safe_filtfilt
from scipy.signal import butter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Fixtures


@pytest.fixture
def simple_tensor():
    """
    Deterministic 50-frame, 20×10 pressure tensor.
    Pressure rises linearly over stance, then falls — a crude but predictable
    double-ramp mimicking normal GRF loading.
    """
    frames, h, w = 50, 20, 10
    ramp_up = np.linspace(0, 1, frames // 2)
    ramp_down = np.linspace(1, 0, frames - frames // 2)
    envelope = np.concatenate([ramp_up, ramp_down])

    # Uniform spatial distribution: every sensor gets the same load
    base = np.ones((h, w), dtype=float)
    tensor = np.stack([envelope[i] * base * 500 for i in range(frames)])
    return tensor


@pytest.fixture
def short_tensor():
    """
    3-frame tensor — shorter than the filtfilt padlen, exercises safe_filtfilt.
    """
    return np.ones((3, 10, 5)) * 200.0


@pytest.fixture
def single_frame_tensor():
    """Edge case: only one frame."""
    return np.ones((1, 10, 5)) * 100.0


# 1. compute_tensor_physics — return structure


class TestComputeTensorPhysicsStructure:

    EXPECTED_KEYS = {
        "peak_grf",
        "stance_duration_frames",
        "time_pct_array",
        "grf_array",
        "cop_ml_array",
        "cop_ap_array",
    }

    def test_returns_dict_with_all_keys(self, simple_tensor):
        result = compute_tensor_physics(simple_tensor)
        assert result is not None
        assert self.EXPECTED_KEYS.issubset(result.keys())

    def test_all_arrays_are_python_lists(self, simple_tensor):
        """JSON serialisation requires plain Python lists, not numpy arrays."""
        result = compute_tensor_physics(simple_tensor)
        for key in ("time_pct_array", "grf_array", "cop_ml_array", "cop_ap_array"):
            assert isinstance(result[key], list), f"{key} should be a list"

    def test_peak_grf_is_float(self, simple_tensor):
        result = compute_tensor_physics(simple_tensor)
        assert isinstance(result["peak_grf"], float)

    def test_stance_duration_is_int(self, simple_tensor):
        result = compute_tensor_physics(simple_tensor)
        assert isinstance(result["stance_duration_frames"], int)


# 2. compute_tensor_physics — numerical correctness


class TestComputeTensorPhysicsNumerics:

    def test_stance_duration_equals_frame_count(self, simple_tensor):
        result = compute_tensor_physics(simple_tensor)
        assert result["stance_duration_frames"] == simple_tensor.shape[0]

    def test_time_pct_starts_at_zero_ends_at_100(self, simple_tensor):
        result = compute_tensor_physics(simple_tensor)
        assert result["time_pct_array"][0] == pytest.approx(0.0, abs=1e-6)
        assert result["time_pct_array"][-1] == pytest.approx(100.0, abs=1e-6)

    def test_time_pct_length_matches_grf_length(self, simple_tensor):
        result = compute_tensor_physics(simple_tensor)
        assert len(result["time_pct_array"]) == len(result["grf_array"])

    def test_peak_grf_is_positive(self, simple_tensor):
        result = compute_tensor_physics(simple_tensor)
        assert result["peak_grf"] > 0

    def test_peak_grf_equals_max_of_grf_array(self, simple_tensor):
        result = compute_tensor_physics(simple_tensor)
        assert result["peak_grf"] == pytest.approx(max(result["grf_array"]), rel=1e-4)

    def test_grf_array_all_non_negative(self, simple_tensor):
        """Filtered GRF should never go significantly negative for a clean signal."""
        result = compute_tensor_physics(simple_tensor)
        # Allow tiny floating-point undershoot
        assert min(result["grf_array"]) > -1.0

    def test_cop_arrays_length_matches_grf(self, simple_tensor):
        result = compute_tensor_physics(simple_tensor)
        assert len(result["cop_ml_array"]) == len(result["grf_array"])
        assert len(result["cop_ap_array"]) == len(result["grf_array"])

    def test_cop_ml_mean_near_zero_for_symmetric_tensor(self, simple_tensor):
        """
        Uniform spatial load → COP should be de-meaned to ≈ 0 in ML direction.
        """
        result = compute_tensor_physics(simple_tensor)
        ml = np.array(result["cop_ml_array"])
        assert np.abs(np.mean(ml)) < 0.5  # within 0.5 cm of centre

    def test_higher_pressure_tensor_produces_higher_peak_grf(self):
        """Doubling sensor values should approximately double peak_grf."""
        base = np.ones((30, 10, 10)) * 200.0
        doubled = base * 2
        r1 = compute_tensor_physics(base)
        r2 = compute_tensor_physics(doubled)
        assert r2["peak_grf"] > r1["peak_grf"]

    def test_unit_conversion_grf_is_in_newtons_range(self, simple_tensor):
        """
        With SENSOR_AREA_M2=2.5e-5 and scale 500 Pa pressure on 200 sensors,
        GRF should be in a physiologically plausible range (not raw sensor counts).
        """
        result = compute_tensor_physics(simple_tensor)
        # We can't assert exact Newtons without full body-weight context, but
        # the value should be well above 0 and not astronomically large.
        assert 0 < result["peak_grf"] < 1e7


# 3. compute_tensor_physics — edge cases


class TestComputeTensorPhysicsEdgeCases:

    def test_short_tensor_does_not_raise(self, short_tensor):
        """safe_filtfilt must bypass filtering for very short signals."""
        result = compute_tensor_physics(short_tensor)
        assert result is not None

    def test_single_frame_tensor_does_not_raise(self, single_frame_tensor):
        result = compute_tensor_physics(single_frame_tensor)
        assert result is not None

    def test_zero_tensor_returns_none_or_zero_peak(self):
        """All-zero pressure → GRF = 0; function should either return None or peak=0."""
        tensor = np.zeros((20, 10, 5))
        result = compute_tensor_physics(tensor)
        if result is not None:
            assert result["peak_grf"] == pytest.approx(0.0, abs=1e-6)


# 4. safe_filtfilt


class TestSafeFilterfilt:

    def _butter_coeffs(self):
        order, cutoff, nyquist = 2, 20, 50
        return butter(order, cutoff / nyquist, btype="low", analog=False)

    def test_long_signal_is_filtered(self):
        b, a = self._butter_coeffs()
        signal = np.random.default_rng(0).normal(0, 1, 200)
        filtered = safe_filtfilt(b, a, signal)
        assert len(filtered) == len(signal)
        # Filtered signal should have lower variance (smoothed)
        assert np.std(filtered) < np.std(signal)

    def test_short_signal_returned_unchanged(self):
        """Signal shorter than padlen must be returned as-is without raising."""
        b, a = self._butter_coeffs()
        signal = np.array([1.0, 2.0, 1.5])
        result = safe_filtfilt(b, a, signal)
        np.testing.assert_array_equal(result, signal)

    def test_output_length_equals_input_length(self):
        b, a = self._butter_coeffs()
        signal = np.ones(100)
        result = safe_filtfilt(b, a, signal)
        assert len(result) == len(signal)
