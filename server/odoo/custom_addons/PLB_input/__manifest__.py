{
    'name': 'PLB (CRM) Lead Extension Custom',
    'version': '17.0.1.0',
    'summary': 'Extends CRM Lead with additional business fields and logic',
    'depends': ['crm', 'base', 'crm_port', 'mail', 'hr'],
    'data': [
        'security/crm_lead_security.xml',
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
        'views/mail_activity_schedule_views.xml',
        'views/hr_employee_behavior_views.xml',
    ],
    'installable': True,
    'application': False,
}
