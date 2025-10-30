# -*- coding: utf-8 -*-
{
    "name": "Slot Booking",
    "summary": "Depot, Yard, Container and Transporter registry for slot booking operations",
    "version": "17.0.1.0.1",
    "category": "Operations/Inventory",
    "author": "Alif Hykal",
    "license": "LGPL-3",
    "depends": ["base", "base_geolocalize"],
    "data": [
        # Security first
        "security/ir.model.access.csv",

        #data
        "data/container_stage_data.xml",
        "data/rot_sequence.xml",
        "data/collection_preadvise_sequence.xml",
        "data/gatepass_sequence.xml",

        # Views and actions first (so menus can find them)
        "views/depot_views.xml",
        "views/yard_views.xml",
        "views/container_journey_views.xml",
        "views/container_maintenance_views.xml",
        "views/container_views.xml",
        "views/transporter_views.xml",
        "views/driver_views.xml",
        "views/vehicle_views.xml",
        "views/trailer_views.xml",
        "views/booking_list_views.xml",
        "views/slot_views.xml",
        "views/criteria_views.xml",
        "views/rot_views.xml",
        "views/collection_preadvise_views.xml",
        "views/gatepass_views.xml",

        # Menus last (they reference the actions above)
        "views/menu.xml",
    ],
    "application": True,
}
