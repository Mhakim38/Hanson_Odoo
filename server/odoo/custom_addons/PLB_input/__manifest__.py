{
    'name': 'PLB (CRM) Lead Extension Custom',
    'version': '17.0.1.0',
    'summary': 'Extends CRM Lead with additional business fields and logic',
    'depends': ['crm', 'base'],
    'data': [
        'security/crm_lead_security.xml',
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
    ],
    'installable': True,
    'application': False,
}
