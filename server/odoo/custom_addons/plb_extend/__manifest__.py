{
    'name': 'PLB Extension Custom View',
    'version': '17.0.1.0',
    'summary': 'Extends CRM Lead with additional business fields and logic',
    'depends': ['crm', 'PLB_input', 'base', 'crm_port', 'mail', 'hr'],
    'data': [
        'views/front_views.xml',
    ],
    "assets": {
        "web.assets_backend": [
            "plb_extend/static/src/js/crm_stage_notebook.js",
        ],
    },

    'installable': True,
    'application': False,
}
