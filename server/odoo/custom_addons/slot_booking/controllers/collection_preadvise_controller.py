from odoo import http
from odoo.http import request
import json


class SlotBookingPreadviseController(http.Controller):
    @http.route(['/slot_booking/preadvises'], type='http', auth='public', website=True)
    def list_preadvises(self, page=1, limit=12, publish_status='all', **kwargs):
        """Render a list of Collection Pre-advise records with optional status filter and pagination."""
        try:
            page = int(page)
        except Exception:
            page = 1
        try:
            limit = int(limit)
        except Exception:
            limit = 12

        domain = []
        if publish_status and publish_status != 'all':
            domain.append(('publish_status', '=', publish_status))

        Preadvise = request.env['res.collection.preadvise'].sudo()
        total = Preadvise.search_count(domain)
        offset = max(0, (page - 1) * limit)
        preadvises = Preadvise.search(domain, order='preadvise_date desc', limit=limit, offset=offset)

        pager = {
            'page': page,
            'pages': max(1, (total + limit - 1) // limit),
            'limit': limit,
            'total': total,
        }

        return request.render('slot_booking.collection_preadvises_template', {
            'preadvises': preadvises,
            'pager': pager,
            'publish_status': publish_status,
        })

    @http.route(['/slot_booking/preadvises/new'], type='http', auth='public', website=True, methods=['GET', 'POST'])
    def preadvise_new(self, **post):
        """Display registration form (GET) and handle creation (POST)."""
        if request.httprequest.method == 'GET':
            depots = request.env['res.depot'].sudo().search([], order='name asc')
            transporters = request.env['res.transporter'].sudo().search([], order='name asc')
            vehicles = request.env['res.vehicle'].sudo().search([], order='name asc')
            drivers = request.env['res.driver'].sudo().search([], order='name asc')
            # Only show containers that are currently available
            containers = request.env['res.container'].sudo().search([('stage_id.name', '=', 'Available')], order='container_number asc')
            yards = request.env['res.yard'].sudo().search([], order='name asc')

            return request.render('slot_booking.collection_preadvise_registration_template', {
                'depots': depots,
                'transporters': transporters,
                'vehicles': vehicles,
                'drivers': drivers,
                'containers': containers,
                'yards': yards,
            })

        # POST: create the preadvise
        vals = {
            'depot_id': int(post.get('depot_id')) if post.get('depot_id') else False,
            'location': post.get('location') or False,
            'transporter_id': int(post.get('transporter_id')) if post.get('transporter_id') else False,
            'readiness_status': post.get('readiness_status') or 'pending',
            'remarks': post.get('remarks') or False,
        }

        # Validate line_data before creating record
        line_data_json = post.get('line_data')
        valid_line_vals = []
        if line_data_json:
            try:
                raw_lines = json.loads(line_data_json)
                seen_containers = set()
                for i, ln in enumerate(raw_lines):
                    # Validate container_id present and integer
                    cid = ln.get('container_id')
                    if not cid:
                        raise ValueError(f"Line {i+1}: missing container selection")
                    try:
                        cid = int(cid)
                    except Exception:
                        raise ValueError(f"Line {i+1}: invalid container id")
                    container = request.env['res.container'].sudo().browse(cid)
                    if not container or not container.exists():
                        raise ValueError(f"Line {i+1}: container not found (id={cid})")
                    # Check availability: accept if stage is False or name == 'Available'
                    if container.stage_id and container.stage_id.name != 'Available':
                        raise ValueError(f"Line {i+1}: container {container.container_number} is not Available")
                    # Prevent duplicate container lines
                    if cid in seen_containers:
                        raise ValueError(f"Line {i+1}: duplicate container {container.container_number}")
                    seen_containers.add(cid)
                    # Prepare line tuple for write
                    valid_line_vals.append((0, 0, {
                        'container_id': cid,
                        'depot_id': int(ln.get('depot_id')) if ln.get('depot_id') else False,
                        'yard_id': int(ln.get('yard_id')) if ln.get('yard_id') else False,
                        'block': ln.get('block') or False,
                        'status': ln.get('status') or (container.stage_id.name if container.stage_id else False),
                        'booking_ref': ln.get('booking_ref') or False,
                    }))
            except ValueError as ve:
                # validation error: re-render form with message
                error = str(ve)
                depots = request.env['res.depot'].sudo().search([], order='name asc')
                transporters = request.env['res.transporter'].sudo().search([], order='name asc')
                vehicles = request.env['res.vehicle'].sudo().search([], order='name asc')
                drivers = request.env['res.driver'].sudo().search([], order='name asc')
                containers = request.env['res.container'].sudo().search([('stage_id.name', '=', 'Available')], order='container_number asc')
                yards = request.env['res.yard'].sudo().search([], order='name asc')
                return request.render('slot_booking.collection_preadvise_registration_template', {
                    'depots': depots,
                    'transporters': transporters,
                    'vehicles': vehicles,
                    'drivers': drivers,
                    'containers': containers,
                    'yards': yards,
                    'error': error,
                    'vals': vals,
                })
            except Exception:
                # generic parse error
                depots = request.env['res.depot'].sudo().search([], order='name asc')
                transporters = request.env['res.transporter'].sudo().search([], order='name asc')
                vehicles = request.env['res.vehicle'].sudo().search([], order='name asc')
                drivers = request.env['res.driver'].sudo().search([], order='name asc')
                containers = request.env['res.container'].sudo().search([('stage_id.name', '=', 'Available')], order='container_number asc')
                yards = request.env['res.yard'].sudo().search([], order='name asc')
                return request.render('slot_booking.collection_preadvise_registration_template', {
                    'depots': depots,
                    'transporters': transporters,
                    'vehicles': vehicles,
                    'drivers': drivers,
                    'containers': containers,
                    'yards': yards,
                    'error': 'Invalid line data',
                    'vals': vals,
                })

        try:
            p = request.env['res.collection.preadvise'].sudo().create(vals)
            # If validated lines are present, write them (replace auto-filled lines)
            if valid_line_vals:
                p.write({'line_ids': [(5, 0, 0)] + valid_line_vals})

            return request.redirect('/slot_booking/preadvises')
        except Exception as e:
            # Re-render form on error with previous selections
            depots = request.env['res.depot'].sudo().search([], order='name asc')
            transporters = request.env['res.transporter'].sudo().search([], order='name asc')
            vehicles = request.env['res.vehicle'].sudo().search([], order='name asc')
            drivers = request.env['res.driver'].sudo().search([], order='name asc')
            containers = request.env['res.container'].sudo().search([('stage_id.name', '=', 'Available')], order='container_number asc')
            yards = request.env['res.yard'].sudo().search([], order='name asc')

            return request.render('slot_booking.collection_preadvise_registration_template', {
                'depots': depots,
                'transporters': transporters,
                'vehicles': vehicles,
                'drivers': drivers,
                'containers': containers,
                'yards': yards,
                'error': str(e),
                'vals': vals,
            })
