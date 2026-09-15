from __future__ import annotations

from app.services.analytics.evidence_calibration import (
    EvidenceCalibrationAnalyzer,
    EvidenceCalibrationReport,
)


class TestEvidenceCalibrationAnalyzer:
    def test_no_corrections(self):
        analyzer = EvidenceCalibrationAnalyzer(min_correction_events=5)
        report = analyzer.evaluate([], [])
        assert report.total_evidence_paired == 0
        assert "no_correction_events_found" in report.blockers
        assert report.recommendation == "collect_belief_correction_events_first"
        assert not report.global_recalibration_recommended

    def test_well_calibrated_extractor(self):
        analyzer = EvidenceCalibrationAnalyzer(
            min_correction_events=5,
            min_paired_evidence=10,
        )
        events = []
        for i in range(50):
            conf = 0.80
            correct = i < 40
            events.append({
                "source_type": "conversational_implicit",
                "confidence": conf,
                "direction_matched": correct,
                "target": "emotional_block",
            })
        report = analyzer.evaluate([], events)
        assert report.total_evidence_paired == 50
        assert not report.global_recalibration_recommended
        assert len(report.source_type_results) == 1
        result = report.source_type_results[0]
        assert 0.75 <= result.overall_accuracy <= 0.85

    def test_overconfident_extractor(self):
        analyzer = EvidenceCalibrationAnalyzer(
            min_correction_events=5,
            min_paired_evidence=10,
            recalibration_overconfidence_threshold=0.05,
        )
        events = []
        for i in range(50):
            conf = 0.85
            correct = i < 20
            events.append({
                "source_type": "conversational_implicit",
                "confidence": conf,
                "direction_matched": correct,
                "target": "cognitive_load",
            })
        report = analyzer.evaluate([], events)
        assert report.total_evidence_paired == 50
        assert report.global_recalibration_recommended
        assert report.global_recalibration_multiplier < 1.0
        result = report.source_type_results[0]
        assert result.overall_accuracy < 0.5

    def test_underconfident_extractor(self):
        analyzer = EvidenceCalibrationAnalyzer(
            min_correction_events=5,
            min_paired_evidence=10,
            recalibration_overconfidence_threshold=0.05,
        )
        events = []
        for i in range(50):
            conf = 0.65
            correct = i < 40
            events.append({
                "source_type": "conversational_implicit",
                "confidence": conf,
                "direction_matched": correct,
                "target": "task_aversion",
            })
        report = analyzer.evaluate([], events)
        assert report.total_evidence_paired == 50
        assert not report.global_recalibration_recommended
        result = report.source_type_results[0]
        assert result.overall_accuracy > 0.7

    def test_multiple_source_types(self):
        analyzer = EvidenceCalibrationAnalyzer(
            min_correction_events=3,
            min_paired_evidence=8,
        )
        events = []
        for i in range(30):
            events.append({
                "source_type": "conversational_implicit",
                "confidence": 0.80,
                "direction_matched": i < 24,
                "target": "emotional_block",
            })
        for i in range(20):
            events.append({
                "source_type": "heuristic_fallback",
                "confidence": 0.70,
                "direction_matched": i < 14,
                "target": "cognitive_load",
            })
        report = analyzer.evaluate([], events)
        assert report.total_evidence_paired == 50
        assert len(report.source_type_results) == 2

    def test_insufficient_paired_evidence(self):
        analyzer = EvidenceCalibrationAnalyzer(
            min_correction_events=3,
            min_paired_evidence=50,
        )
        events = []
        for i in range(20):
            events.append({
                "source_type": "conversational_implicit",
                "confidence": 0.75,
                "direction_matched": i < 15,
                "target": "task_aversion",
            })
        report = analyzer.evaluate([], events)
        assert report.total_evidence_paired == 20
        assert "insufficient_paired_evidence_for_calibration" in report.recommendation

    def test_confidence_bin_distribution(self):
        analyzer = EvidenceCalibrationAnalyzer(
            min_correction_events=5,
            min_paired_evidence=10,
        )
        events = []
        for i in range(10):
            events.append({"source_type": "c", "confidence": 0.55, "direction_matched": i < 7, "target": "a"})
        for i in range(10):
            events.append({"source_type": "c", "confidence": 0.65, "direction_matched": i < 8, "target": "a"})
        for i in range(10):
            events.append({"source_type": "c", "confidence": 0.75, "direction_matched": i < 6, "target": "a"})
        for i in range(10):
            events.append({"source_type": "c", "confidence": 0.85, "direction_matched": i < 5, "target": "a"})
        for i in range(10):
            events.append({"source_type": "c", "confidence": 0.95, "direction_matched": i < 4, "target": "a"})
        report = analyzer.evaluate([], events)
        result = report.source_type_results[0]
        assert len(result.confidence_bins) == 5

    def test_report_to_dict(self):
        report = EvidenceCalibrationReport(
            total_traces_analyzed=100,
            total_correction_events=30,
            total_evidence_paired=50,
            source_type_results=[],
            global_recalibration_recommended=False,
            global_recalibration_multiplier=1.0,
            recommendation="well_calibrated",
        )
        d = report.to_dict()
        assert d["schema_version"] == "evidence_calibration.v1"
        assert d["total_evidence_paired"] == 50
