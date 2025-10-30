from odoo import http
from odoo.http import request


class SlotBookingROTController(http.Controller):
    @http.route(['/slot_booking/rots'], type='http', auth='public', website=True)
    def list_rots(self, page=1, limit=12, status='all', **kwargs):
        """Render a list of ROTs with optional status filter and pagination."""
        try:
            page = int(page)
        except Exception:
            page = 1
        try:
            limit = int(limit)
        except Exception:
            limit = 12

        domain = []
        if status and status != 'all':
            domain.append(('status', '=', status))

        Rot = request.env['res.rot'].sudo()
        total = Rot.search_count(domain)
        offset = max(0, (page - 1) * limit)
        rots = Rot.search(domain, order='rot_date desc', limit=limit, offset=offset)

        pager = {
            'page': page,
            'pages': max(1, (total + limit - 1) // limit),
            'limit': limit,
            'total': total,
        }

        return request.render('slot_booking.rots_template', {
            'rots': rots,
            'pager': pager,
            'status': status,
        })

    @http.route(['/slot_booking/rots/new'], type='http', auth='public', website=True, methods=['GET', 'POST'])
    def rot_new(self, **post):
        """Display registration fsorm (GET) and handle creation (POST)."""
        if request.httprequest.method == 'GET':
            transporters = request.env['res.transporter'].sudo().search([], order='name asc')
            vehicles = request.env['res.vehicle'].sudo().search([], order='name asc')
            drivers = request.env['res.driver'].sudo().search([], order='name asc')
            trailers = request.env['res.trailer'].sudo().search([], order='name asc')
            # The res.container model uses 'container_number' as the record name; order by that field
            containers = request.env['res.container'].sudo().search([], order='container_number asc')
            return request.render('slot_booking.rot_registration_template', {
                'transporters': transporters,
                'vehicles': vehicles,
                'drivers': drivers,
                'trailers': trailers,
                'containers': containers,
            })

        # POST: create the ROT
        vals = {
            'gate_pass_ref': post.get('gate_pass_ref') or False,
            'gate_pass_request_date': post.get('gate_pass_request_date') or False,
            'transporter_id': int(post.get('transporter_id')) if post.get('transporter_id') else False,
            'vehicle_id': int(post.get('vehicle_id')) if post.get('vehicle_id') else False,
            'trailer_id': int(post.get('trailer_id')) if post.get('trailer_id') else False,
            'driver_id': int(post.get('driver_id')) if post.get('driver_id') else False,
            'container_id': int(post.get('container_id')) if post.get('container_id') else False,
            'remarks': post.get('remarks') or False,
        }
        try:
            rot = request.env['res.rot'].sudo().create(vals)
            # Redirect to the ROT list after successful creation
            return request.redirect('/slot_booking/rots')
        except Exception as e:
            # On error, re-render the form with an error message and previously selected values
            transporters = request.env['res.transporter'].sudo().search([], order='name asc')
            vehicles = request.env['res.vehicle'].sudo().search([], order='name asc')
            drivers = request.env['res.driver'].sudo().search([], order='name asc')
            trailers = request.env['res.trailer'].sudo().search([], order='name asc')
            containers = request.env['res.container'].sudo().search([], order='container_number asc')
            return request.render('slot_booking.rot_registration_template', {
                'transporters': transporters,
                'vehicles': vehicles,
                'drivers': drivers,
                'trailers': trailers,
                'containers': containers,
                'error': str(e),
                'vals': vals,
            })
