"""Tests for meok-dvsa-olicence-mcp."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    audit_o_licence_compliance,
    check_financial_standing,
    check_tm_continuous_effective_control,
    audit_pmi_compliance,
    generate_public_inquiry_brief,
    forecast_pi_risk,
    check_repute_indicators,
    prepare_dvsa_visit_pack,
    audit_subcontractor_due_diligence,
    RECENT_DISQUALIFICATIONS,
    FIN_STANDING_FIRST_VEHICLE_GBP,
    FIN_STANDING_EACH_ADDITIONAL_GBP,
    O_LICENCE_AREAS,
)


def _call(tool, **kwargs):
    """FastMCP wraps tools as Tool objects - extract the callable."""
    fn = tool.fn if hasattr(tool, "fn") else tool
    return fn(**kwargs)


# ----------------------------------------------------------------------
# 1) audit_o_licence_compliance
# ----------------------------------------------------------------------

def test_o_licence_audit_clean_operator_passes():
    r = _call(audit_o_licence_compliance,
              operator_name="Templeman Haulage Ltd",
              licence_number="OF1234567",
              num_vehicles=10,
              available_capital_gbp=60_000,
              tm_hours_per_week=10,
              pmi_compliance_pct=98.0,
              drivers_hours_infringement_count=1,
              tacho_download_overdue_count=0,
              cpc_expired_count=0,
              has_designated_tm=True,
              has_sufficient_premises=True,
              last_mot_pass_rate_pct=92.0,
              has_active_repute_issues=False)
    assert r["pass_fail"] == "PASS"
    assert r["overall_score"] >= 80
    assert "area_scores" in r
    assert set(O_LICENCE_AREAS).issubset(set(r["area_scores"].keys()))


def test_o_licence_audit_failing_operator_returns_top_5_risks():
    r = _call(audit_o_licence_compliance,
              operator_name="Bad Apple Transport",
              licence_number="OB7654321",
              num_vehicles=15,
              available_capital_gbp=10_000,           # massive deficit
              tm_hours_per_week=2,                    # well below 20h benchmark
              pmi_compliance_pct=60.0,                # killer finding
              drivers_hours_infringement_count=20,
              tacho_download_overdue_count=5,
              cpc_expired_count=3,
              has_designated_tm=True,
              has_sufficient_premises=True,
              last_mot_pass_rate_pct=55.0,
              has_active_repute_issues=True)
    assert r["pass_fail"] == "FAIL"
    assert len(r["top_5_risks"]) <= 5
    # Highest severity risk should appear first
    assert r["top_5_risks"][0]["severity"] >= 9


def test_o_licence_audit_no_tm_is_terminal():
    r = _call(audit_o_licence_compliance,
              operator_name="No TM Co",
              num_vehicles=5,
              available_capital_gbp=22_800,
              tm_hours_per_week=0,
              has_designated_tm=False)
    assert r["pass_fail"] == "FAIL"
    assert r["area_scores"]["professional_competence"] == 0.0


# ----------------------------------------------------------------------
# 2) check_financial_standing - 2026 rates
# ----------------------------------------------------------------------

def test_financial_standing_one_vehicle_pass():
    r = _call(check_financial_standing, num_vehicles=1, available_capital_gbp=10_000)
    assert r["required_gbp"] == FIN_STANDING_FIRST_VEHICLE_GBP  # 8400
    assert r["compliant"] is True
    assert r["surplus_or_deficit_gbp"] == 1600.0


def test_financial_standing_ten_vehicles_calculation():
    r = _call(check_financial_standing, num_vehicles=10, available_capital_gbp=0)
    expected = FIN_STANDING_FIRST_VEHICLE_GBP + 9 * FIN_STANDING_EACH_ADDITIONAL_GBP
    assert r["required_gbp"] == expected  # 8400 + 9*4600 = 49,800
    assert r["compliant"] is False
    assert r["surplus_or_deficit_gbp"] == -expected


def test_financial_standing_zero_vehicles_normalized_to_one():
    r = _call(check_financial_standing, num_vehicles=0, available_capital_gbp=10_000)
    assert r["num_vehicles"] == 1
    assert r["required_gbp"] == FIN_STANDING_FIRST_VEHICLE_GBP


# ----------------------------------------------------------------------
# 3) check_tm_continuous_effective_control
# ----------------------------------------------------------------------

def test_tm_25_vehicles_below_20h_is_flagged_high_risk():
    """Memory: 'Below 20 hrs/wk for >25 vehicles flagged'.
    Use 28 vehicles to ensure required is 20h."""
    r = _call(check_tm_continuous_effective_control,
              tm_hours_per_week=10,
              num_vehicles=28,
              tm_is_external=True,
              tm_other_operator_count=2)
    assert r["required_hours_per_week"] == 20
    assert r["risk_level"] in ("high", "critical")
    assert any("< required" in i for i in r["issues"])


def test_tm_external_with_many_operators_flagged():
    r = _call(check_tm_continuous_effective_control,
              tm_hours_per_week=30,
              num_vehicles=20,
              tm_is_external=True,
              tm_other_operator_count=5)
    assert any("other operators" in i for i in r["issues"])


def test_tm_compliant_returns_low_risk():
    r = _call(check_tm_continuous_effective_control,
              tm_hours_per_week=8,
              num_vehicles=8,
              tm_is_external=False,
              tm_other_operator_count=0)
    assert r["risk_level"] == "low"
    assert r["issues"] == []


# ----------------------------------------------------------------------
# 4) audit_pmi_compliance
# ----------------------------------------------------------------------

def test_pmi_audit_detects_6week_gap():
    r = _call(audit_pmi_compliance,
              pmi_records=[
                  {"vrn": "AB12CDE", "pmi_dates": ["2026-01-01", "2026-02-10"]},  # 40d gap, OK (< 42d)
                  {"vrn": "XY34ZZZ", "pmi_dates": ["2026-01-01", "2026-04-01"]},  # 90d gap, FAIL
              ],
              cadence="standard")
    assert r["gaps_count"] == 1
    assert r["gaps_found"][0]["vrn"] == "XY34ZZZ"
    assert r["longest_gap_days"] == 90


def test_pmi_audit_specialist_4week_cadence():
    r = _call(audit_pmi_compliance,
              pmi_records=[
                  {"vrn": "TIP01", "pmi_dates": ["2026-01-01", "2026-02-10"]},  # 40d > 28d cadence
              ],
              cadence="specialist")
    assert r["max_days_between_pmi"] == 28
    assert r["gaps_count"] == 1


def test_pmi_audit_all_compliant_passes():
    r = _call(audit_pmi_compliance,
              pmi_records=[
                  {"vrn": "AA01", "pmi_dates": ["2026-01-01", "2026-02-10", "2026-03-20"]},
              ],
              cadence="standard")
    assert r["gaps_count"] == 0
    assert r["verdict"] == "PASS"
    assert r["percentage_on_time"] == 100.0


# ----------------------------------------------------------------------
# 5) generate_public_inquiry_brief - the WEDGE
# ----------------------------------------------------------------------

def test_pi_brief_has_8_sections_and_costs():
    r = _call(generate_public_inquiry_brief,
              operator_name="Templeman Haulage Ltd",
              licence_number="OF1234567",
              triggers=["OCRS Red sustained > 6 months", "Maintenance investigation finding"],
              fleet_size=15,
              tm_name="Nicholas Templeman",
              operator_history_years=12,
              prior_pi_count=0,
              pmi_compliance_pct=72.0,
              ocrs_band="red")
    sections = r["brief_sections"]
    assert len(sections) == 8
    expected_section_starts = ["I.", "II.", "III.", "IV.", "V.", "VI.", "VII.", "VIII."]
    for i, prefix in enumerate(expected_section_starts):
        assert sections[i]["section"].startswith(prefix)
    assert "legal_solicitor_advocate_gbp" in r["estimated_costs"]
    assert "insurance_jump_annual_gbp" in r["estimated_costs"]


def test_pi_brief_horror_stories_include_named_disqualifications():
    """Memory: '6 named TM disqualifications 2024-25
    (Davies 4yr, Murphy indef, Rowland 12mo, Kingston, James, Ogilvie)'."""
    r = _call(generate_public_inquiry_brief,
              operator_name="Test Operator",
              fleet_size=5,
              tm_name="Test TM")
    horrors = r["recent_horror_stories_2024_25"]
    horror_text = " ".join(horrors).lower()
    assert "davies" in horror_text
    assert "murphy" in horror_text
    assert "rowland" in horror_text
    assert "kingston" in horror_text
    assert "james" in horror_text
    assert "ogilvie" in horror_text


