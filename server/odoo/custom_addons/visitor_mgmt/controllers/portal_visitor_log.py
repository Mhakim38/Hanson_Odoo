from odoo import http
from odoo.http import request

class VisitorLogPortal(http.Controller):

    @http.route(['/portal/visitor-log'], type='http', auth="user", website=True)
    def portal_visitor_log(self, **kw):
        """Display the visitor log for the logged-in partner (resident)."""
        partner = request.env.user.partner_id

        # Get visits linked to this partner’s units (owner or resident)
        visits = request.env['estate.visit'].sudo().search([
            '|',
            ('unit_id.owner_id', '=', partner.id),
            ('unit_id.resident_partner_ids', 'in', partner.id)
        ], order='schedule_from desc')

        values = {
            'partner': partner,
            'visits': visits,
        }

        return request.render('visitor_mgmt.portal_visitor_log', values)
