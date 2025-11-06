from odoo import http
from odoo.http import request
from datetime import datetime


class EstateVisitorController(http.Controller):

    # 🟩 Form utama Guard daftar pelawat
    @http.route(['/guard/visitor'], type='http', auth='user', website=True)
    def guard_visitor_form(self, **kw):
        all_hosts = request.env['res.partner'].sudo().search([('is_company', '=', False)], order='name')
        return request.render('multi_user.guard_visitor_form', {
            'all_hosts': all_hosts,
            'error': kw.get('error'),
        })

    # 🟦 Submit pelawat
    @http.route(['/guard/visitor/submit'], type='http', auth='user', website=True, csrf=True)
    def guard_visitor_submit(self, **post):
        Visitor = request.env['estate.visitor'].sudo()

        name = post.get('name')
        id_type = post.get('id_type')
        id_number = post.get('id_number')
        phone = post.get('phone')
        host_id = post.get('host_id')
        notes = post.get('notes')

        if not name or not id_number or not host_id:
            return request.redirect_query('/guard/visitor', {'error': 'Please fill all required fields.'})

        visitor = Visitor.create({
            'name': name,
            'id_type': id_type,
            'id_number': id_number,
            'phone': phone,
            'host_id': int(host_id),
            'notes': notes,
        })

        return request.render('multi_user.guard_visitor_thanks', {
            'visitor': visitor,
        })

    # 🟨 Papar QR (public view)
    @http.route(['/visitor/info/<string:qr_token>'], type='http', auth='public', website=True)
    def visitor_info_qr(self, qr_token=None):
        visitor = request.env['estate.visitor'].sudo().search([('qr_token', '=', qr_token)], limit=1)
        if not visitor:
            return request.render('multi_user.visitor_not_found')

        return request.render('multi_user.visitor_info_public', {
            'visitor': visitor,
        })