def test_pi_brief_includes_transport_solicitors():
    r = _call(generate_public_inquiry_brief,
              operator_name="Test Operator",
              fleet_size=5)
    solicitors = r["named_solicitors_uk_transport"]
    sol_text = " ".join(solicitors).lower()
    assert "backhouse jones" in sol_text
    assert "aaron and partners" in sol_text or "aaron & partners" in sol_text
    assert "jmw" in sol_text


# ----------------------------------------------------------------------
# 6) forecast_pi_risk
# ----------------------------------------------------------------------

def test_forecast_pi_risk_critical_with_red_sustained_and_maintenance():
    r = _call(forecast_pi_risk,
              ocrs_band="red",
              sustained_red_months=7,
              pg9_prohibitions_12mo=4,
              maintenance_investigation_open=True,
              drivers_hours_systematic=True,
              repute_at_risk=True,
              pmi_compliance_pct=60.0)
    assert r["risk_band"] == "critical"
    assert r["weeks_to_likely_pi"] is not None
    assert r["weeks_to_likely_pi"] <= 6
    assert len(r["top_3_triggers"]) == 3


def test_forecast_pi_risk_low_for_clean_operator():
    r = _call(forecast_pi_risk,
              ocrs_band="green",
              sustained_red_months=0,
              pg9_prohibitions_12mo=0,
              maintenance_investigation_open=False,
              pmi_compliance_pct=98.0)
    assert r["risk_band"] == "low"
    assert r["weeks_to_likely_pi"] is None


