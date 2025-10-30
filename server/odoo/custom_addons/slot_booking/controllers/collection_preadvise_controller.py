from odoo import http
from odoo.http import request


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

            return request.render('slot_booking.collection_preadvise_registration_template', {
                'depots': depots,
                'transporters': transporters,
                'vehicles': vehicles,
                'drivers': drivers,
                'containers': containers,
            })

        # POST: create the preadvise
        vals = {
            'depot_id': int(post.get('depot_id')) if post.get('depot_id') else False,
            'location': post.get('location') or False,
            'transporter_id': int(post.get('transporter_id')) if post.get('transporter_id') else False,
            'readiness_status': post.get('readiness_status') or 'pending',
            'remarks': post.get('remarks') or False,
        }
        try:
            p = request.env['res.collection.preadvise'].sudo().create(vals)
            # If user selected a specific container in the form, replace auto-filled lines
            cid = post.get('container_id')
            if cid:
                try:
                    cid = int(cid)
                    container = request.env['res.container'].sudo().browse(cid)
                    if container and container.exists():
                        line_vals = (0, 0, {
                            'container_id': container.id,
                            'depot_id': container.depot_id.id if container.depot_id else False,
                            'yard_id': container.yard_id.id if hasattr(container, 'yard_id') and container.yard_id else False,
                            'block': getattr(container, 'block', False),
                            'status': container.stage_id.name if container.stage_id else False,
                        })
                        # replace existing lines with single selected container
                        p.write({'line_ids': [(5, 0, 0), line_vals]})
                except ValueError:
                    # ignore invalid container id, continue
                    pass

            return request.redirect('/slot_booking/preadvises')
        except Exception as e:
            # Re-render form on error with previous selections
            depots = request.env['res.depot'].sudo().search([], order='name asc')
            transporters = request.env['res.transporter'].sudo().search([], order='name asc')
            vehicles = request.env['res.vehicle'].sudo().search([], order='name asc')
            drivers = request.env['res.driver'].sudo().search([], order='name asc')
            containers = request.env['res.container'].sudo().search([('stage_id.name', '=', 'Available')], order='container_number asc')

            return request.render('slot_booking.collection_preadvise_registration_template', {
                'depots': depots,
                'transporters': transporters,
                'vehicles': vehicles,
                'drivers': drivers,
                'containers': containers,
                'error': str(e),
                'vals': vals,
            })
