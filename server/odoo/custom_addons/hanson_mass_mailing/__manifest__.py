{
    'name': 'Sale Order Mail Body',
    'version': '1.0',
    'summary': 'Add mail body tab from Mass Mailing to Sale Orders',
    'category': 'Sales',
    'depends': ['sale_management', 'mass_mailing'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}