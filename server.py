#!/usr/bin/env python3
"""
MEOK DVSA Operator Licence + Public Inquiry MCP
=================================================

By MEOK AI Labs https://haulage.app MIT
<!-- mcp-name: io.github.CSOAI-ORG/meok-dvsa-olicence-mcp -->

WHAT THIS DOES
--------------
UK general haulage runs on the O-licence, granted by the Traffic Commissioner
under the Goods Vehicles (Licensing of Operators) Act 1995. Lose it and the
business is over.

A single Public Inquiry typically costs:
  - £8,000 to £25,000 legal fees (solicitor + advocate)
  - £20,000 to £100,000 per year insurance jump
  - Loss of FORS / customer contracts
  - At worst: revocation, TM disqualification, business closure

Recent Traffic Commissioner public decisions (2024-25) include:
  - Steven Davies     disqualified 4 years
  - Maurice Murphy    disqualified indefinitely
  - Mark Rowland      disqualified 12 months
  - Tom Kingston      disqualified following maintenance investigation
  - Cheryl James      TM repute lost
  - Robert Ogilvie    disqualified, repute lost

This MCP gives the named TM + owner-operator the callable toolkit to:
  - Audit O-licence compliance across all 11 statutory areas
  - Check financial standing against 2026 rates
  - Test TM continuous + effective control vs Senior TC guidance
  - Detect PMI cadence gaps (the killer DVSA finding)
  - Generate a defence brief for a Traffic Commissioner Public Inquiry
  - Forecast PI risk from known triggers
  - Score repute (Good / At Risk / Lost)
  - Pack a 24h-before-DVSA-visit evidence bundle
  - Vet subcontractor due diligence

TOOLS (9)
---------
- audit_o_licence_compliance(operator_data)        all 11 statutory areas
- check_financial_standing(vehicles, capital)      8400 first + 4600 each
- check_tm_continuous_effective_control(hrs, n)    Senior TC guidance
- audit_pmi_compliance(pmi_records)                6-week or 4-week cadence
- generate_public_inquiry_brief(op, lic, ...)      8-section defence brief
- forecast_pi_risk(operator_data)                  risk band + weeks-to-PI
- check_repute_indicators(history)                 Good / At Risk / Lost
- prepare_dvsa_visit_pack(operator_data)           24h evidence checklist
- audit_subcontractor_due_diligence(subs)          each sub O-licence + MOT

WHY YOU PAY
-----------
One avoided Public Inquiry saves more than 5 years of Fleet-tier subscription.
The PI brief generator alone is the wedge.

PRICING
-------
Free MIT self-host
79 GBP per month Starter
249 GBP per month Pro
799 GBP per month Fleet

REGULATORY BASIS
----------------
Goods Vehicles (Licensing of Operators) Act 1995
Senior Traffic Commissioner Statutory Guidance + Directives 1 to 12
DVSA Operator Compliance Risk Score (OCRS) Guide
Public Inquiries - Traffic Commissioner public decisions register
DVSA Guide to Maintaining Roadworthiness (PMI cadence)
Goods Vehicles (Licensing of Operators) Regulations 1995 (as amended)
"""

from __future__ import annotations
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone, date
from typing import Optional
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("meok-dvsa-olicence")
_HMAC_SECRET = os.environ.get("MEOK_HMAC_SECRET", "")


# ----------------------------------------------------------------------
# Regulatory tables (2026 rates + Senior TC Statutory Guidance)
# ----------------------------------------------------------------------

# Financial standing rates verified for 2026 (Senior TC Statutory Doc No. 2)
FIN_STANDING_FIRST_VEHICLE_GBP = 8400
FIN_STANDING_EACH_ADDITIONAL_GBP = 4600

# Senior TC Statutory Document No. 3 - Transport Managers
# "Continuous and effective control" — hours per week benchmarks
TM_HOURS_BENCHMARKS = {
    "1_2_vehicles": 2,
    "3_5_vehicles": 4,
    "6_10_vehicles": 8,
    "11_14_vehicles": 12,
    "15_29_vehicles": 20,
    "30_50_vehicles": 30,
    "51_plus_vehicles": "full_time_or_multi_tm",
}

# PMI cadence per DVSA Guide to Maintaining Roadworthiness
PMI_CADENCE_DAYS = {
    "standard": 42,      # 6 weeks
    "specialist": 28,    # 4 weeks (tippers, heavy haulage, recovery, refuse)
    "trailer": 42,       # 6 weeks aligned with motive
}

# Statutory O-licence audit areas
O_LICENCE_AREAS = [
    "financial_standing",
    "repute",
    "professional_competence",
    "vehicle_fitness",
    "maintenance_arrangements",
    "drivers_hours",
    "tachograph",
    "drivers_cpc",
    "vehicle_examiner_role",
    "designated_tm",
    "premises_sufficient",
]

# Known PI trigger reasons (Senior TC Statutory Guidance + recent decisions)
PI_TRIGGER_REASONS = [
    "OCRS Red sustained > 6 months",
    "Multiple roadside prohibitions in 12 months",
    "Maintenance investigation finding",
    "Driver-hours systematic non-compliance",
    "Loss of financial standing",
    "Loss of repute of operator/TM",
    "Failure to notify changes within 28 days",
    "DVSA referral for criminal/civil matters",
    "PG9 prohibitions with S-marking (significant)",
    "Failure of fitness/maintenance audit",
    "TM not exercising continuous + effective control",
]

