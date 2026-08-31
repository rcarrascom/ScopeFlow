"""
One-time generator for mock_data.py. Not imported by the running app - run
this script whenever the demo dataset needs to be regenerated, then commit
the resulting mock_data.py alongside main.py.

A purely synthetic dataset: every client, collaborator, project, and note is
fictional, invented for this project. No real clients, no real business data.
"""
import json
import random
from datetime import datetime, timedelta

random.seed(7)

# --- Roster ------------------------------------------------------------
LEAD_NAME = "Alex Rivera"  # the freelancer/consultant running the business
COLLABORATOR_NAMES = [
    "Jordan Blake", "Sami Okafor", "Priya Desai", "Tomas Lindqvist", "Wren Castillo",
]

MOCK_COLLABORATORS = []
_uid = 1
def _fake_person_id(n):
    return f"usr{n:015d}"

MOCK_COLLABORATORS.append({
    "Id": _fake_person_id(_uid), "Name": LEAD_NAME,
    "Email": LEAD_NAME.lower().replace(" ", ".") + "@scopeflow-demo.com",
    "_role": "lead",
})
_uid += 1
for name in COLLABORATOR_NAMES:
    MOCK_COLLABORATORS.append({
        "Id": _fake_person_id(_uid), "Name": name,
        "Email": name.lower().replace(" ", ".") + "@scopeflow-demo.com",
        "_role": "collaborator",
    })
    _uid += 1

LEAD_USER = MOCK_COLLABORATORS[0]
COLLABORATOR_USERS = [u for u in MOCK_COLLABORATORS if u["_role"] == "collaborator"]

# --- Clients -------------------------------------------------------------
CLIENT_NAMES = [
    "Northfield Bakery Co.", "Alderwood Dental Group", "Pixel & Pine Studio",
    "Harbor City Realty", "Kindred Roots Nonprofit", "Summit Ridge Fitness",
    "Blue Anchor Brewing", "Cobalt Consulting Partners", "Willow & Wren Events",
    "Marrow Coffee Roasters", "Nomad Trail Outfitters", "Clearwater Legal Group",
    "Second Story Bookshop", "Terra Firma Landscaping", "Lantern Row Marketing",
    "Foothill Veterinary Clinic", "Amber Grove Winery", "Cedarline Architecture",
    "Driftwood Design Co.", "Ivy & Iron Fabrication", "Meadowlight Yoga Studio",
    "Rustic Table Catering", "Bright Current Media", "Copperfield Financial",
    "Sable Peak Outdoor Gear",
]

SERVICE_TYPES = ["Website Design", "Brand Strategy", "Marketing Audit", "Ongoing Retainer", "App Development", "Content Strategy"]
LEAD_SOURCES = ["Referral", "Cold Outreach", "Inbound - Website", "Platform (Upwork/Fiverr)", "Past Client"]
STAGE_WEIGHTS = [
    ("1 - Lead", 6), ("2 - Discovery Call", 9), ("3 - Proposal Sent", 8),
    ("4 - Scope Call", 5), ("5 - Negotiation", 4),
    ("6 - Closed Won", 20), ("7 - Closed Lost", 28),
]
STAGE_POOL = [s for s, w in STAGE_WEIGHTS for _ in range(w)]
OPEN_STAGE_POOL = [s for s, w in STAGE_WEIGHTS if "Closed" not in s for _ in range(w)]
CLOSED_STAGE_POOL = [s for s, w in STAGE_WEIGHTS if "Closed" in s for _ in range(w)]

CONTRACT_STATUSES = ["Not Sent", "Sent", "Signed"]
CLOSED_REASONS_WON = ["Scope and budget aligned quickly", "Strong referral, low friction", "Rebooked past client"]
CLOSED_REASONS_LOST = ["Budget too low for scope", "Client went with an in-house hire", "Timeline mismatch", "Went quiet after proposal"]

NEXT_STEP_SAMPLES = [
    "Send revised proposal reflecting reduced scope.",
    "Confirm kickoff date once deposit clears.",
    "Follow up after client reviews the discovery notes.",
    "Schedule a scope call to firm up deliverables.",
]

