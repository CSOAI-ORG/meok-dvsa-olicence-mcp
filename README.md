<!-- mcp-name: io.github.CSOAI-ORG/meok-dvsa-olicence-mcp -->
[![MCP Scorecard: 84/100](https://img.shields.io/badge/proofof.ai-84%2F100-5b21b6)](https://proofof.ai/scorecard/meok-dvsa-olicence-mcp.html)

# meok-dvsa-olicence-mcp

[![PyPI](https://img.shields.io/badge/PyPI-1.0.0-blue)](https://pypi.org/project/meok-dvsa-olicence-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-1.3.0+-green)](https://modelcontextprotocol.io)

> UK DVSA **Operator Licence audit** + **Traffic Commissioner Public Inquiry brief** generator. The compliance toolkit the **44,660 UK O-licence holders** wish their TM had at hand. By **MEOK AI Labs**.

## Why this exists

UK general haulage runs on the **O-licence** — granted by the Traffic Commissioner under the *Goods Vehicles (Licensing of Operators) Act 1995*. Lose it and the business is over.

Recent Traffic Commissioner public decisions (2024-25) include:

- **Steven Davies** — disqualified from holding an O-licence **for 4 years** (Senior TC decision)
- **Maurice Murphy** — disqualified **indefinitely** as TM and operator
- **Mark Rowland** — disqualified **12 months**, repute lost
- **Tom Kingston** — disqualified following maintenance investigation
- **Cheryl James** — TM repute lost, revocation upheld
- **Robert Ogilvie** — disqualified, repute lost, multiple PG9s

A single Public Inquiry typically costs **£8,000-£25,000** in legal fees, drives insurance premiums up **£20,000-£100,000/yr**, and can end the business in licence revocation. The wedge of avoidance is enormous.

This MCP gives **named Transport Managers, owner-operators, and transport solicitors** the callable toolkit for:

- Comprehensive O-licence audit across all 11 statutory areas
- Financial standing check (£8,400 first vehicle + £4,600 each additional, 2026 rates)
- TM continuous + effective control test (Senior TC Statutory Guidance)
- PMI cadence audit (6-week or 4-week specialist windows)
- **Public Inquiry defence-brief generator** — the existential wedge
- PI risk forecasting (weeks_to_likely_PI)
- Repute scoring (Good / At Risk / Lost)
- 24h-before-DVSA-visit evidence pack
- Subcontractor due diligence

## Install

```bash
pip install meok-dvsa-olicence-mcp
```

## Claude Desktop config

```json
{
  "mcpServers": {
    "dvsa-olicence": {
      "command": "meok-dvsa-olicence-mcp"
    }
  }
}
```

## Tools (9)

| Tool | Use case |
|------|----------|
| `audit_o_licence_compliance` | Full 11-area audit, scored + ranked top 5 risks. |
| `check_financial_standing` | £8,400 + £4,600/vehicle rate check, surplus/deficit. |
| `check_tm_continuous_effective_control` | Hours-per-week against fleet size, per Senior TC guidance. |
| `audit_pmi_compliance` | 6-week (or 4-week specialist) PMI gap detection. |
| `generate_public_inquiry_brief` | **The wedge** — 8-section PI defence brief + estimated costs. |
| `forecast_pi_risk` | Risk band + top 3 triggers + weeks-to-likely-PI. |
| `check_repute_indicators` | Convictions, prohibitions, DVSA referrals, TM disqualifications. |
| `prepare_dvsa_visit_pack` | Comprehensive 24h evidence checklist (not just tacho). |
| `audit_subcontractor_due_diligence` | Subcontractor O-licence, insurance, MOT, repute. |

## Pricing

- **Free** — MIT self-host
- **Starter** — £79/mo (signed attestations + email support)
- **Pro** — £249/mo (multi-user dashboard + PI brief auto-update)
- **Fleet** — £799/mo (50+ vehicles, audit-export, solicitor-handoff, SLA)

[Subscribe Pro 79/mo](https://www.csoai.org/checkout) · [Talk to Nick](mailto:nicholas@meok.ai)

## Regulatory basis

- *Goods Vehicles (Licensing of Operators) Act 1995*
- Senior Traffic Commissioner's **Statutory Guidance + Statutory Directives 1-12**
- DVSA **OCRS Guide** (Operator Compliance Risk Score)
- Public Inquiries — Traffic Commissioner public decisions register
- *Goods Vehicles (Licensing of Operators) Regulations 1995* (as amended)
- *Drivers' Hours Rules* (EU 561/2006 retained + GB Domestic Hours)
- DVSA Guide to Maintaining Roadworthiness (PMI cadence)

## Sign your responses (production)

```bash
export MEOK_HMAC_SECRET="your-secret"
meok-dvsa-olicence-mcp
```

Every tool response returns an HMAC-SHA256 signature for audit-trail evidence — defensible in a Public Inquiry.

## Companion MCPs

Part of the **MEOK Haulage** stack on haulage.app:

- `meok-tacho-audit-mcp` — Tacho + OCRS + driver hours
- `meok-ev-recall-transport-mcp` — ADR Class 9 for damaged/recalled EVs
- `meok-dvsa-olicence-mcp` — this one (O-licence + PI brief)

## License

MIT (c) 2026 Nicholas Templeman / MEOK AI Labs · [haulage.app](https://haulage.app)