# 2024-25 disqualified TMs / operators — for repute test scenarios
# (from Traffic Commissioner public decisions register)
RECENT_DISQUALIFICATIONS = {
    "steven_davies": {"period": "4 years", "year": 2024, "ground": "repute lost, maintenance + driver-hours"},
    "maurice_murphy": {"period": "indefinite", "year": 2024, "ground": "indefinite disqualification, TM + operator"},
    "mark_rowland": {"period": "12 months", "year": 2025, "ground": "repute lost"},
    "tom_kingston": {"period": "unspecified", "year": 2024, "ground": "maintenance investigation"},
    "cheryl_james": {"period": "TM repute lost", "year": 2025, "ground": "revocation upheld"},
    "robert_ogilvie": {"period": "unspecified", "year": 2025, "ground": "repute lost, multiple PG9s"},
}

REPUTE_WEIGHTS = {
    "conviction_road_transport": 8,
    "conviction_non_road": 3,
    "pg9_prohibition_s_marked": 4,
    "pg9_prohibition_clean": 2,
    "dvsa_referral_pending": 5,
    "tm_disqualification_history": 9,
    "failure_to_notify_28_days": 2,
    "fixed_penalty_drivers_hours": 3,
    "tachograph_falsification_finding": 10,
}


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _sign(payload: dict) -> str:
    """HMAC-sign the response for tamper-evident audit."""
    if not _HMAC_SECRET:
        return "unsigned-no-key-configured"
    return hmac.new(
        _HMAC_SECRET.encode(),
        json.dumps(payload, sort_keys=True, default=str).encode(),
        hashlib.sha256,
    ).hexdigest()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _attestation(payload: dict) -> dict:
    return {
        **payload,
        "ts": _ts(),
        "sig": _sign(payload),
        "issuer": "meok-dvsa-olicence-mcp",
        "version": "1.0.0",
    }


def _tm_hours_required(num_vehicles: int) -> int:
    """Senior TC Statutory Guidance benchmark hours per week."""
    if num_vehicles <= 2:
        return 2
    if num_vehicles <= 5:
        return 4
    if num_vehicles <= 10:
        return 8
    if num_vehicles <= 14:
        return 12
    if num_vehicles <= 29:
        return 20
    if num_vehicles <= 50:
        return 30
    return 35  # effectively full-time


# ----------------------------------------------------------------------
# Tools
# ----------------------------------------------------------------------