# Qualification checklist - an original framework for this project, not a
# reproduction of any external sales methodology.
QUALIFICATION_FIELDS = [
    ("Budget_Confirmed__c", "Budget Confirmed"),
    ("Decision_Maker_Identified__c", "Decision Maker Identified"),
    ("Timeline_Defined__c", "Timeline Defined"),
    ("Success_Criteria_Defined__c", "Success Criteria Defined"),
    ("Competing_Priorities_Noted__c", "Competing Priorities Noted"),
]
QUAL_SAMPLES = {
    "Budget_Confirmed__c": ["Verbal range confirmed: $3k-6k.", "Client has a hard cap set by finance.", "Budget not yet discussed."],
    "Decision_Maker_Identified__c": ["Owner is the sole decision maker.", "Needs sign-off from a business partner.", "Marketing lead decides, owner rubber-stamps."],
    "Timeline_Defined__c": ["Wants to launch before their seasonal rush.", "No hard deadline, flexible.", "Tied to an event date - firm deadline."],
    "Success_Criteria_Defined__c": ["Success = more inbound leads from the site.", "Success = consistent posting cadence.", "Not yet defined - flagged for scope call."],
    "Competing_Priorities_Noted__c": ["Comparing quotes from two other freelancers.", "Considering an in-house hire instead.", "No competing options mentioned."],
}

RISK_VALUES = ["Green", "Yellow", "Red"]
CALL_STATUSES = ["Not Scheduled", "Scheduled", "Completed"]
BLOCKER_TYPES = ["None", "Budget", "Scope Creep", "Client Responsiveness", "Timeline Conflict"]
OUTCOMES = ["Scope Confirmed", "Scope Reduced", "Needs Follow-up", "Client Went Quiet", "N/A - Not Yet Held"]
PROPOSAL_STATUSES = ["Draft", "Sent", "Revised", "Accepted"]

CALL_NOTE_SAMPLES = [
    "Walked through deliverables page by page - client aligned on scope.",
    "Client wants to trim scope to fit budget - revising proposal.",
    "No-show, rescheduling for next week.",
    "Great call, added an upsell for ongoing maintenance retainer.",
    "Client still deciding between us and another freelancer.",
]


def fake_id(prefix, n):
    pad_width = 18 - len(prefix)
    return f"{prefix}{n:0{pad_width}d}"


def rand_date(days_back_min, days_back_max):
    return datetime(2026, 8, 27) - timedelta(days=random.randint(days_back_min, days_back_max))


