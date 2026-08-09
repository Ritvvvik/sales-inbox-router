from backend.models import Email
from backend.routing import route_email


def make_email(subject: str, body: str, received_at: str = "2026-08-01T09:14:22+05:30") -> Email:
    return Email(
        email_id="em_x",
        thread_id="th_x",
        message_index=0,
        from_name="Sender",
        from_email="sender@example.com",
        to="sales@company.com",
        cc=[],
        subject=subject,
        body=body,
        received_at=received_at,
        attachments=[],
        is_reply=False,
    )


def test_pr_substring_does_not_turn_enterprise_rfp_into_triage():
    decision = route_email(make_email(
        "RFP - Enterprise Document Management System",
        "Meridian Steel invites proposals for an enterprise DMS covering 1,200 users. "
        "Indicative budget is Rs. 25 lakhs. Proposals must reach us by 12th August 2026.",
    ))
    assert decision.assignee_id == "u_aarti"
    assert decision.category == "enterprise_rfp"
    assert decision.deal_value_inr == 2500000


def test_pr_substring_does_not_break_psu_tender_or_alliance():
    psu = route_email(make_email(
        "Tender Notice No. BHEL/PROC/2026/0847",
        "Bharat Heavy Electricals Limited invites bids for analytics software licences. "
        "Estimated value: Rs. 6,50,000. Last date for bid submission: 03-08-2026, 1700 hrs IST.",
    ))
    assert psu.assignee_id == "u_aarti"
    assert psu.category == "enterprise_rfp"

    alliance = route_email(make_email(
        "Partnership discussion",
        "We're a Salesforce implementation partner across MEA with 40+ enterprise clients. "
        "We'd like to explore reselling your platform or a technical integration.",
    ))
    assert alliance.assignee_id == "u_karan"
    assert alliance.category == "alliances"


def test_money_parser_prefers_currency_units_over_plain_user_counts():
    decision = route_email(make_email(
        "Need product for dealer network",
        "Bhai, humko aapka product chahiye for our dealer network. Around 150 users honge. "
        "Budget approx 1.2 cr allocated hai for this FY. Thoda jaldi, board review 20th ko hai.",
        "2026-08-05T09:00:00+05:30",
    ))
    assert decision.assignee_id == "u_aarti"
    assert decision.category == "enterprise_rfp"
    assert decision.deal_value_inr == 12000000