@mcp.tool()
def audit_o_licence_compliance(
    operator_name: str = "",
    licence_number: str = "",
    num_vehicles: int = 1,
    available_capital_gbp: float = 0.0,
    tm_hours_per_week: float = 0.0,
    pmi_compliance_pct: float = 100.0,
    drivers_hours_infringement_count: int = 0,
    tacho_download_overdue_count: int = 0,
    cpc_expired_count: int = 0,
    has_designated_tm: bool = True,
    has_sufficient_premises: bool = True,
    last_mot_pass_rate_pct: float = 100.0,
    has_active_repute_issues: bool = False,
) -> dict:
    """Comprehensive 11-area O-licence audit.

    Args:
      operator_name: trading name
      licence_number: e.g. "OF1234567"
      num_vehicles: count of vehicles on the licence
      available_capital_gbp: liquid + agreed credit per Statutory Doc 2
      tm_hours_per_week: hours TM exercises continuous + effective control
      pmi_compliance_pct: % of PMIs completed within 6-week window (last 12mo)
      drivers_hours_infringement_count: trailing 28 days
      tacho_download_overdue_count: drivers with card download > 28d overdue
      cpc_expired_count: drivers with expired DCPC
      has_designated_tm: a named external/internal TM is in place
      has_sufficient_premises: operating centre meets policy + adequate
      last_mot_pass_rate_pct: vehicle first-time MoT pass rate (12mo)
      has_active_repute_issues: any open conviction / DVSA referral / TM disq

    Returns: per-area score (0-100), overall pass/fail, top 5 risks ranked.
    """
    scores = {}
    risks = []

    # 1) Financial standing
    required_fs = FIN_STANDING_FIRST_VEHICLE_GBP + (
        max(0, num_vehicles - 1) * FIN_STANDING_EACH_ADDITIONAL_GBP
    )
    fs_ratio = available_capital_gbp / required_fs if required_fs else 1.0
    fs_score = min(100.0, fs_ratio * 100.0)
    scores["financial_standing"] = round(fs_score, 1)
    if fs_score < 100:
        risks.append({
            "area": "financial_standing",
            "score": round(fs_score, 1),
            "issue": f"Deficit GBP {round(required_fs - available_capital_gbp)}",
            "severity": 9 if fs_score < 50 else 6,
        })

    # 2) Repute
    rep_score = 30.0 if has_active_repute_issues else 100.0
    scores["repute"] = rep_score
    if has_active_repute_issues:
        risks.append({
            "area": "repute",
            "score": rep_score,
            "issue": "Active repute issue - open conviction, DVSA referral, or TM disq history",
            "severity": 10,
        })

    # 3) Professional competence (proxy: designated TM + TM hours)
    pc_score = 100.0 if has_designated_tm else 0.0
    scores["professional_competence"] = pc_score
    if not has_designated_tm:
        risks.append({
            "area": "professional_competence",
            "score": pc_score,
            "issue": "No designated TM - licence cannot stand under Act 1995 s.13A",
            "severity": 10,
        })

    # 4) Vehicle fitness (proxy: MoT pass rate)
    vf_score = float(last_mot_pass_rate_pct)
    scores["vehicle_fitness"] = vf_score
    if vf_score < 85:
        risks.append({
            "area": "vehicle_fitness",
            "score": vf_score,
            "issue": f"MoT first-time pass rate {vf_score}% (DVSA expects >85%)",
            "severity": 7,
        })

    # 5) Maintenance arrangements (PMI)
    ma_score = float(pmi_compliance_pct)
    scores["maintenance_arrangements"] = ma_score
    if ma_score < 95:
        risks.append({
            "area": "maintenance_arrangements",
            "score": ma_score,
            "issue": f"PMI compliance {ma_score}% - DVSA killer finding if < 95%",
            "severity": 9 if ma_score < 80 else 6,
        })

    # 6) Drivers' hours
    dh_score = max(0.0, 100.0 - drivers_hours_infringement_count * 5.0)
    scores["drivers_hours"] = dh_score
    if drivers_hours_infringement_count > 5:
        risks.append({
            "area": "drivers_hours",
            "score": dh_score,
            "issue": f"{drivers_hours_infringement_count} infringements in 28 days",
            "severity": 8,
        })

    # 7) Tachograph
    tc_score = max(0.0, 100.0 - tacho_download_overdue_count * 10.0)
    scores["tachograph"] = tc_score
    if tacho_download_overdue_count > 0:
        risks.append({
            "area": "tachograph",
            "score": tc_score,
            "issue": f"{tacho_download_overdue_count} drivers with card download > 28d overdue",
            "severity": 6,
        })

    # 8) Drivers' CPC
    cp_score = max(0.0, 100.0 - cpc_expired_count * 15.0)
    scores["drivers_cpc"] = cp_score
    if cpc_expired_count > 0:
        risks.append({
            "area": "drivers_cpc",
            "score": cp_score,
            "issue": f"{cpc_expired_count} drivers with expired DCPC - cannot drive vocationally",
            "severity": 8,
        })

    # 9) Vehicle examiner role (proxy: PMI + MoT signals)
    ve_score = (ma_score + vf_score) / 2.0
    scores["vehicle_examiner_role"] = round(ve_score, 1)

    # 10) Designated TM continuous + effective control
    req_hrs = _tm_hours_required(num_vehicles)
    tm_ratio = (tm_hours_per_week / req_hrs) if req_hrs else 1.0
    tm_score = min(100.0, tm_ratio * 100.0)
    scores["designated_tm"] = round(tm_score, 1)
    if tm_score < 100:
        risks.append({
            "area": "designated_tm",
            "score": round(tm_score, 1),
            "issue": f"TM hours {tm_hours_per_week}/wk vs required {req_hrs}/wk for {num_vehicles} vehicles",
            "severity": 9 if tm_score < 50 else 5,
        })

    # 11) Premises
    pr_score = 100.0 if has_sufficient_premises else 0.0
    scores["premises_sufficient"] = pr_score
    if not has_sufficient_premises:
        risks.append({
            "area": "premises_sufficient",
            "score": pr_score,
            "issue": "Operating centre inadequate - parking / environmental / planning",
            "severity": 7,
        })

    # Overall
    overall = round(sum(scores.values()) / len(scores), 1)
    pass_fail = "PASS" if overall >= 80 and not any(r["severity"] >= 9 for r in risks) else "FAIL"

    risks.sort(key=lambda r: r["severity"], reverse=True)
    top_5_risks = risks[:5]

    payload = {
        "tool": "audit_o_licence_compliance",
        "operator_name": operator_name,
        "licence_number": licence_number,
        "num_vehicles": num_vehicles,
        "area_scores": scores,
        "overall_score": overall,
        "pass_fail": pass_fail,
        "top_5_risks": top_5_risks,
        "advisory": (
            "Compliant - schedule rolling internal audit + brief TM monthly."
            if pass_fail == "PASS"
            else "FAIL - generate PI defence brief now, engage transport solicitor, "
                 "action top 5 risks in 14 days. PI referral likely if uncorrected."
        ),
        "reference": "Goods Vehicles (Licensing of Operators) Act 1995 + Senior TC Statutory Guidance",
    }
    return _attestation(payload)


@mcp.tool()
def check_financial_standing(
    num_vehicles: int = 1,
    available_capital_gbp: float = 0.0,
) -> dict:
    """Financial standing check per Senior TC Statutory Document No. 2.

    2026 rates: GBP 8,400 first vehicle + GBP 4,600 each additional.

    Args:
      num_vehicles: total vehicles on licence
      available_capital_gbp: average available capital + agreed credit
        over last 3 months bank statements (or equivalent evidence).
    """
    if num_vehicles < 1:
        num_vehicles = 1
    required = FIN_STANDING_FIRST_VEHICLE_GBP + (
        (num_vehicles - 1) * FIN_STANDING_EACH_ADDITIONAL_GBP
    )
    surplus = round(available_capital_gbp - required, 2)
    compliant = surplus >= 0
    recommendation = (
        "Compliant. Maintain 3 months bank statements + overdraft facility letter as evidence."
        if compliant
        else f"Deficit GBP {abs(surplus):,.0f}. Inject capital, secure overdraft, "
             "or reduce vehicle count. If sustained > 6 months, notify TC voluntarily under "
             "Statutory Guidance to avoid public-inquiry escalation."
    )
    payload = {
        "tool": "check_financial_standing",
        "num_vehicles": num_vehicles,
        "required_gbp": required,
        "actual_gbp": round(available_capital_gbp, 2),
        "surplus_or_deficit_gbp": surplus,
        "compliant": compliant,
        "recommendation": recommendation,
        "rate_first_vehicle_gbp": FIN_STANDING_FIRST_VEHICLE_GBP,
        "rate_each_additional_gbp": FIN_STANDING_EACH_ADDITIONAL_GBP,
        "rate_year": 2026,
        "reference": "Senior Traffic Commissioner Statutory Document No. 2",
    }
    return _attestation(payload)


