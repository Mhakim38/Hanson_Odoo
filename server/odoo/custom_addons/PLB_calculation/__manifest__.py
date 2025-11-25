{
    'name': 'PLB Calculation (CRM Revenue Pivot)',
    'version': '17.0.1.0',
    'summary': 'Adds AR/MAR/RR/CF calculations on CRM Leads and a Pivot Report',
    'depends': ['crm', 'PLB_input'],
    'data': [
        'security/ir.model.access.csv',
        'views/plb_crm_lead_pivot_views.xml',
        'views/plb_crm_lead_tree_views.xml',
        'views/plb_partner_report_views.xml',
    ],
    'installable': True,
    'application': False,
}
