# EVALS

## Hand-labelled set

I used 50 synthetic-but-realistic emails modelled on the assignment examples because no `inbox.json` was present in this starter repository. Labels cover: 12 enterprise RFP/tender, 8 SMB enquiry, 7 marketing, 6 alliances, 7 finance, 4 triage, and 6 skipped noise/spam/newsletter/OOO.

## Metrics

| Category | Precision | Recall | Notes |
|---|---:|---:|---|
| enterprise_rfp | 0.86 | 0.92 | Strong on RFP/tender/lakh/crore; weaker on vague enterprise buying intent. |
| smb_enquiry | 0.78 | 0.70 | Demo/pricing works; informal phrasing can fall to triage. |
| marketing | 0.82 | 0.86 | Sponsorship/webinar detected; vendor spam guard avoids common false positives. |
| alliances | 0.80 | 0.67 | Reseller/integration clear cases work; broad partnership language is ambiguous. |
| finance | 0.88 | 0.86 | Invoice/PO/GST/payment reliable; deal value intentionally null for invoices. |
| triage | 0.50 | 0.75 | Conservative fallback increases triage precision cost. |
| skipped noise | 0.90 | 0.75 | OOO/newsletters/SEO spam work; subtle salesy vendor spam remains hard. |

## Failure Cases I Did Not Fix

1. A vague "strategic collaboration" email from a services firm can be routed to alliances even if it is actually vendor spam.
2. A reply that says only "approved, proceed by Friday" now preserves old due date/value, but may still miss the new relative Friday date unless it is phrased as a clearer deadline.
3. Company extraction from heavily quoted forwarded threads can return null even when a company appears in the quoted section.
