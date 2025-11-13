{
    'name': 'CRM Port',
    'version': '1.0',
    'summary': 'Manage ports (airports, seaports, landports, etc.)',
    'category': 'CRM',
    'author': 'Your Name',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/port_views.xml',
    ],
    'installable': True,
    'application': False,
}