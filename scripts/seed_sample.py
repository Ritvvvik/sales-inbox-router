#!/usr/bin/env python3
import json

def sample(n=250):
    subjects=["RFP for analytics platform","Quick demo request","Sponsorship deadline tomorrow","Invoice payment overdue","Reseller partnership","Out of Office","B2B Growth Weekly"]
    bodies=["Tender for enterprise software. Budget Rs. 25 lakhs. Last date 12 Aug 2026.","Can we get a demo next week? Nothing urgent.","Gold sponsorship for India SaaS Summit is ₹4,00,000. Need confirmation by tomorrow EOD.","Invoice INV-2026 for Rs. 1,18,000 incl GST is overdue.","We want to explore reseller or technology integration partnership.","I am out of office until 14th August with limited access.","Issue #212. Unsubscribe"]
    return [{"email_id":f"em_{i+1:05d}","thread_id":f"th_{i//2+1:04d}","message_index":i%2,"from_name":"Sample Sender","from_email":f"sender{i}@example.com","to":"sales@company.com","cc":[],"subject":subjects[i%len(subjects)],"body":bodies[i%len(bodies)],"received_at":"2026-08-01T09:14:22+05:30","attachments":[],"is_reply":bool(i%2)} for i in range(n)]

if __name__ == "__main__":
    print(json.dumps(sample(), indent=2, ensure_ascii=False))
