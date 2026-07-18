"""Synthetic mixed CaseFiles for the CaseLens demo.

Three scenarios, each a small mixed case file (documents + device extraction
+ comms) sized for a demo review, with roughly half the artifacts
investigatively relevant and half routine noise — enough to require a real
triage decision rather than an obvious one.
"""

CASES = [
    {
        "name": "Trussell & Voss Logistics — Q3 Vendor Payment Irregularities",
        "artifacts": [
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
                "source_type": "device",
                "raw_content": (
                    "SMS thread, D. Ostrander to unsaved number ending 8834, 2026-05-29 22:14: "
                    "'Send the new account details tonight, want it in before month end close.' "
                    "Reply 22:19: 'Done, confirm when it clears.'"
                ),
                "metadata": {"extraction_source": "mobile", "date": "2026-05-29"},
            },
            {
                "source_type": "device",
                "raw_content": (
                    "Call log entry: outgoing call from D. Ostrander's device to unsaved number "
                    "ending 8834, 2026-05-29, duration 4m12s, 21:58."
                ),
                "metadata": {"extraction_source": "mobile", "date": "2026-05-29"},
            },
            {
                "source_type": "comms",
                "raw_content": (
                    "Email, D. Ostrander to AP Team, 2026-06-01 08:02, subject 'Expedite "
                    "Meridian payment': 'Please push INV-88213 through today, vendor is "
                    "threatening to pause the Q3 lane and I don't want to deal with the fallout.'"
                ),
                "metadata": {"platform": "email", "date": "2026-06-01"},
            },
            {
                "source_type": "comms",
                "raw_content": (
                    "Email, AP Clerk to D. Ostrander, 2026-06-01 09:15: 'This invoice has no PO "
                    "and the bank details just changed. Standard process needs a second "
                    "approval for that. Can you confirm?' Reply 09:41: 'Approved, just process it, "
                    "I'll deal with the paperwork after.'"
                ),
                "metadata": {"platform": "email", "date": "2026-06-01"},
            },
            {
                "source_type": "document",
                "raw_content": (
                    "Q1 warehousing invoice from Meridian Freight Partners, #INV-81002, "
                    "$79,200.00, matched to PO-4471, standard 30-day terms, paid on time, no "
                    "discrepancies noted."
                ),
                "metadata": {"filename": "INV-81002.pdf", "date": "2026-03-15"},
            },
            {
                "source_type": "comms",
                "raw_content": (
                    "Slack, #procurement-team, 2026-04-10: routine thread about warehouse space "
                    "utilization reporting for the quarterly ops review, no financial content."
                ),
                "metadata": {"platform": "slack", "date": "2026-04-10"},
            },
            {
                "source_type": "document",
                "raw_content": (
                    "Org chart update memo, Procurement division, 2026-02-01, noting D. "
                    "Ostrander's promotion to VP Procurement effective 2026-01-15."
                ),
                "metadata": {"filename": "org_update_feb2026.pdf", "date": "2026-02-01"},
            },
            {
                "source_type": "device",
                "raw_content": (
                    "Calendar entry, D. Ostrander, 2026-05-29, 'Dinner — M.F.' 19:30, private "
                    "location note, no other attendees listed."
                ),
                "metadata": {"extraction_source": "mobile", "date": "2026-05-29"},
            },
            {
                "source_type": "comms",
                "raw_content": (
                    "Email, D. Ostrander to spouse, 2026-06-03: family scheduling logistics, "
                    "unrelated to case."
                ),
                "metadata": {"platform": "email", "date": "2026-06-03"},
            },
            {
                "source_type": "document",
                "raw_content": (
                    "Standard Finance Policy 4.2 excerpt: vendor bank detail changes exceeding "
                    "$10,000 in annual spend require dual sign-off from Procurement and "
                    "Finance Control before the next payment cycle."
                ),
                "metadata": {"filename": "finance_policy_4.2.pdf", "date": "2023-08-01"},
            },
            {
                "source_type": "device",
                "raw_content": (
                    "Photo metadata: image captured 2026-05-29 20:02, geolocation matches a "
                    "restaurant three blocks from Meridian Freight Partners' registered office."
                ),
                "metadata": {"extraction_source": "mobile", "date": "2026-05-29"},
            },
            {
                "source_type": "comms",
                "raw_content": (
                    "Slack, D. Ostrander (DM to self / saved notes), 2026-05-30: 'need to loop "
                    "finance control on the account change before it looks like I skipped it.'"
                ),
                "metadata": {"platform": "slack", "date": "2026-05-30"},
            },
            {
                "source_type": "document",
                "raw_content": (
                    "AP processing log: INV-88213 processed and paid 2026-06-02, 14:03, no "
                    "second-approval field completed, exception flag suppressed by user "
                    "override code 'PROC-VP-OVERRIDE'."
                ),
                "metadata": {"filename": "ap_processing_log.csv", "date": "2026-06-02"},
            },
            {
                "source_type": "comms",
                "raw_content": (
                    "Email, IT Helpdesk to all staff, 2026-05-28: scheduled maintenance window "
                    "notice, unrelated to case."
                ),
                "metadata": {"platform": "email", "date": "2026-05-28"},
            },
            {
                "source_type": "document",
                "raw_content": (
                    "Vendor onboarding record for Meridian Freight Partners, original entry "
                    "2019-03-12, no prior banking changes on file until 2026-05-30."
                ),
                "metadata": {"filename": "vendor_onboarding_2019.pdf", "date": "2019-03-12"},
            },
        ],
    },
    {
        "name": "Vantage Robotics — Departing Employee IP Review",
        "artifacts": [
            {
                "source_type": "document",
                "raw_content": (
                    "Resignation letter, R. Chen (Senior Controls Engineer), submitted "
                    "2026-04-18, effective 2026-05-02, two-week notice, joining a competitor "
                    "named in the letter as 'Ferro Dynamics.'"
                ),
                "metadata": {"filename": "chen_resignation.pdf", "date": "2026-04-18"},
            },
            {
                "source_type": "device",
                "raw_content": (
                    "USB device connection log, R. Chen's workstation, 2026-04-19 23:41, "
                    "unregistered removable storage device connected for 47 minutes outside "
                    "normal working hours."
                ),
                "metadata": {"extraction_source": "endpoint", "date": "2026-04-19"},
            },
            {
                "source_type": "device",
                "raw_content": (
                    "File access log: 214 files from the 'ARM-Controller-v4' repository "
                    "accessed and copied to removable media between 23:44 and 00:12 on "
                    "2026-04-19/20, including files R. Chen had not opened in over six months."
                ),
                "metadata": {"extraction_source": "endpoint", "date": "2026-04-19"},
            },
            {
                "source_type": "document",
                "raw_content": (
                    "Signed IP and Confidentiality Agreement, R. Chen, dated at hire "
                    "2022-08-01, standard terms covering all controller firmware and design "
                    "documentation as confidential."
                ),
                "metadata": {"filename": "chen_ip_agreement_2022.pdf", "date": "2022-08-01"},
            },
            {
                "source_type": "comms",
                "raw_content": (
                    "Email, R. Chen to personal Gmail address, 2026-04-19 23:52, subject "
                    "'backup', three attachments matching filenames from the "
                    "ARM-Controller-v4 repository access log."
                ),
                "metadata": {"platform": "email", "date": "2026-04-19"},
            },
            {
                "source_type": "comms",
                "raw_content": (
                    "Slack DM, R. Chen to former colleague J. Patel (already departed to Ferro "
                    "Dynamics), 2026-04-10: 'still ironing out start date, will have more to "
                    "share on the tech side once I'm settled in.'"
                ),
                "metadata": {"platform": "slack", "date": "2026-04-10"},
            },
            {
                "source_type": "document",
                "raw_content": (
                    "Exit interview notes, HR, 2026-05-01: R. Chen stated departure was for "
                    "'better growth opportunities,' declined to name new employer during the "
                    "interview despite it being named in the resignation letter."
                ),
                "metadata": {"filename": "exit_interview_notes.docx", "date": "2026-05-01"},
            },
            {
                "source_type": "device",
                "raw_content": (
                    "Badge access log: R. Chen entered the building 2026-04-19 at 22:58, "
                    "outside their normal working pattern (typical hours 08:30-17:30), no "
                    "calendar entry or approved after-hours work request on file."
                ),
                "metadata": {"extraction_source": "badge_system", "date": "2026-04-19"},
            },
            {
                "source_type": "document",
                "raw_content": (
                    "Standard equipment return checklist, R. Chen, completed 2026-05-01, all "
                    "company hardware returned, laptop hard drive imaged per standard offboarding "
                    "procedure before wipe."
                ),
                "metadata": {"filename": "equipment_return_chen.pdf", "date": "2026-05-01"},
            },
            {
                "source_type": "comms",
                "raw_content": (
                    "Email, R. Chen to manager, 2026-04-05: routine handover planning for "
                    "ongoing projects, professional tone, no red flags."
                ),
                "metadata": {"platform": "email", "date": "2026-04-05"},
            },
            {
                "source_type": "document",
                "raw_content": (
                    "Performance review, R. Chen, Q1 2026: rated 'exceeds expectations,' no "
                    "disciplinary history on file, considered a high performer."
                ),
                "metadata": {"filename": "chen_q1_review.pdf", "date": "2026-03-15"},
            },
            {
                "source_type": "comms",
                "raw_content": (
                    "Slack, #engineering-general, 2026-04-15: R. Chen's farewell message to "
                    "the team, warm and generic, no relevant content."
                ),
                "metadata": {"platform": "slack", "date": "2026-04-15"},
            },
            {
                "source_type": "device",
                "raw_content": (
                    "Cloud storage upload log: personal Dropbox account linked to R. Chen's "
                    "work laptop shows a 1.2GB upload completed 2026-04-20 00:09, six minutes "
                    "after the Gmail attachment send."
                ),
                "metadata": {"extraction_source": "endpoint", "date": "2026-04-20"},
            },
        ],
    },
    {
        "name": "Northbridge Rail Maintenance — Falsified Inspection Records",
        "artifacts": [
            {
                "source_type": "document",
                "raw_content": (
                    "Track inspection report, Segment 14-B, dated 2026-03-02, signed off by "
                    "inspector T. Falk, status 'pass, no defects noted.' Weather log for that "
                    "date shows the segment was inaccessible due to flooding until 2026-03-04."
                ),
                "metadata": {"filename": "inspection_14b_mar2.pdf", "date": "2026-03-02"},
            },
            {
                "source_type": "device",
                "raw_content": (
                    "GPS log, inspection vehicle assigned to T. Falk, 2026-03-02: no location "
                    "data recorded near Segment 14-B; vehicle remained at the depot the entire "
                    "shift."
                ),
                "metadata": {"extraction_source": "vehicle_telematics", "date": "2026-03-02"},
            },
            {
                "source_type": "comms",
                "raw_content": (
                    "Text message, T. Falk to shift supervisor M. Reyes, 2026-03-02 06:15: "
                    "'segment's flooded, can't get out there today, what do you want me to put "
                    "down.' Reply 06:22: 'just log it as pass, we can't miss the quarterly "
                    "target again, we'll catch it next cycle.'"
                ),
                "metadata": {"platform": "sms", "date": "2026-03-02"},
            },
            {
                "source_type": "document",
                "raw_content": (
                    "Regional weather bulletin, 2026-03-01 to 2026-03-04: sustained flooding "
                    "across the corridor including Segment 14-B, track access suspended by "
                    "regional operations."
                ),
                "metadata": {"filename": "weather_bulletin_mar2026.pdf", "date": "2026-03-01"},
            },
            {
                "source_type": "document",
                "raw_content": (
                    "Quarterly inspection compliance summary submitted to regulator, Q1 2026: "
                    "100% of scheduled segments reported passed, including Segment 14-B, signed "
                    "by M. Reyes as shift supervisor of record."
                ),
                "metadata": {"filename": "q1_compliance_summary.pdf", "date": "2026-04-01"},
            },
            {
                "source_type": "device",
                "raw_content": (
                    "Photo metadata attached to the Segment 14-B inspection report: image "
                    "EXIF timestamp reads 2026-01-14, three months before the report date, "
                    "suggesting a reused photo from an earlier, unrelated inspection."
                ),
                "metadata": {"extraction_source": "document_metadata", "date": "2026-01-14"},
            },
            {
                "source_type": "comms",
                "raw_content": (
                    "Email, M. Reyes to T. Falk, 2026-02-20: routine shift scheduling for the "
                    "upcoming inspection cycle, no relevant content."
                ),
                "metadata": {"platform": "email", "date": "2026-02-20"},
            },
            {
                "source_type": "document",
                "raw_content": (
                    "Incident report, 2026-03-19: minor derailment on Segment 14-B attributed "
                    "to rail wear that a passed inspection should have flagged three weeks "
                    "earlier."
                ),
                "metadata": {"filename": "incident_report_mar19.pdf", "date": "2026-03-19"},
            },
            {
                "source_type": "device",
                "raw_content": (
                    "Badge access log, depot facility, 2026-03-02: T. Falk clocked in at 06:00 "
                    "and clocked out at 14:05, consistent with a full shift spent at the depot "
                    "rather than in the field."
                ),
                "metadata": {"extraction_source": "badge_system", "date": "2026-03-02"},
            },
            {
                "source_type": "document",
                "raw_content": (
                    "T. Falk's training certification record: current and up to date on all "
                    "required inspection qualifications as of 2026-01-05."
                ),
                "metadata": {"filename": "falk_certifications.pdf", "date": "2026-01-05"},
            },
            {
                "source_type": "comms",
                "raw_content": (
                    "Slack, #depot-14-crew, 2026-03-03: general shift-change chatter about the "
                    "flooding delaying multiple segments, no specific admission of falsified "
                    "records."
                ),
                "metadata": {"platform": "slack", "date": "2026-03-03"},
            },
            {
                "source_type": "document",
                "raw_content": (
                    "Segment 14-B inspection history, prior four quarters: three passes, one "
                    "flagged for minor wear and remediated on schedule — no prior pattern of "
                    "irregularities before this report."
                ),
                "metadata": {"filename": "segment_14b_history.pdf", "date": "2025-12-01"},
            },
        ],
    },
]

# Backward-compatible aliases for any code still importing the old names —
# both now point at the first scenario in CASES.
CASE_FILE_NAME = CASES[0]["name"]
ARTIFACTS = CASES[0]["artifacts"]
