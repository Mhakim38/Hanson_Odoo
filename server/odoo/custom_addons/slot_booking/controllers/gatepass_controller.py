from odoo import http
from odoo.http import request


class SlotBookingGatepassController(http.Controller):
    @http.route(['/slot_booking/gatepasses'], type='http', auth='public', website=True)
    def list_gatepasses(self, page=1, limit=12, status='all', **kwargs):
        """Render a list of Gate Pass applications with optional status filter and pagination."""
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

        Gatepass = request.env['res.gatepass'].sudo()
        total = Gatepass.search_count(domain)
        offset = max(0, (page - 1) * limit)
        gatepasses = Gatepass.search(domain, order='application_date desc', limit=limit, offset=offset)

        pager = {
            'page': page,
            'pages': max(1, (total + limit - 1) // limit),
            'limit': limit,
            'total': total,
        }

        return request.render('slot_booking.gatepasses_template', {
            'gatepasses': gatepasses,
            'pager': pager,
            'status': status,
        })

    @http.route(['/slot_booking/gatepasses/new'], type='http', auth='public', website=True, methods=['GET', 'POST'])
    def gatepass_new(self, **post):
        """Display gatepass registration form (GET) and handle creation (POST)."""
        if request.httprequest.method == 'GET':
            containers = request.env['res.container'].sudo().search([], order='container_number asc')
            transporters = request.env['res.transporter'].sudo().search([], order='name asc')
            vehicles = request.env['res.vehicle'].sudo().search([], order='name asc')
            drivers = request.env['res.driver'].sudo().search([], order='name asc')
            preadvises = request.env['res.collection.preadvise'].sudo().search([], order='preadvise_date desc')

            return request.render('slot_booking.gatepass_registration_template', {
                'containers': containers,
                'transporters': transporters,
                'vehicles': vehicles,
                'drivers': drivers,
                'preadvises': preadvises,
            })

        # POST: create the Gate Pass
        vals = {
            'applicant_name': post.get('applicant_name') or False,
            'preadvise_id': int(post.get('preadvise_id')) if post.get('preadvise_id') else False,
            'container_id': int(post.get('container_id')) if post.get('container_id') else False,
            'haulier_id': int(post.get('haulier_id')) if post.get('haulier_id') else False,
            'vehicle_id': int(post.get('vehicle_id')) if post.get('vehicle_id') else False,
            'driver_id': int(post.get('driver_id')) if post.get('driver_id') else False,
            'remarks': post.get('remarks') or False,
        }
        try:
            gp = request.env['res.gatepass'].sudo().create(vals)
            return request.redirect('/slot_booking/gatepasses')
        except Exception as e:
            # On error, re-render the form with error message and previous selections
            containers = request.env['res.container'].sudo().search([], order='container_number asc')
            transporters = request.env['res.transporter'].sudo().search([], order='name asc')
            vehicles = request.env['res.vehicle'].sudo().search([], order='name asc')
            drivers = request.env['res.driver'].sudo().search([], order='name asc')
            preadvises = request.env['res.collection.preadvise'].sudo().search([], order='preadvise_date desc')

            return request.render('slot_booking.gatepass_registration_template', {
                'containers': containers,
                'transporters': transporters,
                'vehicles': vehicles,
                'drivers': drivers,
                'preadvises': preadvises,
                'error': str(e),
                'vals': vals,
            })