@mcp.tool()
def check_tm_continuous_effective_control(
    tm_hours_per_week: float = 0.0,
    num_vehicles: int = 1,
    tm_is_external: bool = False,
    tm_other_operator_count: int = 0,
) -> dict:
    """Senior TC Statutory Document No. 3 - the TM must exercise continuous
    and effective control of transport operations.

    Args:
      tm_hours_per_week: contracted + actual hours of control
      num_vehicles: vehicles on the licence
      tm_is_external: contracted TM (not employed) - higher scrutiny
      tm_other_operator_count: other operators the TM acts for
    """
    required = _tm_hours_required(num_vehicles)
    ratio = (tm_hours_per_week / required) if required else 1.0

    issues = []
    if tm_hours_per_week < required:
        issues.append(f"Hours {tm_hours_per_week}/wk < required {required}/wk for {num_vehicles} vehicles")
    if tm_is_external and tm_other_operator_count >= 4:
        issues.append(f"External TM acting for {tm_other_operator_count} other operators - TC may question capacity")
    if tm_is_external and num_vehicles > 25 and tm_hours_per_week < 20:
        issues.append("External TM, > 25 vehicles, < 20h/wk - flagged as not effective per Senior TC guidance")
    if num_vehicles > 50:
        issues.append("Fleet > 50 vehicles - consider second TM or full-time arrangement")

    if not issues:
        risk = "low"
        advice = "Compliant with Senior TC benchmarks. Document hours via signed TM contract + diary."
    elif ratio < 0.5:
        risk = "critical"
        advice = "URGENT: Below 50% of required hours. PI referral risk high. Increase hours, add second TM, or downsize fleet."
    elif ratio < 1.0:
        risk = "high"
        advice = "Below benchmark. Either raise contracted hours or reduce vehicle count. Document remediation."
    else:
        risk = "medium"
        advice = "Hours OK but other red flags (external TM scale). Document due-diligence + TM diary."

    payload = {
        "tool": "check_tm_continuous_effective_control",
        "tm_hours_per_week": tm_hours_per_week,
        "num_vehicles": num_vehicles,
        "required_hours_per_week": required,
        "ratio": round(ratio, 2),
        "tm_is_external": tm_is_external,
        "tm_other_operators": tm_other_operator_count,
        "issues": issues,
        "risk_level": risk,
        "advice": advice,
        "reference": "Senior Traffic Commissioner Statutory Document No. 3",
    }
    return _attestation(payload)


@mcp.tool()
def audit_pmi_compliance(
    pmi_records: Optional[list] = None,
    cadence: str = "standard",
) -> dict:
    """Audit Preventative Maintenance Inspection cadence per DVSA Guide
    to Maintaining Roadworthiness. PMI gaps are the single biggest killer
    finding in a DVSA on-site visit.

    Args:
      pmi_records: list of dicts like
        {"vrn": "AB12CDE", "pmi_dates": ["2026-01-10", "2026-02-21", ...]}
      cadence: 'standard' (6 weeks) or 'specialist' (4 weeks, tippers,
                heavy haulage, recovery, refuse).
    """
    pmi_records = pmi_records or []
    max_days = PMI_CADENCE_DAYS.get(cadence, PMI_CADENCE_DAYS["standard"])
    gaps_found = []
    on_time_count = 0
    total_intervals = 0
    longest_gap_days = 0

    for v in pmi_records:
        vrn = v.get("vrn", "UNKNOWN")
        dates_raw = v.get("pmi_dates", [])
        parsed = []
        for d in dates_raw:
            try:
                parsed.append(date.fromisoformat(d))
            except Exception:
                pass
        parsed.sort()
        for i in range(1, len(parsed)):
            gap = (parsed[i] - parsed[i - 1]).days
            total_intervals += 1
            if gap > max_days:
                gaps_found.append({
                    "vrn": vrn,
                    "from": parsed[i - 1].isoformat(),
                    "to": parsed[i].isoformat(),
                    "gap_days": gap,
                    "exceeded_by_days": gap - max_days,
                })
            else:
                on_time_count += 1
            longest_gap_days = max(longest_gap_days, gap)

    pct_on_time = round((on_time_count / total_intervals * 100.0), 1) if total_intervals else 100.0

    if not gaps_found:
        verdict = "PASS"
        advice = f"All inspections within {max_days}-day window. Maintain forward-planner."
    elif pct_on_time >= 95:
        verdict = "MARGINAL"
        advice = f"{len(gaps_found)} gaps. Tighten forward-planner. DVSA tolerates < 5% slippage."
    else:
        verdict = "FAIL"
        advice = (f"{len(gaps_found)} gaps, {pct_on_time}% on-time. "
                  "This is the killer DVSA finding. Action this week: review root cause, "
                  "schedule remedial inspections, brief TM, update forward-planner.")

    payload = {
        "tool": "audit_pmi_compliance",
        "cadence": cadence,
        "max_days_between_pmi": max_days,
        "vehicles_audited": len(pmi_records),
        "intervals_evaluated": total_intervals,
        "gaps_found": gaps_found,
        "gaps_count": len(gaps_found),
        "longest_gap_days": longest_gap_days,
        "percentage_on_time": pct_on_time,
        "verdict": verdict,
        "advice": advice,
        "reference": "DVSA Guide to Maintaining Roadworthiness",
    }
    return _attestation(payload)


