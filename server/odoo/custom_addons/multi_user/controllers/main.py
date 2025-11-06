from datetime import date
from odoo import http
from odoo.http import request

class CustomPortalHome(http.Controller):

    @http.route(['/my', '/my/home'], type='http', auth='user', website=True)
    def custom_portal_home(self, **kwargs):
        user = request.env.user

        if user.user_type == 'guard':
            return request.render('multi_user.portal_home_guard', {
                'today': date.today(),
                'user': user,
            })

        if user.user_type == 'resident':
            return request.render('multi_user.portal_home_resident', {
                'today': date.today(),
                'user': user,
            })

        # Kalau bukan guard/resident, bagi error supaya senang detect
        return request.not_found()