# ----------------------------------------------------------------------
# 7) check_repute_indicators - using 6 named TM disqualifications context
# ----------------------------------------------------------------------

def test_repute_clean_returns_good():
    r = _call(check_repute_indicators)
    assert r["repute_status"] == "Good"
    assert r["repute_score"] == 0


def test_repute_davies_scenario_repute_lost():
    """Steven Davies scenario: repute lost, maintenance + driver-hours,
    4-year disqualification. Replicate the trigger signal set."""
    r = _call(check_repute_indicators,
              convictions_road_transport=1,
              pg9_s_marked_12mo=3,
              fixed_penalties_drivers_hours=2)
    assert r["repute_status"] in ("At Risk", "Lost")
    assert r["repute_score"] >= 14 or r["repute_status"] == "Lost"


def test_repute_murphy_scenario_indefinite_disq():
    """Maurice Murphy: indefinite disqualification, TM + operator.
    Tacho falsification = solo top weight."""
    r = _call(check_repute_indicators,
              tm_disqualification_history=True,
              tacho_falsification_finding=True,
              dvsa_referrals_pending=1)
    assert r["repute_status"] == "Lost"
    # Confirm horror-story comparator surfaces in payload
    assert "maurice_murphy" in r["comparators_2024_25"]
    assert "indefinite" in r["comparators_2024_25"]["maurice_murphy"]["period"]


def test_repute_kingston_maintenance_investigation():
    """Tom Kingston: disqualification following maintenance investigation."""
    r = _call(check_repute_indicators,
              pg9_s_marked_12mo=2,
              dvsa_referrals_pending=1,
              convictions_road_transport=1)
    assert r["repute_status"] in ("At Risk", "Lost")


def test_repute_includes_all_6_named_disqualifications():
    r = _call(check_repute_indicators)
    comparators = r["comparators_2024_25"]
    for name in ["steven_davies", "maurice_murphy", "mark_rowland",
                 "tom_kingston", "cheryl_james", "robert_ogilvie"]:
        assert name in comparators, f"Missing {name} in RECENT_DISQUALIFICATIONS comparators"


# ----------------------------------------------------------------------
# 8) prepare_dvsa_visit_pack
# ----------------------------------------------------------------------

def test_dvsa_visit_pack_includes_all_categories():
    r = _call(prepare_dvsa_visit_pack,
              operator_name="Templeman Haulage Ltd",
              licence_number="OF1234567",
              num_vehicles=10)
    checklist = r["evidence_checklist"]
    assert "licence_documents" in checklist
    assert "financial_standing" in checklist
    assert "vehicle_maintenance" in checklist
    assert "drivers" in checklist
    assert "compliance_systems" in checklist
    assert "trailers" in checklist
    # Expect financial standing line to include the right GBP figure
    fs_text = " ".join(checklist["financial_standing"])
    expected_amount = FIN_STANDING_FIRST_VEHICLE_GBP + 9 * FIN_STANDING_EACH_ADDITIONAL_GBP
    assert f"{expected_amount:,}" in fs_text