@mcp.tool()
def generate_public_inquiry_brief(
    operator_name: str,
    licence_number: str = "",
    triggers: Optional[list] = None,
    fleet_size: int = 0,
    tm_name: str = "",
    operator_history_years: int = 0,
    prior_pi_count: int = 0,
    corrective_actions_completed: Optional[list] = None,
    financial_evidence_attached: bool = False,
    pmi_compliance_pct: float = 0.0,
    ocrs_band: str = "amber",
) -> dict:
    """Produce a Traffic Commissioner Public Inquiry defence brief.

    The wedge. 8 sections per Senior TC Statutory Guidance.

    Args:
      operator_name: trading name
      licence_number: e.g. "OF1234567"
      triggers: list of strings from PI_TRIGGER_REASONS
      fleet_size: number of vehicles
      tm_name: designated Transport Manager
      operator_history_years: years since licence grant
      prior_pi_count: number of prior public inquiries
      corrective_actions_completed: list of strings
      financial_evidence_attached: 3-month bank statements + standing
      pmi_compliance_pct: PMI on-time rate (last 12 months)
      ocrs_band: 'green' / 'amber' / 'red'
    """
    triggers = triggers or []
    corrective_actions_completed = corrective_actions_completed or []

    sections = [
        {
            "section": "I. Operator's history + good repute",
            "content_required": [
                f"Years licensed: {operator_history_years}",
                f"Prior PI count: {prior_pi_count}",
                "Good-repute character references (3+ business / industry referees)",
                "FORS Bronze / Silver / Gold certifications",
                "Industry memberships (RHA, Logistics UK)",
                "Charitable / community evidence (if any)",
            ],
        },
        {
            "section": "II. Specific triggers + root-cause analysis",
            "triggers_identified": triggers,
            "content_required": [
                "5-Whys root-cause for each trigger",
                "External factors (driver shortage, post-Brexit, recession)",
                "Internal factors (training gap, system gap, leadership)",
                "Owned vs disputed (be honest - TCs respect candour)",
            ],
        },
        {
            "section": "III. Corrective action plan with evidence",
            "actions_completed": corrective_actions_completed,
            "content_required": [
                "Schedule of remedial actions (dated, owner, evidence)",
                "OCRS trajectory chart (last 12 months)",
                "Internal audit programme (monthly + annual)",
                "Independent compliance audit (RHA, Logistics UK, named consultant)",
                "Staff briefings on hours + tacho",
                f"Current OCRS band: {ocrs_band.upper()}",
            ],
        },
        {
            "section": "IV. Transport Manager statement of repute + CPD",
            "tm_name": tm_name,
            "content_required": [
                "TM CPC certificate (Operator CPC) - copy attached",
                "CPD log (35h over last 5 years - minimum)",
                "TM contract hours-of-work record",
                f"TM diary - last 90 days, evidencing continuous control of {fleet_size} vehicles",
                "TM statement of repute (signed declaration)",
                "TM other-operator declarations (Statutory Doc 3)",
            ],
        },
        {
            "section": "V. Financial standing evidence",
            "financial_evidence_attached": financial_evidence_attached,
            "content_required": [
                "3 months bank statements (most recent)",
                f"Standing required: GBP {FIN_STANDING_FIRST_VEHICLE_GBP + (max(0, fleet_size - 1) * FIN_STANDING_EACH_ADDITIONAL_GBP):,}",
                "Overdraft facility letter (if relied upon)",
                "Management accounts (last 2 years)",
                "Forward cash-flow forecast (12 months)",
                "Accountant's letter of comfort",
            ],
        },
        {
            "section": "VI. Vehicle maintenance evidence",
            "content_required": [
                f"PMI compliance: {pmi_compliance_pct}% on-time",
                "PMI sheets - last 12 months (every vehicle)",
                "Brake test reports - every PMI (laden where required)",
                "MoT history (annual test) - every vehicle",
                "Tachograph calibration certificates",
                "Driver defect reports + actioned-defect log",
                "Maintenance contract / in-house workshop ISO9001 or PAS",
                "Forward-planner screenshot (PMI + MoT calendar)",
            ],
        },
        {
            "section": "VII. Driver management evidence",
            "content_required": [
                "Driver list with DCPC expiry + entitlement check",
                "Infringement letters issued + signed back",
                "Drivers' hours training records (annual)",
                "Tachograph download cadence log (28-day card / 90-day VU)",
                "Driver licence checks (annual mandatory)",
                "Disciplinary action evidence",
            ],
        },
        {
            "section": "VIII. Proposed undertakings",
            "content_required": [
                "Voluntary curtailment of vehicle authorisation (e.g. 20 -> 15)",
                "Quarterly independent audit for 24 months (named firm)",
                "Monthly compliance report submitted to TC office",
                "Additional TM hours (specify increase, e.g. 8 -> 20)",
                "Driver-hours systems upgrade (specify product e.g. Microlise, FleetCheck)",
                "FORS Silver achieved within 12 months",
                "Suspension of any specific operating centre that triggered the inquiry",
                "Voluntary financial penalty (where appropriate)",
            ],
        },
    ]

    horror_stories = [
        f"{name.replace('_', ' ').title()}: {d['ground']} ({d['period']}, {d['year']})"
        for name, d in RECENT_DISQUALIFICATIONS.items()
    ]

    payload = {
        "tool": "generate_public_inquiry_brief",
        "operator_name": operator_name,
        "licence_number": licence_number,
        "fleet_size": fleet_size,
        "tm_name": tm_name,
        "triggers_identified": triggers,
        "brief_sections": sections,
        "estimated_costs": {
            "legal_solicitor_advocate_gbp": "8,000 to 25,000",
            "insurance_jump_annual_gbp": "20,000 to 100,000",
            "lost_contracts_estimate_gbp": "varies - typically 6 months turnover at risk",
            "total_avoided_by_winning": "100,000+",
        },
        "named_solicitors_uk_transport": [
            "Backhouse Jones (Clitheroe)",
            "Aaron and Partners (Chester)",
            "JMW Solicitors (Manchester)",
            "Smith Bowyer Clarke (Nottingham)",
            "Rotheras Solicitors",
        ],
        "recent_horror_stories_2024_25": horror_stories,
        "next_action_72h": (
            "1. Engage transport solicitor TODAY (PI call-up notice = 14 days). "
            "2. Compile sections IV (TM) + V (financial) FIRST. "
            "3. Book independent compliance audit (RHA / Logistics UK). "
            "4. Brief insurer in writing (preserve cover)."
        ),
        "reference": "Senior Traffic Commissioner Statutory Guidance + Practice Direction on PIs",
    }
    return _attestation(payload)


