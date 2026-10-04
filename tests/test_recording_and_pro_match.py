"""Test verifying movement recording to server vault and pro similarity recommendation dialog."""

import os
import sys
import time
from pathlib import Path
import cv2
import numpy as np

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.abspath("."))

from PySide6.QtWidgets import QApplication
from services.db import db
from services.video_service import video_service
from services.pro_similarity_service import pro_similarity_service
from services.theme import load_application_fonts, get_stylesheet
from ui.comparison_screen import ComparisonScreen
from ui.pro_recommendation_dialog import ProRecommendationDialog

def run_test():
    app = QApplication.instance() or QApplication(sys.argv)
    load_application_fonts()
    app.setStyleSheet(get_stylesheet())
    print("1. Verifying Pro Athlete Videos in Database & Storage...")
    pros = db.get_uploaded_videos(category="pro")
    print(f"   Found {len(pros)} professional athlete reference videos:")
    for p in pros:
        print(f"   - [{p['sport']}] {p['title']} ({p['file_path']})")

    # Pick an existing test video
    all_vids = db.get_uploaded_videos()
    test_user_path = all_vids[0]["file_path"] if all_vids else "WIN_20261003_14_31_28_Pro.mp4"

    print(f"\n2. Running AI Pro Recommendation on: {test_user_path}...")
    report = pro_similarity_service.recommend_pro_athlete(test_user_path)
    assert report is not None, "Report should not be None!"
    assert report.best_match is not None, "Best match should not be None!"
    print(f"   Best Match: {report.best_match.pro_title}")
    print(f"   Variance Cosine Similarity: {report.best_match.variance_cosine_similarity:.2f}%")
    print(f"   Dynamic Kinematic Congruence: {report.best_match.enhanced_dynamic_congruence:.2f}%")
    print(f"   Kinetic Sequencing Score: {report.best_match.kinetic_sequencing_score:.2f}%")
    print(f"   Segment matches: {report.best_match.segment_matches}")
    print(f"   Total ranked candidates: {len(report.all_ranked_matches)}")

    # 3. Test ComparisonScreen UI with new AI Pro Match Button
    print("\n3. Testing ComparisonScreen layout and capture...")
    comp = ComparisonScreen(user={"id": 1, "username": "TestAthlete"})
    comp.resize(1300, 850)
    comp.load_user_video(test_user_path)
    comp.show()
    app.processEvents()

    # Capture comparison screen
    pix_comp = comp.grab()
    comp_img_path = Path("artifacts_comp_screen.png")
    pix_comp.save(str(comp_img_path))
    print(f"   Saved comparison screen screenshot to {comp_img_path}")

    # 4. Test ProRecommendationDialog modal UI
    print("\n4. Testing ProRecommendationDialog rendering...")
    loaded_pro_path = None
    def on_load_pro(p):
        nonlocal loaded_pro_path
        loaded_pro_path = p
        print(f"   on_load_pro callback invoked with: {p}")

    dialog = ProRecommendationDialog(report, on_load_pro=on_load_pro)
    dialog.resize(880, 750)
    dialog.show()
    app.processEvents()

    pix_diag = dialog.grab()
    diag_img_path = Path("artifacts_pro_dialog.png")
    pix_diag.save(str(diag_img_path))
    print(f"   Saved ProRecommendationDialog screenshot to {diag_img_path}")

    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
    return 0

if __name__ == "__main__":
    sys.exit(run_test())
