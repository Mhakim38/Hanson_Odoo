{
    "name": "Guard Patrol",
    "version": "17.0.1.0.0",
    "summary": "Patrol routes, checkpoints, tours, logs, and incidents",
    "depends": ["base", "estate_core", "visitor_mgmt", "mail", "hr", "website"],
    "data": [
        "security/ir.model.access.csv",
        "views/patrol_views.xml",
        'views/estate_guard_views.xml',
        'views/portal_templates.xml',
        'views/portal_not_found.xml',
        "views/menus.xml"
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": True
}