@mcp.tool()
def forecast_pi_risk(
    ocrs_band: str = "green",
    sustained_red_months: int = 0,
    pg9_prohibitions_12mo: int = 0,
    maintenance_investigation_open: bool = False,
    drivers_hours_systematic: bool = False,
    financial_standing_lost: bool = False,
    repute_at_risk: bool = False,
    tm_disq_history: bool = False,
    pmi_compliance_pct: float = 100.0,
) -> dict:
    """Forecast Public Inquiry referral risk from known trigger signals.

    Each trigger weighted; returns risk_band (low/medium/high/critical),
    top 3 triggers ranked, and weeks-to-likely-PI estimate.
    """
    triggers = []
    if ocrs_band.lower() == "red" and sustained_red_months >= 6:
        triggers.append({"trigger": "OCRS Red sustained > 6 months", "weight": 10})
    elif ocrs_band.lower() == "red":
        triggers.append({"trigger": f"OCRS Red ({sustained_red_months}mo)", "weight": 6})
    elif ocrs_band.lower() == "amber":
        triggers.append({"trigger": "OCRS Amber - watch list", "weight": 2})

    if pg9_prohibitions_12mo >= 3:
        triggers.append({"trigger": f"Multiple PG9 prohibitions ({pg9_prohibitions_12mo})", "weight": 8})
    elif pg9_prohibitions_12mo >= 1:
        triggers.append({"trigger": f"PG9 prohibitions ({pg9_prohibitions_12mo})", "weight": 4})

    if maintenance_investigation_open:
        triggers.append({"trigger": "Maintenance investigation open", "weight": 9})
    if drivers_hours_systematic:
        triggers.append({"trigger": "Drivers' hours systematic non-compliance", "weight": 8})
    if financial_standing_lost:
        triggers.append({"trigger": "Loss of financial standing", "weight": 7})
    if repute_at_risk:
        triggers.append({"trigger": "Loss of repute (operator or TM)", "weight": 10})
    if tm_disq_history:
        triggers.append({"trigger": "TM disqualification history", "weight": 9})
    if pmi_compliance_pct < 80:
        triggers.append({"trigger": f"PMI compliance {pmi_compliance_pct}% (< 80%)", "weight": 7})
    elif pmi_compliance_pct < 95:
        triggers.append({"trigger": f"PMI compliance {pmi_compliance_pct}% (< 95%)", "weight": 3})

    triggers.sort(key=lambda t: t["weight"], reverse=True)
    score = sum(t["weight"] for t in triggers)

    if score == 0:
        band = "low"
        weeks_to_pi = None
    elif score < 6:
        band = "low"
        weeks_to_pi = None
    elif score < 12:
        band = "medium"
        weeks_to_pi = 26  # ~6 months
    elif score < 20:
        band = "high"
        weeks_to_pi = 12  # ~3 months
    else:
        band = "critical"
        weeks_to_pi = 4   # ~1 month - call-up imminent

    top_3 = triggers[:3]

    payload = {
        "tool": "forecast_pi_risk",
        "trigger_count": len(triggers),
        "trigger_score": score,
        "risk_band": band,
        "top_3_triggers": top_3,
        "weeks_to_likely_pi": weeks_to_pi,
        "advisory": (
            "Maintain rolling internal audit. Reassess monthly."
            if band == "low" else
            "Schedule independent compliance audit + brief TM. Reassess fortnightly."
            if band == "medium" else
            "Engage transport solicitor (advisory). Compile evidence pack now. Pre-emptive corrective action."
            if band == "high" else
            "URGENT: PI call-up likely within 4-6 weeks. Engage transport solicitor TODAY. "
            "Generate full PI defence brief (use generate_public_inquiry_brief tool). Brief insurer."
        ),
        "reference": "Senior Traffic Commissioner Statutory Guidance + DVSA OCRS Guide",
    }
    return _attestation(payload)