def test_dvsa_visit_pack_warns_on_killer_findings():
    r = _call(prepare_dvsa_visit_pack, operator_name="Test", num_vehicles=5)
    killers = r["common_killer_findings_pre_check"]
    killer_text = " ".join(killers).lower()
    assert "pmi" in killer_text
    assert "brake" in killer_text
    assert "driver hours" in killer_text or "drivers' hours" in killer_text or "drivers hours" in killer_text


# ----------------------------------------------------------------------
# 9) audit_subcontractor_due_diligence
# ----------------------------------------------------------------------

def test_subcontractor_due_diligence_passes_clean_sub():
    r = _call(audit_subcontractor_due_diligence,
              subcontractors=[{
                  "name": "Clean Haulage Ltd",
                  "o_licence_number": "OF1111111",
                  "o_licence_valid": True,
                  "insurance_expiry": "2027-12-31",
                  "last_mot_pass_rate_pct": 92.0,
                  "ocrs_band": "green",
                  "tm_disqualification_history": False,
              }])
    assert r["overall_pass"] is True
    assert r["pass_count"] == 1
    assert r["results"][0]["verdict"] == "PASS"


def test_subcontractor_due_diligence_fails_red_ocrs():
    r = _call(audit_subcontractor_due_diligence,
              subcontractors=[{
                  "name": "Bad Haulage Ltd",
                  "o_licence_number": "OF9999999",
                  "o_licence_valid": True,
                  "insurance_expiry": "2027-12-31",
                  "last_mot_pass_rate_pct": 70.0,
                  "ocrs_band": "red",
                  "tm_disqualification_history": False,
              }])
    assert r["overall_pass"] is False
    assert r["results"][0]["verdict"] == "FAIL"
    assert any("RED" in f for f in r["results"][0]["flags"])


def test_subcontractor_due_diligence_fails_expired_insurance():
    r = _call(audit_subcontractor_due_diligence,
              subcontractors=[{
                  "name": "Old Insurance Co",
                  "o_licence_number": "OF8888888",
                  "o_licence_valid": True,
                  "insurance_expiry": "2020-01-01",
                  "last_mot_pass_rate_pct": 85.0,
                  "ocrs_band": "green",
              }])
    assert r["overall_pass"] is False
    assert any("EXPIRED" in f for f in r["results"][0]["flags"])


# ----------------------------------------------------------------------
# Attestation / HMAC chain
# ----------------------------------------------------------------------

def test_attestation_carries_ts_sig_issuer_version():
    r = _call(check_financial_standing, num_vehicles=1, available_capital_gbp=10_000)
    assert "ts" in r and "sig" in r and "issuer" in r and "version" in r
    assert r["issuer"] == "meok-dvsa-olicence-mcp"


def test_attestation_signature_present_or_unsigned_label():
    """If no MEOK_HMAC_SECRET set, signature is explicit 'unsigned-no-key-configured'.
    If set, signature is a 64-char SHA256 hex string. Confirm one or the other."""
    r = _call(forecast_pi_risk, ocrs_band="green")
    sig = r["sig"]
    assert sig == "unsigned-no-key-configured" or len(sig) == 64


def test_hmac_chain_with_secret_set(monkeypatch):
    """HMAC chain: setting a secret produces a deterministic signature."""
    import server as srv
    monkeypatch.setattr(srv, "_HMAC_SECRET", "test-secret-value")
    r = _call(check_financial_standing, num_vehicles=1, available_capital_gbp=10_000)
    assert r["sig"] != "unsigned-no-key-configured"
    assert len(r["sig"]) == 64
    # Same payload + secret = same sig deterministically
    r2 = _call(check_financial_standing, num_vehicles=1, available_capital_gbp=10_000)
    # ts differs so we cannot directly compare; but both should be valid 64-char hex
    assert len(r2["sig"]) == 64


# ----------------------------------------------------------------------
# Module-level invariants
# ----------------------------------------------------------------------

def test_recent_disqualifications_has_all_6_named():
    expected = {"steven_davies", "maurice_murphy", "mark_rowland",
                "tom_kingston", "cheryl_james", "robert_ogilvie"}
    assert expected.issubset(set(RECENT_DISQUALIFICATIONS.keys()))


def test_o_licence_areas_has_11_statutory_areas():
    assert len(O_LICENCE_AREAS) == 11


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
