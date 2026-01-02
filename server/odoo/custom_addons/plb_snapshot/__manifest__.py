{
    "name": "CRM Lead Weekly Snapshot",
    "version": "1.1",
    "summary": "Automatically create weekly snapshots of CRM Leads",
    "depends": ["crm"],
    "data": [
        "security/ir.model.access.csv",
        "views/lead_snapshot_views.xml",
        "data/cron.xml",
    ],
    "installable": True,
    "application": False,
}
