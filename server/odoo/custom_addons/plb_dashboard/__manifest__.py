{
    'name': 'PLB Dashboard',
    'version': '17.0.1.0',
    'depends': ['web', 'crm', 'PLB_input'],
    'assets': {
        'web.assets_backend': [
            'plb_dashboard/static/src/js/dashboard.js',
        ],
    },
    'data': [
        'views/dashboard_plb.xml',
    ],
    'installable': True,
}