def build_project(idx, client_name, collaborators, stage, forced_close_date=None):
    project_id = fake_id("prj_demo", idx)
    is_closed = "Closed" in stage
    created = rand_date(15, 300)

    if forced_close_date is not None:
        target_delivery = forced_close_date
        if created >= target_delivery:
            created = target_delivery - timedelta(days=random.randint(20, 80))
    else:
        target_delivery = created + timedelta(days=random.randint(20, 120))

    target_start = created + timedelta(days=random.randint(5, 30))
    deal_value = round(random.choice([0] + [random.uniform(800, 18000) for _ in range(6)]), 2)
    # Always populated, mirroring a freelancer who prices in an ongoing
    # retainer add-on for nearly every engagement.
    retainer_value = round(random.uniform(150, 3000), 2)

    qual_vals = {}
    fill_count = random.randint(1, len(QUALIFICATION_FIELDS))
    for api_name, _label in random.sample(QUALIFICATION_FIELDS, fill_count):
        qual_vals[api_name] = random.choice(QUAL_SAMPLES[api_name])

    service_type = random.choice(SERVICE_TYPES)
    project = {
        "Id": project_id,
        "Name": f"{client_name} - {service_type}",
        "ClientId": fake_id("cli_demo", idx),
        "Client": {"Name": client_name},
        "LeadCollaboratorId": LEAD_USER["Id"],
        "LeadCollaborator": {"Name": LEAD_USER["Name"]},
        "ServiceType": service_type,
        "DealValue": deal_value,
        "RetainerValue__c": retainer_value,
        "Probability": 100 if "Won" in stage else (0 if "Lost" in stage else random.choice([10, 25, 50, 75, 90])),
        "TargetStartDate": target_start.strftime("%Y-%m-%d"),
        "TargetDeliveryDate": target_delivery.strftime("%Y-%m-%d"),
        "Stage": stage,
        "NextStep": random.choice(NEXT_STEP_SAMPLES),
        "CreatedDate": created.strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
        "LastModifiedDate": (created + timedelta(days=random.randint(1, 45))).strftime("%Y-%m-%dT%H:%M:%S.000+0000"),
        "LeadSource": random.choice(LEAD_SOURCES),
        "ContractStatus": "Signed" if "Closed" in stage and "Won" in stage else random.choice(CONTRACT_STATUSES),
        "ClosedReason__c": random.choice(CLOSED_REASONS_WON if "Won" in stage else CLOSED_REASONS_LOST) if is_closed else None,
        **qual_vals,
    }

    scope_call_id = fake_id("scp_demo", idx)
    call_status = "Completed" if is_closed else random.choice(CALL_STATUSES)
    primary_collab = collaborators[0]
    scope_call = {
        "Id": scope_call_id,
        "ProjectId": project_id,
        "AssignedCollaboratorId": primary_collab["Id"],
        "AssignedCollaborator": {"Name": primary_collab["Name"]},
        "CallStatus": call_status,
        "RiskLevel": random.choice(RISK_VALUES),
        "CallNotes": random.choice(CALL_NOTE_SAMPLES) if call_status == "Completed" else "",
        "CallDate": (created + timedelta(days=random.randint(3, 15))).strftime("%Y-%m-%d") if call_status != "Not Scheduled" else None,
        "EstimatedHours": random.choice([None, round(random.uniform(4, 80), 1)]),
        "BlockerType": "None" if random.random() < 0.6 else random.choice(BLOCKER_TYPES[1:]),
        "Outcome": random.choice(OUTCOMES[:-1]) if call_status == "Completed" else "N/A - Not Yet Held",
        "ProposalStatus": "Accepted" if "Won" in stage else random.choice(PROPOSAL_STATUSES),
    }

    project["ScopeCalls__r"] = {"records": [scope_call]}
    project["Collaborators__r"] = {"records": [{"CollaboratorId": c["Id"], "Collaborator": {"Name": c["Name"]}} for c in collaborators]}
    return project


projects = []
idx = 1

# The default logged-in view (Alex Rivera, the lead) should show a healthy,
# never-sparse pipeline: 20 projects, 8 currently open.
open_stages = [random.choice(OPEN_STAGE_POOL) for _ in range(8)]
closed_stages = [random.choice(CLOSED_STAGE_POOL) for _ in range(12)]
default_stages = open_stages + closed_stages
random.shuffle(default_stages)

for stage in default_stages:
    client = random.choice(CLIENT_NAMES)
    shared = random.random() < 0.2
    collabs = [LEAD_USER, random.choice(COLLABORATOR_USERS)] if shared else [LEAD_USER]
    projects.append(build_project(idx, client, collabs, stage))
    idx += 1

# Broader roster of projects credited to other collaborators, so Look Up
# Collaborator has real, varied pipelines to show.
for _ in range(35):
    client = random.choice(CLIENT_NAMES)
    stage = random.choice(STAGE_POOL)
    shared = random.random() < 0.15
    collabs = random.sample(COLLABORATOR_USERS, 2) if shared else [random.choice(COLLABORATOR_USERS)]
    projects.append(build_project(idx, client, collabs, stage))
    idx += 1

