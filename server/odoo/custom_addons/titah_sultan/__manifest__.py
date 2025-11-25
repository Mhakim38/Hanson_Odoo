{
    'name': 'Pengurusan Titah DYMM Sultan Selangor',
    'version': '1.0',
    'category': 'Custom',
    'summary': 'Modul untuk urus titah, maklum balas, dan laporan tidak laksana',
    'description': """
        Modul ini membolehkan pentadbir merekod titah DYMM Sultan Selangor,
        memantau maklum balas dari agensi, serta melaporkan ketidakpatuhan.
    """,
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/laporan_tidaklaksana_views.xml',
        'views/senarai_titah_views.xml',
        'views/titah_respon_dashboard_views.xml',
        'views/titah_respon_views.xml',
        'views/titah_dashboard_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'titah_sultan/static/src/img/logo.png',
            'titah_sultan/static/src/js/titah_list_header.js',
            'titah_sultan/static/src/js/titah_respon_list.js',
            'titah_sultan/static/src/js/titah_dashboard.js',
            'titah_sultan/static/src/xml/titah_dashboard_template.xml',
        ],
        "web.assets_qweb": [
            "titah_sultan/static/src/xml/titah_dashboard_template.xml",
        ]
    },

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
