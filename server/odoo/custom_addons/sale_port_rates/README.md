        # sale_port_rates
        Odoo 17 module to add a Port Rates Quotation variant to Sales quotations.
        - Adds `is_port_rate_quotation` boolean on sale.order
        - Adds order line fields: port, validation, export_rate, inclusive
        - Provides form view conditional trees and a PDF report layout

Installation:
        1. Drop this module folder into your Odoo addons path.
        2. Update app list and install 'Sale Port Rates Quotation'.
        3. Create a quotation, toggle 'Port Rates Quotation' in the 'Quotation Type' page.