# Forecast coverage for the rest of the calendar year - force a handful of
# still-open projects (never "Closed") into each remaining month.
for month in (9, 10, 11, 12):
    for _ in range(3):
        forced_delivery = datetime(2026, month, random.randint(1, 27))
        client = random.choice(CLIENT_NAMES)
        stage = random.choice(OPEN_STAGE_POOL)
        shared = random.random() < 0.2
        collabs = [LEAD_USER, random.choice(COLLABORATOR_USERS)] if shared else [LEAD_USER]
        projects.append(build_project(idx, client, collabs, stage, forced_close_date=forced_delivery))
        idx += 1
    for _ in range(2):
        forced_delivery = datetime(2026, month, random.randint(1, 27))
        client = random.choice(CLIENT_NAMES)
        stage = random.choice(OPEN_STAGE_POOL)
        collabs = [random.choice(COLLABORATOR_USERS)]
        projects.append(build_project(idx, client, collabs, stage, forced_close_date=forced_delivery))
        idx += 1

project_ids = [p["Id"] for p in projects]
assert len(project_ids) == len(set(project_ids)), "Duplicate Project Ids generated"
collab_ids = [u["Id"] for u in MOCK_COLLABORATORS]
assert len(collab_ids) == len(set(collab_ids)), "Duplicate Collaborator Ids generated"

QUALIFICATION_META = [{"name": n, "label": l} for n, l in QUALIFICATION_FIELDS]
PROJECT_FIELD_META = {
    "Name": {"label": "Project", "type": "string"},
    "ServiceType": {"label": "Service Type", "type": "string"},
    "DealValue": {"label": "Deal Value", "type": "currency"},
    "RetainerValue__c": {"label": "Retainer Value (Monthly)", "type": "currency"},
    "Probability": {"label": "Probability (%)", "type": "percent"},
    "TargetStartDate": {"label": "Target Start Date", "type": "date"},
    "TargetDeliveryDate": {"label": "Target Delivery Date", "type": "date"},
    "Stage": {"label": "Stage", "type": "string"},
    "NextStep": {"label": "Next Step", "type": "string"},
    "LeadSource": {"label": "Lead Source", "type": "string"},
    "ContractStatus": {"label": "Contract Status", "type": "string"},
    "ClosedReason__c": {"label": "Closed Reason", "type": "string"},
}
SCOPE_CALL_FIELD_META = {
    "CallStatus": {"label": "Call Status", "type": "string"},
    "RiskLevel": {"label": "Risk Level", "type": "string"},
    "CallNotes": {"label": "Call Notes", "type": "string"},
    "CallDate": {"label": "Call Date", "type": "date"},
    "EstimatedHours": {"label": "Estimated Hours", "type": "number"},
    "BlockerType": {"label": "Blocker Type", "type": "string"},
    "Outcome": {"label": "Outcome", "type": "string"},
    "ProposalStatus": {"label": "Proposal Status", "type": "string"},
}
SCOPE_CALL_PICKLISTS = {
    "CallStatus": CALL_STATUSES,
    "RiskLevel": RISK_VALUES,
    "BlockerType": BLOCKER_TYPES,
    "Outcome": OUTCOMES,
    "ProposalStatus": PROPOSAL_STATUSES,
}


def _write_as_json_literal(f, varname, value):
    raw = json.dumps(value, indent=2)
    assert "'''" not in raw, f"{varname}: payload contains a triple-quote sequence"
    f.write(f"{varname} = _json.loads(r'''\n{raw}\n''')\n\n")


with open("mock_data.py", "w") as f:
    f.write('"""Auto-generated by generate_mock_data.py - do not hand-edit; regenerate instead."""\n')
    f.write("import json as _json\n\n")
    _write_as_json_literal(f, "MOCK_COLLABORATORS", MOCK_COLLABORATORS)
    _write_as_json_literal(f, "MOCK_PROJECTS", projects)
    _write_as_json_literal(f, "PROJECT_FIELD_META", PROJECT_FIELD_META)
    _write_as_json_literal(f, "SCOPE_CALL_FIELD_META", SCOPE_CALL_FIELD_META)
    _write_as_json_literal(f, "QUALIFICATION_META", QUALIFICATION_META)
    _write_as_json_literal(f, "SCOPE_CALL_PICKLISTS", SCOPE_CALL_PICKLISTS)

print(f"Generated {len(projects)} projects, {len(MOCK_COLLABORATORS)} collaborators.")
