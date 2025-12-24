{
    'name': 'PLB Dashboard',
    'version': '17.0.1.0',
    'depends': ['web', 'crm', 'PLB_input', 'hr'],
    'assets': {
        'web.assets_backend': [
            'plb_dashboard/static/src/js/dashboard.js',
            'plb_dashboard/static/src/js/kpi.js',
        ],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/target_kpi_views.xml',
        'views/dashboard_plb.xml',
    ],
    'installable': True,
}
