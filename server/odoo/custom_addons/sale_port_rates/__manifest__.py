{
    'name': 'Sale Port Rates Quotation',
    'version': '17.0.1.1.7',
    'summary': 'Adds Port Rates Quotation type to Sales with custom order lines and report',
    'description': 'Provide a Port Rates Quotation boolean on quotations, custom order lines (port, validation, export_rate, inclusive) and a special PDF layout.',
    'category': 'Sales',
    'author': 'Alif Hykal',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'hanson_mass_mailing', 'hanson_letter_t3'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'report/sale_order_report.xml',
        'report/hide_address_layout.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
