from odoo import http
from odoo.http import request


class PortalContainer(http.Controller):

    # ----------------------------------------------------------
    # List View
    # ----------------------------------------------------------
    @http.route(['/my/containers'], type='http', auth='user', website=True)
    def portal_my_containers(self, **kw):
        containers = request.env['res.container'].sudo().search([])
        return request.render('slot_booking.portal_my_containers', {'containers': containers})

    # ----------------------------------------------------------
    # Create New Container
    # ----------------------------------------------------------
    @http.route(['/my/containers/new'], type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_container_new(self, **post):
        Container = request.env['res.container'].sudo()

        partners = request.env['res.partner'].sudo().search([])
        depots = request.env['res.depot'].sudo().search([])
        yards = request.env['res.yard'].sudo().search([])

        if request.httprequest.method == 'POST':
            vals = {
                'container_number': post.get('container_number'),
                'owner_code': post.get('owner_code'),
                'equipment_category': post.get('equipment_category'),
                'serial_number': post.get('serial_number'),
                'check_digit': post.get('check_digit'),
                'iso_size_type_code': post.get('iso_size_type_code'),
                'container_type': post.get('container_type'),
                'size': post.get('size'),
                'max_gross_weight': post.get('max_gross_weight'),
                'tare_weight': post.get('tare_weight'),
                'remarks': post.get('remarks'),
                'container_owner': int(post.get('container_owner') or 0) or False,
                'depot_id': int(post.get('depot_id') or 0) or False,
                'yard_id': int(post.get('yard_id') or 0) or False,
                'block': int(post.get('block') or 0) or False,
            }
            container = Container.create(vals)
            return request.redirect(f'/my/containers/{container.id}')

        return request.render('slot_booking.portal_container_edit', {
            'container': Container,
            'partners': partners,
            'depots': depots,
            'yards': yards,
            'blocks': yards,  # same model for block
        })

    # ----------------------------------------------------------
    # Edit Existing Container
    # ----------------------------------------------------------
    @http.route(['/my/containers/<int:container_id>'], type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_container_detail(self, container_id, **post):
        container = request.env['res.container'].sudo().browse(container_id)
        if not container.exists():
            return request.redirect('/my/containers')

        partners = request.env['res.partner'].sudo().search([])
        depots = request.env['res.depot'].sudo().search([])
        yards = request.env['res.yard'].sudo().search([])

        if request.httprequest.method == 'POST':
            container.sudo().write({
                'container_number': post.get('container_number'),
                'owner_code': post.get('owner_code'),
                'equipment_category': post.get('equipment_category'),
                'serial_number': post.get('serial_number'),
                'check_digit': post.get('check_digit'),
                'iso_size_type_code': post.get('iso_size_type_code'),
                'container_type': post.get('container_type'),
                'size': post.get('size'),
                'max_gross_weight': post.get('max_gross_weight'),
                'tare_weight': post.get('tare_weight'),
                'remarks': post.get('remarks'),
                'container_owner': int(post.get('container_owner') or 0) or False,
                'depot_id': int(post.get('depot_id') or 0) or False,
                'yard_id': int(post.get('yard_id') or 0) or False,
                'block': int(post.get('block') or 0) or False,
            })
            return request.redirect(f'/my/containers/{container.id}')

        return request.render('slot_booking.portal_container_edit', {
            'container': container,
            'partners': partners,
            'depots': depots,
            'yards': yards,
            'blocks': yards,
        })
