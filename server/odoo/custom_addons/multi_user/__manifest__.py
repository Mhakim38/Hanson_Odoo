{
    'name': 'Custom Portal Home',
    'version': '1.0',
    'author': 'Izzati',
    'category': 'Website',
    'summary': 'Different portal homepages for Resident and Guard users',
    'depends': ['portal', 'website', 'visitor_mgmt', 'estate_core'],
    'data': [
        'views/res_users_views.xml',
        'views/home_page.xml',
        'views/register_visit_visitor.xml',
    ],
    'installable': True,
    'application': False,
}
