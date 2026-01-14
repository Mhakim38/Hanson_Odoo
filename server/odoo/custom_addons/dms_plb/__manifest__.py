{
    'name': 'CRM Lead DMS',
    'version': '1.0.0',
    'category': 'CRM',
    'summary': 'Quotation and Contract management for CRM Leads',
    'author': 'Your Company',
    'license': 'LGPL-3',
    'application': False,

    'depends': [
        'crm',
        'mail',   # for chatter / attachments safety
    ],

    'data': [
        # Security
        'security/ir.model.access.csv',

        # DMS model views
        'views/crm_lead_dms_views.xml',

        # Wizard
        'wizard/crm_lead_dms_upload_wizard_view.xml',

        # CRM Lead extensions (buttons, booleans)
        'views/crm_lead_views.xml',
    ],

    'installable': True,
}
