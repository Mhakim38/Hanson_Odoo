from odoo import http
from odoo.http import request
from odoo.exceptions import UserError


class PortalVehicle(http.Controller):

    # ===============================
    # LIST PAGE
    # ===============================
    @http.route(['/my/vehicles'], type='http', auth='user', website=True)
    def portal_my_vehicles(self, **kwargs):
        search = kwargs.get('search', '')
        domain = []
        if search:
            domain = ['|', ('name', 'ilike', search), ('vehicle_plate_no', 'ilike', search)]

        # Paparkan hanya vehicle milik transporter user login
        user = request.env.user
        transporter = request.env['res.transporter'].sudo().search([
            ('name', '=', user.partner_id.id)
        ], limit=1)


        vehicles = request.env['res.vehicle'].sudo().search([
            ('transporter_id', '=', transporter.id)
        ] + domain)

        return request.render('transport_portal.portal_my_vehicles', {
            'vehicle_list': vehicles,
            'search': search,
        })

    # ===============================
    # FORM PAGE (CREATE / EDIT)
    # ===============================
    @http.route(['/my/vehicle', '/my/vehicle/<int:vehicle_id>'], type='http', auth='user', website=True)
    def portal_my_vehicle(self, vehicle_id=None, **kw):
        user = request.env.user
        Vehicle = request.env['res.vehicle'].sudo()
        vehicle = Vehicle.browse(vehicle_id) if vehicle_id else None

        # Dapatkan transporter link kepada user
        transporter = request.env['res.transporter'].sudo().search([
            ('name', '=', user.partner_id.id)
        ], limit=1)

        return request.render('transport_portal.portal_my_vehicle_form', {
            'vehicle': vehicle,
            'transporter': transporter,
            'user': user,
        })

    # ===============================
    # SAVE (CREATE / UPDATE)
    # ===============================
    @http.route(['/my/vehicle/save'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_save_vehicle(self, **post):
        user = request.env.user

        required_fields = [
            'name', 'vehicle_plate_no', 'vehicle_type',
            'vehicle_capacity', 'insurance_expiry', 'vehicle_roadtax'
        ]
        missing = [f for f in required_fields if not post.get(f)]
        if missing:
            raise UserError("Please fill all required fields before submitting.")

        # Auto-link transporter berdasarkan user login
        transporter = request.env['res.transporter'].sudo().search([
            ('name', '=', user.partner_id.id)
        ], limit=1)

        if not transporter:
            raise UserError("Your account is not linked to a valid transporter. Please contact the admin.")

        vals = {
            'name': post.get('name'),
            'vehicle_plate_no': post.get('vehicle_plate_no'),
            'vehicle_type': post.get('vehicle_type'),
            'vehicle_capacity': post.get('vehicle_capacity'),
            'insurance_expiry': post.get('insurance_expiry'),
            'vehicle_roadtax': post.get('vehicle_roadtax'),
            'transporter_id': transporter.id,
        }

        Vehicle = request.env['res.vehicle'].sudo()

        if post.get('vehicle_id'):
            vehicle = Vehicle.browse(int(post['vehicle_id']))
            if vehicle.exists():
                vehicle.write(vals)
        else:
            Vehicle.create(vals)

        return request.redirect('/my/vehicles')
