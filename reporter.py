"""
Reporter module: Generates terminal tables, JSON reports, CSV time-series exports,
and publication-quality kinematic angle graphs with expected value and variance bands
across every adjacent appendage.
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
    Produces formatted statistical summaries and visual graphs of joint angle kinematics
    and variances between every adjacent appendage.
    """

    def __init__(self, kinematic_tracker: KinematicTracker, video_metadata: dict):
        self.tracker = kinematic_tracker
        self.metadata = video_metadata
        self.stats: Dict[str, JointStats] = self.tracker.compute_all_stats()

    def print_terminal_summary(self):
        """Prints a clean, formatted ASCII table of kinematic statistics to the console."""
        print("\n" + "=" * 106)
        print("               FORMCHECK KINEMATICS REPORT: ALL ADJACENT APPENDAGE VARIANCES              ")
        print("=" * 106)
        print(f" Video Source: {self.metadata.get('video_path', 'Unknown')}")
        print(
            f" Duration: {self.metadata.get('duration_s', 0):.2f}s | "
            f" Total Frames: {self.metadata.get('total_frames', 0)} | "
            f" FPS: {self.metadata.get('fps', 0):.1f} | "
            f" Resolution: {self.metadata.get('resolution', 'Unknown')}"
        )
        print("-" * 106)
        print(
            f"{'Adjacent Appendage Joint':<34} | {'Cat':<10} | {'E[X] (Mean)':<12} | {'Variance (σ²)':<14} | {'Std Dev (σ)':<11} | {'ROM (Min-Max)':<16}"
        )
        print("-" * 106)

        if not self.stats:
            print(" No valid pose landmarks detected.")
        else:
            categories = ["Lower Body", "Upper Body", "Core & Head"]
            for cat in categories:
                cat_items = [s for s in self.stats.values() if s.category == cat]
                if not cat_items:
                    continue

                print(f" --- {cat.upper()} APPENDAGES ---")
                for s in cat_items:
                    mean_str = f"{s.expected_value:5.1f}°"
                    var_str = f"{s.variance:6.1f}°²"
                    std_str = f"{s.std_dev:5.1f}°"
                    rom_str = f"{s.range_of_motion:4.1f}° ({s.min_angle:.0f}°-{s.max_angle:.0f}°)"

                    print(
                        f" {s.name:<33} | {s.category:<10} | {mean_str:<12} | {var_str:<14} | {std_str:<11} | {rom_str:<16}"
                    )

        print("=" * 106)
        print(" Note: Expected Value (E[X]) represents average joint angle across observed frames.")
        print("       Variance (Var[X] = σ²) represents the spread/dispersion between adjacent segments.")
        print("=" * 106 + "\n")

    def save_json(self, output_path: str):
        """Exports complete statistics and frame-by-frame time-series to JSON."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        summary_data = {}
        for key, s in self.stats.items():
            summary_data[key] = {
                "name": s.name,
                "category": s.category,
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

        all_frames = set()
        frame_timestamps = {}
        for series in self.tracker.history.values():
            for f_idx, t_s, _ in series:
                all_frames.add(f_idx)
                frame_timestamps[f_idx] = t_s

        sorted_frames = sorted(list(all_frames))
        joint_keys = list(self.tracker.history.keys())

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
        Generates and saves a 4-panel publication-grade Matplotlib kinematic plot
        showing angle trajectories, expected value lines, and variance (±1σ) bands
        across every adjacent appendage.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        fig, axs = plt.subplots(4, 1, figsize=(13, 14), sharex=True)
        fig.suptitle(
            "FormCheck Kinematic Analysis: All Adjacent Appendage Angles, Expected Values & Variance",
            fontsize=14,
            fontweight="bold",
            y=0.98,
        )

        c_left = "#1f77b4"
        c_right = "#ff7f0e"
        c_alt1 = "#2ca02c"
        c_alt2 = "#d62728"

        # --- Subplot 1: Lower Body - Knees & Hips ---
        ax1 = axs[0]
        p1 = self._plot_joint_series(ax1, "left_knee", "L Knee (Femur-Shin)", c_left, "-")
        p2 = self._plot_joint_series(ax1, "right_knee", "R Knee (Femur-Shin)", c_right, "--")
        p3 = self._plot_joint_series(ax1, "left_hip", "L Hip (Torso-Femur)", c_alt1, "-.")
        p4 = self._plot_joint_series(ax1, "right_hip", "R Hip (Torso-Femur)", c_alt2, ":")
        ax1.set_ylabel("Angle (°)", fontsize=10, fontweight="bold")
        ax1.set_title("Lower Body: Knees & Hips (Femur Kinematics)", fontsize=11, fontweight="bold")
        ax1.grid(True, linestyle=":", alpha=0.6)
        if any([p1, p2, p3, p4]):
            ax1.legend(loc="upper right", framealpha=0.9, fontsize=8)

        # --- Subplot 2: Lower Body - Ankles & Pelvis ---
        ax2 = axs[1]
        p5 = self._plot_joint_series(ax2, "left_ankle", "L Ankle (Shin-Foot)", c_left, "-")
        p6 = self._plot_joint_series(ax2, "right_ankle", "R Ankle (Shin-Foot)", c_right, "--")
        p7 = self._plot_joint_series(ax2, "left_pelvis_femur", "L Pelvis-Femur", c_alt1, "-.")
        p8 = self._plot_joint_series(ax2, "right_pelvis_femur", "R Pelvis-Femur", c_alt2, ":")
        ax2.set_ylabel("Angle (°)", fontsize=10, fontweight="bold")
        ax2.set_title("Lower Body: Ankles (Shin-Foot) & Pelvic Abduction", fontsize=11, fontweight="bold")
        ax2.grid(True, linestyle=":", alpha=0.6)
        if any([p5, p6, p7, p8]):
            ax2.legend(loc="upper right", framealpha=0.9, fontsize=8)

        # --- Subplot 3: Upper Body - Shoulders & Elbows ---
        ax3 = axs[2]
        p9 = self._plot_joint_series(ax3, "left_shoulder", "L Shoulder (Torso-Arm)", c_left, "-")
        p10 = self._plot_joint_series(ax3, "right_shoulder", "R Shoulder (Torso-Arm)", c_right, "--")
        p11 = self._plot_joint_series(ax3, "left_elbow", "L Elbow (Arm-Forearm)", c_alt1, "-.")
        p12 = self._plot_joint_series(ax3, "right_elbow", "R Elbow (Arm-Forearm)", c_alt2, ":")
        ax3.set_ylabel("Angle (°)", fontsize=10, fontweight="bold")
        ax3.set_title("Upper Body: Shoulders & Elbows", fontsize=11, fontweight="bold")
        ax3.grid(True, linestyle=":", alpha=0.6)
        if any([p9, p10, p11, p12]):
            ax3.legend(loc="upper right", framealpha=0.9, fontsize=8)

        # --- Subplot 4: Wrists & Core/Spine ---
        ax4 = axs[3]
        p13 = self._plot_joint_series(ax4, "left_wrist_index", "L Wrist (Forearm-Hand)", c_left, "-")
        p14 = self._plot_joint_series(ax4, "right_wrist_index", "R Wrist (Forearm-Hand)", c_right, "--")
        p15 = self._plot_joint_series(ax4, "trunk_inclination", "Trunk Lean vs Vertical", c_alt1, "-.")
        p16 = self._plot_joint_series(ax4, "neck_head_angle", "Head & Neck to Spine", c_alt2, ":")
        ax4.set_xlabel("Time (seconds)", fontsize=10, fontweight="bold")
        ax4.set_ylabel("Angle (°)", fontsize=10, fontweight="bold")
        ax4.set_title("Distal & Axial: Wrists, Trunk Lean & Head/Neck", fontsize=11, fontweight="bold")
        ax4.grid(True, linestyle=":", alpha=0.6)
        if any([p13, p14, p15, p16]):
            ax4.legend(loc="upper right", framealpha=0.9, fontsize=8)

        plt.tight_layout(rect=[0, 0.02, 1, 0.97])
        plt.savefig(output_path, dpi=200)
        plt.close(fig)
        print(f"[✓] Saved Kinematic Plot to: {output_path}")

    def _plot_joint_series(
        self, ax, joint_key: str, label_prefix: str, color: str, linestyle: str = "-"
    ) -> bool:
        """Helper to plot time-series with Expected Value line and Variance band."""
        series = self.tracker.history.get(joint_key, [])
        if not series:
            return False

        times = np.array([t for _, t, _ in series])
        angles = np.array([a for _, _, a in series])

        if len(angles) == 0:
            return False

        mean = np.mean(angles)
        variance = np.var(angles)
        std = np.std(angles)

        ax.plot(
            times,
            angles,
            color=color,
            linestyle=linestyle,
            linewidth=1.7,
            label=f"{label_prefix} [E={mean:.1f}°, Var={variance:.1f}°²]",
        )

        ax.axhline(
            mean,
            color=color,
            linestyle=":",
            alpha=0.55,
            linewidth=1.1,
        )

        ax.fill_between(
            times,
            mean - std,
            mean + std,
            color=color,
            alpha=0.12,
        )
        return True
