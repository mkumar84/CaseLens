"""Synthetic mixed CaseFile for the CaseLens demo.

Scenario: an internal investigation into vendor-payment irregularities at a
fictional logistics company. 18 artifacts across documents, a device
extraction, and comms — small enough to review in a demo, mixed enough to
require a real triage decision (roughly half are investigatively relevant,
half are routine noise).
"""

CASE_FILE_NAME = "Trussell & Voss Logistics — Q3 Vendor Payment Irregularities"

ARTIFACTS = [
    {
        "source_type": "document",
        "raw_content": (
            "Invoice #INV-88213 from Meridian Freight Partners, dated 2026-06-02, "
            "amount $84,500.00, approved by D. Ostrander (VP Procurement). Line item: "
            "'Q2 warehousing consolidation services.' No PO number referenced. "
            "Vendor bank details changed on file three days prior to invoice date."
        ),
        "metadata": {"filename": "INV-88213.pdf", "date": "2026-06-02"},
    },
    {
        "source_type": "document",
        "raw_content": (
            "Vendor Master File change log: Meridian Freight Partners banking details "
            "updated 2026-05-30 by user 'd.ostrander'. Old account ending 4471, new "
            "account ending 9902. No secondary approval recorded for the change, "
            "though company policy (Finance Policy 4.2) requires dual sign-off for "
            "vendor bank detail changes over $10,000 in annual spend."
        ),
        "metadata": {"filename": "vendor_master_changelog.csv", "date": "2026-05-30"},
    },
    {
        "source_type": "document",
        "raw_content": (
            "Q2 warehousing services contract with Meridian Freight Partners, signed "
            "2024-11-01, term 24 months, scope covers three regional distribution "
            "centers. Standard terms, nothing unusual. Countersigned by Legal."
        ),
        "metadata": {"filename": "meridian_contract_2024.pdf", "date": "2024-11-01"},
    },
    {
        "source_type": "document",
        "raw_content": (
            "Expense report for D. Ostrander, week of 2026-06-01: client dinner "
            "$142.00, taxi $38.00, hotel $210.00. All within policy limits, receipts "
            "attached and legible."
        ),
        "metadata": {"filename": "expense_ostrander_wk22.pdf", "date": "2026-06-05"},
    },
    {
        "source_type": "document",
        "raw_content": (
            "Corporate secretary of state filing lookup: 'Meridian Freight Partners LLC' "
            "registered 2026-04-15, four weeks before the first invoice was submitted. "
            "Registered agent address matches a residential mail-forwarding service. "
            "No prior business history found under this entity name."
        ),
        "metadata": {"filename": "sos_lookup_meridian.pdf", "date": "2026-06-10"},
    },
    {
        "source_type": "document",
        "raw_content": (
            "Q1 all-hands meeting notes: quarterly revenue review, headcount planning "
            "for the Denver distribution center, and a reminder that badge access "
            "cards expire annually. No procurement or vendor items discussed."
        ),
        "metadata": {"filename": "q1_allhands_notes.docx", "date": "2026-01-20"},
    },
    {
        "source_type": "document",
        "raw_content": (
            "IT helpdesk ticket #4471: employee requesting a monitor stand replacement "
            "for their desk. Resolved same day. Unrelated to procurement systems."
        ),
        "metadata": {"filename": "helpdesk_4471.pdf", "date": "2026-03-11"},
    },
    {
        "source_type": "document",
        "raw_content": (
            "Facilities work order: HVAC filter replacement scheduled for the third "
            "floor east wing, week of 2026-04-06. Routine maintenance, no exceptions "
            "noted."
        ),
        "metadata": {"filename": "facilities_wo_2204.pdf", "date": "2026-04-06"},
    },
    {
        "source_type": "device",
        "raw_content": (
            "Device extraction (D. Ostrander, company phone) — location log: device "
            "was at [residential address, not a company facility] during business "
            "hours (10:14-11:52) on 2026-05-30, the same day the Meridian vendor "
            "banking details were changed from a desktop session logged as originating "
            "from the office network."
        ),
        "metadata": {"device_id": "phone-ostrander-01", "date": "2026-05-30"},
    },
    {
        "source_type": "device",
        "raw_content": (
            "Device extraction (D. Ostrander, company phone) — banking app "
            "'QuickPay Business' installed 2026-05-28 and opened four times between "
            "2026-05-28 and 2026-06-02. App is not on the company's approved software "
            "list for procurement staff."
        ),
        "metadata": {"device_id": "phone-ostrander-01", "date": "2026-05-28"},
    },
    {
        "source_type": "device",
        "raw_content": (
            "Device extraction (D. Ostrander, company phone) — step count and "
            "screen-time summary for 2026-06-15: 6,204 steps, 3h42m screen time. "
            "No investigative relevance."
        ),
        "metadata": {"device_id": "phone-ostrander-01", "date": "2026-06-15"},
    },
    {
        "source_type": "device",
        "raw_content": (
            "Device extraction (shared warehouse tablet) — barcode scanner app usage "
            "log, routine inbound/outbound scans for 2026-06-03, all counts reconcile "
            "with the WMS system."
        ),
        "metadata": {"device_id": "tablet-wh-07", "date": "2026-06-03"},
    },
    {
        "source_type": "comms",
        "raw_content": (
            "Text message, D. Ostrander to unsaved number ending 0092, 2026-05-29 "
            "22:41: 'Send me the new account info tonight, need to load it before "
            "the invoice goes in tomorrow. Don't cc finance on this one, I'll handle "
            "the paperwork.'"
        ),
        "metadata": {"channel": "sms", "date": "2026-05-29", "sender": "d.ostrander"},
    },
    {
        "source_type": "comms",
        "raw_content": (
            "Text message, unsaved number ending 0092 to D. Ostrander, 2026-05-29 "
            "22:47: 'Sent. Same split as last time, 60/40, my cut goes to the usual "
            "account.'"
        ),
        "metadata": {"channel": "sms", "date": "2026-05-29", "sender": "unknown-0092"},
    },
    {
        "source_type": "comms",
        "raw_content": (
            "Email, D. Ostrander to AP team, 2026-06-02, subject 'Please expedite "
            "INV-88213': 'This one's time-sensitive for the vendor, can we get it "
            "through today without the usual PO matching step? I'll sort out the "
            "PO retroactively.'"
        ),
        "metadata": {"channel": "email", "date": "2026-06-02", "sender": "d.ostrander"},
    },
    {
        "source_type": "comms",
        "raw_content": (
            "Email, AP team to D. Ostrander, 2026-06-02, subject 'RE: Please expedite "
            "INV-88213': 'Processed as requested, flagging that PO matching was "
            "skipped per your approval.'"
        ),
        "metadata": {"channel": "email", "date": "2026-06-02", "sender": "ap-team"},
    },
    {
        "source_type": "comms",
        "raw_content": (
            "Email thread, D. Ostrander to team distribution list, 2026-04-18, "
            "subject 'Team lunch Friday': coordinating a team lunch order, no "
            "business-sensitive content."
        ),
        "metadata": {"channel": "email", "date": "2026-04-18", "sender": "d.ostrander"},
    },
    {
        "source_type": "comms",
        "raw_content": (
            "Text message, D. Ostrander to spouse, 2026-06-08: 'Picking up the kids "
            "at 5, running a bit late.' Personal, no investigative relevance."
        ),
        "metadata": {"channel": "sms", "date": "2026-06-08", "sender": "d.ostrander"},
    },
]
