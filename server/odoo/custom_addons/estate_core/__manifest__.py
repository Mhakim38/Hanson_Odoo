{
    "name": "Estate Core",
    "version": "17.0.1.0.0",
    "summary": "Core data models for properties, units, partners, and vehicles",
    "depends": ["base", "contacts"],
    "data": [
        "security/ir.model.access.csv",

        "views/estate_property_views.xml",
        "views/estate_unit_views.xml",
        "views/estate_vehicle_views.xml",
        "views/res_partner_views.xml",
        "views/vehicle_form_template.xml",
        "views/portal_property_template.xml",
        "views/estate_menus.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": True
}
