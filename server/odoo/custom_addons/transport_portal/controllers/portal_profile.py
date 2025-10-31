from odoo import http
from odoo.http import request

class PortalProfile(http.Controller):

    @http.route(['/my/profile'], type='http', auth='user', website=True)
    def portal_my_profile(self, **kw):
        user = request.env.user
        partner = user.partner_id
        return request.render("transport_portal.portal_my_profile", {
            'user': user,          # ✅ tambah ni
            'partner': partner,    # optional kalau template guna
        })
