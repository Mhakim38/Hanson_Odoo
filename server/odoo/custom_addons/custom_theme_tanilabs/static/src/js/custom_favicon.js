
odoo.define('custom_theme_tanilabs.custom_theme_tanilabs', function (require) {
    'use strict';

    const AbstractAction = require('web.AbstractAction');
    const core = require('web.core');

    const CustomFavicon = AbstractAction.extend({
        start: function () {
            const company = odoo.session_info.user_context.allowed_company_ids[0];
            const rpc = require('web.rpc');

            // Fetch company data
            rpc.query({
                model: 'res.company',
                method: 'search_read',
                args: [[['id', '=', company]], ['favicon', 'website_title']],
            }).then(function (companies) {
                if (companies.length > 0) {
                    const company = companies[0];

                    // Update favicon
                    if (company.favicon) {
                        const link = document.querySelector("link[rel~='icon']");
                        if (!link) {
                            link = document.createElement('link');
                            link.rel = 'icon';
                            document.getElementsByTagName('head')[0].appendChild(link);
                        }
                        link.href = 'data:image/x-icon;base64,' + company.favicon;
                    }

                    // Update title
                    if (company.website_title) {
                        document.title = company.website_title;
                    }
                }
            });
        },
    });

    core.action_registry.add('custom_theme_tanilabs.custom_theme_tanilabs', CustomFavicon);
});
