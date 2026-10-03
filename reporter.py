"""
Reporter module: Generates terminal tables, JSON reports, CSV time-series exports,
and publication-quality kinematic angle graphs with expected value and variance bands.
"""

import csv
import json
import os
from typing import Dict, Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from kinematics import JointStats, KinematicTracker


class KinematicReporter:
    """
    Produces formatted statistical summaries and visual graphs of joint angle kinematics.
    """

    def __init__(self, kinematic_tracker: KinematicTracker, video_metadata: dict):
        self.tracker = kinematic_tracker
        self.metadata = video_metadata
        self.stats: Dict[str, JointStats] = self.tracker.compute_all_stats()

    def print_terminal_summary(self):
        """Prints a clean, formatted ASCII table of kinematic statistics to the console."""
        print("\n" + "=" * 94)
        print("                           FORMCHECK KINEMATICS ANALYSIS REPORT                           ")
        print("=" * 94)
        print(f" Video Source: {self.metadata.get('video_path', 'Unknown')}")
        print(
            f" Duration: {self.metadata.get('duration_s', 0):.2f}s | "
            f" Total Frames: {self.metadata.get('total_frames', 0)} | "
            f" FPS: {self.metadata.get('fps', 0):.1f} | "
            f" Resolution: {self.metadata.get('resolution', 'Unknown')}"
        )
        print("-" * 94)
        print(
            f"{'Joint Name':<32} | {'Count':<5} | {'E[Angle] (Mean)':<15} | {'Variance (σ²)':<14} | {'Std Dev (σ)':<11} | {'ROM (Min-Max)':<16}"
        )
        print("-" * 94)

        if not self.stats:
            print(" No valid pose landmarks detected.")
        else:
            # Highlight Lower body (Femur, Shin, Hip) first
            priority_order = [
                "left_knee",
                "right_knee",
                "left_hip",
                "right_hip",
                "left_ankle",
                "right_ankle",
                "left_pelvis_femur",
                "right_pelvis_femur",
                "trunk_inclination",
                "left_elbow",
                "right_elbow",
                "left_shoulder",
                "right_shoulder",
            ]

            keys = [k for k in priority_order if k in self.stats]
            for k in self.stats:
                if k not in keys:
                    keys.append(k)

            for key in keys:
                s = self.stats[key]
                mean_str = f"{s.expected_value:6.2f}°"
                var_str = f"{s.variance:7.2f}°²"
                std_str = f"{s.std_dev:5.2f}°"
                rom_str = f"{s.range_of_motion:4.1f}° ({s.min_angle:.0f}°-{s.max_angle:.0f}°)"

                print(
                    f" {s.name:<31} | {s.count:<5} | {mean_str:<15} | {var_str:<14} | {std_str:<11} | {rom_str:<16}"
                )

        print("=" * 94)
        print(" Note: Expected Value (E[X]) represents average joint angle during movement.")
        print("       Variance (Var[X]) indicates the dispersion/spread of joint excursions.")
        print("=" * 94 + "\n")

    def save_json(self, output_path: str):
        """Exports complete statistics and frame-by-frame time-series to JSON."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        summary_data = {}
        for key, s in self.stats.items():
            summary_data[key] = {
                "name": s.name,
                "sample_count": s.count,
                "expected_value_deg": round(s.expected_value, 3),
                "variance_deg2": round(s.variance, 3),
                "std_dev_deg": round(s.std_dev, 3),
                "min_angle_deg": round(s.min_angle, 3),
                "max_angle_deg": round(s.max_angle, 3),
                "range_of_motion_deg": round(s.range_of_motion, 3),
                "median_deg": round(s.median, 3),
                "q25_deg": round(s.q25, 3),
                "q75_deg": round(s.q75, 3),
            }

        # Frame-by-frame series
        time_series = {}
        for key, series in self.tracker.history.items():
            time_series[key] = [
                {
                    "frame": f_idx,
                    "timestamp_s": round(t_s, 4),
                    "angle_deg": round(ang, 2),
                }
                for f_idx, t_s, ang in series
            ]

        data = {
            "metadata": self.metadata,
            "summary_statistics": summary_data,
            "time_series": time_series,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[✓] Saved JSON report to: {output_path}")

    def save_csv(self, output_path: str):
        """Exports joint angles over time in tabular CSV format."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Collect unique frames
        all_frames = set()
        frame_timestamps = {}
        for series in self.tracker.history.values():
            for f_idx, t_s, _ in series:
                all_frames.add(f_idx)
                frame_timestamps[f_idx] = t_s

        sorted_frames = sorted(list(all_frames))
        joint_keys = list(self.tracker.history.keys())

        # Map: frame -> key -> angle
        frame_joint_map = {f: {} for f in sorted_frames}
        for key, series in self.tracker.history.items():
            for f_idx, _, ang in series:
                frame_joint_map[f_idx][key] = round(ang, 2)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            header = ["frame_index", "timestamp_s"] + joint_keys
            writer.writerow(header)

            for f_idx in sorted_frames:
                t_s = frame_timestamps.get(f_idx, 0.0)
                row = [f_idx, f"{t_s:.4f}"]
                for k in joint_keys:
                    row.append(frame_joint_map[f_idx].get(k, ""))
                writer.writerow(row)

        print(f"[✓] Saved CSV time series to: {output_path}")

    def save_kinematics_plot(self, output_path: str):
        """
        Generates and saves a publication-quality Matplotlib kinematic plot
        showing angle trajectories, expected value lines, and variance (±1σ) bands.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        fig, axs = plt.subplots(3, 1, figsize=(12, 11), sharex=True)
        fig.suptitle(
            "FormCheck Kinematic Analysis: Joint Angles, Expected Values & Variance",
            fontsize=15,
            fontweight="bold",
            y=0.98,
        )

        # Color schemes
        c_left = "#1f77b4"
        c_right = "#ff7f0e"
        c_accent = "#2ca02c"

        # --- Subplot 1: Knee Angles (Femur & Shin) ---
        ax1 = axs[0]
        self._plot_joint_series(
            ax1, "left_knee", "Left Knee (Femur-Shin)", c_left, linestyle="-"
        )
        self._plot_joint_series(
            ax1, "right_knee", "Right Knee (Femur-Shin)", c_right, linestyle="--"
        )
        ax1.set_ylabel("Knee Angle (°)", fontsize=11, fontweight="semibold")
        ax1.set_title("Knee Kinematics (Femur & Shin)", fontsize=12, fontweight="bold")
        ax1.grid(True, linestyle=":", alpha=0.6)
        ax1.legend(loc="upper right", framealpha=0.9)

        # --- Subplot 2: Hip Angles (Torso & Femur) ---
        ax2 = axs[1]
        self._plot_joint_series(
            ax2, "left_hip", "Left Hip (Torso-Femur)", c_left, linestyle="-"
        )
        self._plot_joint_series(
            ax2, "right_hip", "Right Hip (Torso-Femur)", c_right, linestyle="--"
        )
        ax2.set_ylabel("Hip Angle (°)", fontsize=11, fontweight="semibold")
        ax2.set_title("Hip Kinematics (Torso & Femur)", fontsize=12, fontweight="bold")
        ax2.grid(True, linestyle=":", alpha=0.6)
        ax2.legend(loc="upper right", framealpha=0.9)

        # --- Subplot 3: Ankles & Torso Lean ---
        ax3 = axs[2]
        self._plot_joint_series(
            ax3, "left_ankle", "Left Ankle (Shin-Foot)", c_left, linestyle="-"
        )
        self._plot_joint_series(
            ax3, "right_ankle", "Right Ankle (Shin-Foot)", c_right, linestyle="--"
        )
        self._plot_joint_series(
            ax3,
            "trunk_inclination",
            "Trunk Lean (Torso vs Vertical)",
            c_accent,
            linestyle="-.",
        )
        ax3.set_xlabel("Time (seconds)", fontsize=11, fontweight="semibold")
        ax3.set_ylabel("Angle (°)", fontsize=11, fontweight="semibold")
        ax3.set_title("Ankle & Trunk Inclination", fontsize=12, fontweight="bold")
        ax3.grid(True, linestyle=":", alpha=0.6)
        ax3.legend(loc="upper right", framealpha=0.9)

        plt.tight_layout(rect=[0, 0.02, 1, 0.96])
        plt.savefig(output_path, dpi=200)
        plt.close(fig)
        print(f"[✓] Saved Kinematic Plot to: {output_path}")

    def _plot_joint_series(
        self, ax, joint_key: str, label_prefix: str, color: str, linestyle: str = "-"
    ):
        """Helper to plot time-series with Expected Value line and Variance band."""
        series = self.tracker.history.get(joint_key, [])
        if not series:
            return

        times = np.array([t for _, t, _ in series])
        angles = np.array([a for _, _, a in series])

        if len(angles) == 0:
            return

        mean = np.mean(angles)
        variance = np.var(angles)
        std = np.std(angles)

        # Plot angle trajectory
        ax.plot(
            times,
            angles,
            color=color,
            linestyle=linestyle,
            linewidth=1.8,
            label=f"{label_prefix} [E={mean:.1f}°, Var={variance:.1f}°²]",
        )

        # Expected value dashed line
        ax.axhline(
            mean,
            color=color,
            linestyle=":",
            alpha=0.6,
            linewidth=1.2,
        )

        # Variance band: mean ± 1 std dev (sigma = sqrt(var))
        ax.fill_between(
            times,
            mean - std,
            mean + std,
            color=color,
            alpha=0.12,
        )