@mcp.tool()
def check_repute_indicators(
    convictions_road_transport: int = 0,
    convictions_other: int = 0,
    pg9_s_marked_12mo: int = 0,
    pg9_clean_12mo: int = 0,
    dvsa_referrals_pending: int = 0,
    tm_disqualification_history: bool = False,
    failures_to_notify_28d: int = 0,
    fixed_penalties_drivers_hours: int = 0,
    tacho_falsification_finding: bool = False,
) -> dict:
    """Score operator + TM repute per Senior TC Statutory Doc No. 1.

    Returns repute_status: 'Good' / 'At Risk' / 'Lost'.
    """
    score = 0
    contributing = []

    if convictions_road_transport > 0:
        w = REPUTE_WEIGHTS["conviction_road_transport"] * convictions_road_transport
        score += w
        contributing.append({"factor": f"{convictions_road_transport} road-transport conviction(s)", "weight": w})
    if convictions_other > 0:
        w = REPUTE_WEIGHTS["conviction_non_road"] * convictions_other
        score += w
        contributing.append({"factor": f"{convictions_other} non-road conviction(s)", "weight": w})
    if pg9_s_marked_12mo > 0:
        w = REPUTE_WEIGHTS["pg9_prohibition_s_marked"] * pg9_s_marked_12mo
        score += w
        contributing.append({"factor": f"{pg9_s_marked_12mo} S-marked PG9(s)", "weight": w})
    if pg9_clean_12mo > 0:
        w = REPUTE_WEIGHTS["pg9_prohibition_clean"] * pg9_clean_12mo
        score += w
        contributing.append({"factor": f"{pg9_clean_12mo} clean PG9(s)", "weight": w})
    if dvsa_referrals_pending > 0:
        w = REPUTE_WEIGHTS["dvsa_referral_pending"] * dvsa_referrals_pending
        score += w
        contributing.append({"factor": f"{dvsa_referrals_pending} pending DVSA referral(s)", "weight": w})
    if tm_disqualification_history:
        w = REPUTE_WEIGHTS["tm_disqualification_history"]
        score += w
        contributing.append({"factor": "TM disqualification history", "weight": w})
    if failures_to_notify_28d > 0:
        w = REPUTE_WEIGHTS["failure_to_notify_28_days"] * failures_to_notify_28d
        score += w
        contributing.append({"factor": f"{failures_to_notify_28d} failure(s) to notify within 28d", "weight": w})
    if fixed_penalties_drivers_hours > 0:
        w = REPUTE_WEIGHTS["fixed_penalty_drivers_hours"] * fixed_penalties_drivers_hours
        score += w
        contributing.append({"factor": f"{fixed_penalties_drivers_hours} fixed penalty (hours)", "weight": w})
    if tacho_falsification_finding:
        w = REPUTE_WEIGHTS["tachograph_falsification_finding"]
        score += w
        contributing.append({"factor": "Tachograph falsification finding", "weight": w})

    if score == 0:
        status = "Good"
        advice = "Repute intact. Maintain compliance evidence + routine internal audit."
    elif score < 6:
        status = "Good"
        advice = "Minor signals. Action root cause + document remediation."
    elif score < 14:
        status = "At Risk"
        advice = ("Repute fragile. Engage compliance consultant. "
                  "Expect DVSA scrutiny. Brief TM weekly.")
    else:
        status = "Lost"
        advice = ("Repute lost or near-lost. TM disq + licence revocation possible. "
                  "Engage transport solicitor IMMEDIATELY. Prepare PI defence brief.")

    contributing.sort(key=lambda c: c["weight"], reverse=True)

    payload = {
        "tool": "check_repute_indicators",
        "repute_score": score,
        "repute_status": status,
        "contributing_factors_ranked": contributing,
        "advice": advice,
        "comparators_2024_25": RECENT_DISQUALIFICATIONS,
        "reference": "Senior Traffic Commissioner Statutory Document No. 1 (Good Repute)",
    }
    return _attestation(payload)


@mcp.tool()
def prepare_dvsa_visit_pack(
    operator_name: str = "",
    licence_number: str = "",
    expected_visit_date: str = "",
    num_vehicles: int = 1,
) -> dict:
    """Comprehensive 24h-before-DVSA-visit evidence checklist for a full
    O-licence visit (not just tacho). Bundles every document a Vehicle
    Examiner or Traffic Examiner will ask for.
    """
    required_standing = FIN_STANDING_FIRST_VEHICLE_GBP + (
        (max(0, num_vehicles - 1) * FIN_STANDING_EACH_ADDITIONAL_GBP)
    )

    return _attestation({
        "tool": "prepare_dvsa_visit_pack",
        "operator_name": operator_name,
        "licence_number": licence_number,
        "expected_visit_date": expected_visit_date,
        "num_vehicles": num_vehicles,
        "evidence_checklist": {
            "licence_documents": [
                "Original O-licence + variation notices",
                "Vehicle list cross-referenced to VOL (Vehicle Operator Licensing) database",
                "Operating Centre address + planning consent (where required)",
                "TM contract (employed or external) + hours-of-work record",
                "TM CPC certificate (Operator CPC) + CPD log (35h/5yr)",
            ],
            "financial_standing": [
                f"3 months bank statements demonstrating GBP {required_standing:,} availability",
                "Overdraft facility letter (if relied upon)",
                "Latest management accounts",
                "Accountant's letter of comfort",
            ],
            "vehicle_maintenance": [
                "PMI sheets - last 12 months (every vehicle)",
                "PMI forward-planner screenshot (next 6 months)",
                "Brake test reports - every PMI (laden where required)",
                "Roller brake-test prints (filed by VRN)",
                "Annual test (MoT/HGV test) certificates - every vehicle",
                "Tachograph calibration certificates - every vehicle",
                "Driver defect reports + actioned-defect log",
                "Maintenance contract (3rd party) or workshop QC system",
            ],
            "drivers": [
                "Driver list with DCPC expiry + entitlement check (last 90 days)",
                "Driver licence check confirmations",
                "Drivers' hours training records (annual minimum)",
                "Tachograph download cadence log (28-day card / 90-day VU)",
                "Infringement letters issued + signed back",
                "Disciplinary records (drivers' hours)",
                "Working Time Directive records (48h average)",
            ],
            "compliance_systems": [
                "OCRS dashboard screenshot (DVSA portal)",
                "FORS Bronze / Silver / Gold certificates (if applicable)",
                "Earned Recognition data feed (if applicable)",
                "Internal audit programme + last audit report",
                "Independent compliance audit (last 12 months)",
                "Insurance certificates (HGV + Public/Employers Liability)",
            ],
            "trailers": [
                "Trailer list cross-referenced (where third-party trailers used)",
                "Trailer PMI sheets aligned to motive cadence",
            ],
        },
        "common_killer_findings_pre_check": [
            "Missing PMI within 6-week window (or 4-week specialist)",
            "Brake test below 50% laden efficiency",
            "Driver hours infringements not actioned within 14 days",
            "TM not exercising continuous + effective control (hours below benchmark)",
            "Drivers' defect reports not actioned same-day or next morning",
            "Vehicle list / VOL discrepancy (vehicles in use not on licence)",
            "DCPC expired drivers still on rota",
            "Tacho calibration overdue (every 2 years)",
            "Operating Centre overflow / planning breach",
            "Financial standing evidence gap (last 3 months bank)",
        ],
        "if_examiner_asks_for_TM": [
            "TM must be present (or available within 1 hour by phone)",
            "TM has full pack of evidence above",
            "TM diary (last 90 days) showing continuous control",
            "TM signed declaration of other operator commitments",
        ],
        "post_visit_72h": [
            "Examiner issues Maintenance Report / Traffic Report",
            "Operator + TM sign acknowledgement",
            "Generate 14-day corrective action plan",
            "Brief solicitor if any S-marked finding or referral",
        ],
        "reference": "DVSA Operator Compliance Risk Score (OCRS) Guide + Statutory Guidance",
    })


