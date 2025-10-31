from odoo import http
from odoo.http import request

class PortalTrailer(http.Controller):

    @http.route(['/my/trailers'], type='http', auth='user', website=True)
    def portal_my_trailers(self, **kw):
        user = request.env.user
        transporter = request.env['res.transporter'].sudo().search([('name', '=', user.partner_id.id)], limit=1)

        search_query = kw.get('search', '').strip()  # ambil nilai search
        domain = [('transporter_id', '=', transporter.id)]

        if search_query:
            domain += ['|', ('name', 'ilike', search_query), ('trailer_plate_no', 'ilike', search_query)]

        trailers = request.env['res.trailer'].sudo().search(domain)

        return request.render("transport_portal.portal_my_trailers", {
            'trailers': trailers,
            'transporter': transporter,
            'search': search_query,  # supaya input field boleh retain nilai
        })

    # ===============================
    # FORM PAGE (CREATE / EDIT)
    # ===============================
    @http.route(['/my/trailer', '/my/trailer/<int:trailer_id>'], type='http', auth='user', website=True)
    def portal_my_trailer_form(self, trailer_id=None, **kw):
        user = request.env.user
        Trailer = request.env['res.trailer'].sudo()
        trailer = Trailer.browse(trailer_id) if trailer_id else None

        transporter = request.env['res.transporter'].sudo().search([
            ('name', '=', user.partner_id.id)
        ], limit=1)

        containers = request.env['res.container'].sudo().search([])

        return request.render('transport_portal.portal_create_trailer', {
            'trailer': trailer,
            'transporter': transporter,
            'containers': containers,
        })

    # ===============================
    # SAVE (CREATE / UPDATE)
    # ===============================
    @http.route(['/my/trailer/save'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_save_trailer(self, **post):
        user = request.env.user

        transporter = request.env['res.transporter'].sudo().search([
            ('name', '=', user.partner_id.id)
        ], limit=1)

        vals = {
            'name': post.get('name'),
            'trailer_plate_no': post.get('trailer_plate_no'),
            'trailer_capacity': post.get('trailer_capacity'),
            'container_id': int(post.get('container_id')) if post.get('container_id') else False,
            'insurance_expiry': post.get('insurance_expiry'),
            'trailer_permit': post.get('trailer_permit'),
            'transporter_id': transporter.id,
        }

        Trailer = request.env['res.trailer'].sudo()

        if post.get('trailer_id'):
            trailer = Trailer.browse(int(post['trailer_id']))
            if trailer.exists():
                trailer.write(vals)
        else:
            Trailer.create(vals)

        return request.redirect('/my/trailers')

