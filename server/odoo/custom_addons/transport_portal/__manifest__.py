{
    'name': 'Transport Portal',
    'version': '1.0',
    'author': 'Novutal DevTeam: Izzati',
    'category': 'Portal',
    'summary': 'Portal view for Transporter, Driver, Vehicle, and Trailer',
    'depends': ['base', 'portal', 'website', 'slot_booking'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/driver_views.xml',
        'views/vehicle_views.xml',
        'views/trailer_views.xml',
        'views/profile_views.xml',
    ],
    'application': True,
    'installable': True,
}
