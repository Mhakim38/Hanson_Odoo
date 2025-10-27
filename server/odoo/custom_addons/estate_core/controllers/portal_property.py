from odoo import http
from odoo.http import request

class PortalPropertyController(http.Controller):

    @http.route(['/portal/my-properties'], type='http', auth='user', website=True)
    def portal_my_properties(self, **kwargs):
        user = request.env.user
        partner = user.partner_id

        # Get owned/linked units
        units = partner.estate_unit_ids

        return request.render('estate_core.portal_property_template', {
            'partner': partner,
            'units': units,
        })