@mcp.tool()
def audit_subcontractor_due_diligence(
    subcontractors: Optional[list] = None,
) -> dict:
    """Vet each subcontractor's O-licence, insurance, MOT compliance, and
    repute. Operator's own O-licence is at risk if a subcontractor is
    non-compliant (Senior TC Statutory Document on Subcontracting).

    Args:
      subcontractors: list of dicts like {
        "name": "AB Haulage Ltd",
        "o_licence_number": "OF1234567",
        "o_licence_valid": True,
        "insurance_expiry": "2026-09-30",
        "last_mot_pass_rate_pct": 92.0,
        "ocrs_band": "green",
        "tm_disqualification_history": False,
        "fors_level": "silver"
      }
    """
    subcontractors = subcontractors or []
    today = date.today()
    results = []
    overall_pass = True

    for sub in subcontractors:
        name = sub.get("name", "UNKNOWN")
        flags = []

        if not sub.get("o_licence_valid", False):
            flags.append("O-licence INVALID or unverified - do not subcontract")
        if not sub.get("o_licence_number"):
            flags.append("Missing O-licence number")

        try:
            ins_exp = date.fromisoformat(sub.get("insurance_expiry", "2000-01-01"))
            days = (ins_exp - today).days
            if days < 0:
                flags.append(f"Insurance EXPIRED ({-days}d ago)")
            elif days < 30:
                flags.append(f"Insurance expires in {days}d - renewal evidence required")
        except Exception:
            flags.append("Insurance expiry not parseable / not provided")

        mot_pct = sub.get("last_mot_pass_rate_pct", 0.0)
        if mot_pct < 75:
            flags.append(f"MoT pass rate {mot_pct}% (< 75%) - vehicle fitness concern")

        ocrs = sub.get("ocrs_band", "unknown").lower()
        if ocrs == "red":
            flags.append("OCRS RED - do not subcontract; operator's repute at risk")
        elif ocrs == "amber":
            flags.append("OCRS Amber - permitted but document due diligence")

        if sub.get("tm_disqualification_history", False):
            flags.append("TM has disqualification history - elevated repute risk")

        verdict = "PASS" if not flags else ("FAIL" if any("INVALID" in f or "RED" in f or "EXPIRED" in f for f in flags) else "WATCH")
        if verdict == "FAIL":
            overall_pass = False

        results.append({
            "name": name,
            "o_licence_number": sub.get("o_licence_number", ""),
            "flags": flags,
            "verdict": verdict,
        })

    payload = {
        "tool": "audit_subcontractor_due_diligence",
        "subcontractors_evaluated": len(subcontractors),
        "results": results,
        "fail_count": sum(1 for r in results if r["verdict"] == "FAIL"),
        "watch_count": sum(1 for r in results if r["verdict"] == "WATCH"),
        "pass_count": sum(1 for r in results if r["verdict"] == "PASS"),
        "overall_pass": overall_pass,
        "advisory": (
            "All subcontractors compliant. Refresh evidence pack every 6 months."
            if overall_pass else
            "FAIL: at least one subcontractor is non-compliant. "
            "Stop using until evidence rectified. Document decision. "
            "Operator's own O-licence repute is on the line."
        ),
        "evidence_to_keep_per_sub": [
            "O-licence copy (current)",
            "Insurance certificate (current + 30 days of expiry)",
            "MOT history extract",
            "OCRS band confirmation",
            "FORS / Earned Recognition (where claimed)",
            "Annual signed declaration of compliance",
        ],
        "reference": "Senior Traffic Commissioner Statutory Guidance on Subcontracting",
    }
    return _attestation(payload)


# ----------------------------------------------------------------------
# Server entry
# ----------------------------------------------------------------------

def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()


# ── MEOK monetization layer (Stripe upgrade · PAYG · pricing) ──────────
# Free tier is zero-config. Upgrade to Pro (unlimited) or pay-as-you-go per call.
import os as _meok_os
MEOK_STRIPE_UPGRADE = "https://buy.stripe.com/5kQ6oJ0xS3ce8sl7ew8k91j"  # Pro (unlimited)
MEOK_PAYG_KEY = _meok_os.environ.get("MEOK_PAYG_KEY", "")  # set to enable PAYG (x402 / ~GBP0.05 per call)
MEOK_PRICING = "https://meok.ai/pricing"


def meok_upsell(tier: str = "free") -> dict:
    """Monetization options for free-tier callers: Pro upgrade, PAYG, or pricing page."""
    if tier != "free":
        return {}
    return {"upgrade_url": MEOK_STRIPE_UPGRADE,
            "payg_enabled": bool(MEOK_PAYG_KEY),
            "pricing": MEOK_PRICING}
