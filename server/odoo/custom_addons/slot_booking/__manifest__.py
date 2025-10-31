# -*- coding: utf-8 -*-
{
    "name": "Slot Booking",
    "summary": "Depot, Yard, Container and Transporter registry for slot booking operations",
    "version": "17.0.1.0.1",
    "category": "Operations/Inventory",
    "author": "Alif Hykal",
    "license": "LGPL-3",
    "depends": ["base", "base_geolocalize", "website"],
    "data": [
        # Security first
        "security/ir.model.access.csv",

        # data
        "data/rot_sequence.xml",
        "data/gatepass_sequence.xml",
        "data/container_stage_data.xml",
        "data/collection_preadvise_sequence.xml",

        # Load views that define actions first (these actions are referenced by menu.xml)
        "views/depot_views.xml",
        "views/yard_views.xml",
        "views/container_maintenance_views.xml",
        "views/container_journey_views.xml",
        "views/container_views.xml",
        "views/transporter_views.xml",
        "views/booking_list_views.xml",
        "views/slot_views.xml",
        "views/criteria_views.xml",

        # QWeb templates for website frontend
        "views/transporter_templates.xml",
        "views/rot_templates.xml",
        "views/portal_container_templates.xml",
        "views/slot_booking_form_template.xml",

        # Now load menus so menu items can reference the actions above and other views can reference menus
        "views/menu.xml",

        # Remaining views and actions
        "views/driver_views.xml",
        "views/vehicle_views.xml",
        "views/trailer_views.xml",
        "views/rot_views.xml",
        "views/collection_preadvise_views.xml",
        "views/gatepass_views.xml",
    ],
    "application": True,
}
