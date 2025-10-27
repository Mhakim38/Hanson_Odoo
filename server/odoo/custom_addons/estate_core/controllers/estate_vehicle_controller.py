from odoo import http
from odoo.http import request

class EstateVehicleController(http.Controller):

    @http.route(['/estate/vehicle'], type='http', auth='user', website=True)
    def vehicle_form(self, **kwargs):
        """Display vehicle registration form with user's linked units"""
        partner = request.env.user.partner_id
        units = partner.estate_unit_ids
        vehicles = request.env['estate.vehicle'].sudo().search([('host_id', '=', partner.id)])

        return request.render('estate_core.vehicle_form_template', {
            'units': units,
            'vehicles': vehicles or []

        })

    @http.route(['/estate/vehicle/submit'], type='http', auth='user', website=True, methods=['POST'])
    def vehicle_form_submit(self, **post):
        """Handle vehicle registration submission"""
        try:
            partner = request.env.user.partner_id
            unit_id = post.get('unit_id')
            plate_no = post.get('plate_no')
            make = post.get('make')
            model = post.get('model')
            color = post.get('color')

            if not unit_id or not plate_no:
                raise ValueError("Please fill all required fields.")

            request.env['estate.vehicle'].sudo().create({
                'unit_id': int(unit_id),
                'host_id': partner.id,
                'plate_no': plate_no,
                'make': make,
                'model': model,
                'color': color,
            })

            return request.render('estate_core.vehicle_form_thanks', {
                'plate_no': plate_no,
                'host_name': partner.name,
            })

        except Exception as e:
            partner = request.env.user.partner_id
            units = partner.estate_unit_ids
            vehicles = request.env['estate.vehicle'].sudo().search([('host_id', '=', partner.id)])
            return request.render('estate_core.vehicle_form_template', {
                'error': str(e),
                'units': units,
                'vehicles': vehicles,
            })
