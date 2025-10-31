from odoo import http
from odoo.http import request
from datetime import date
import json

class BookingPortalController(http.Controller):

    @http.route(['/slot_booking/book_slot'], type='http', auth='public', website=True)
    def slot_booking_form(self, **kw):
        slots = request.env['res.slot'].sudo().search([])
        transporters = request.env['res.transporter'].sudo().search([])
        containers = request.env['res.container'].sudo().search([])
        vehicles = request.env['res.vehicle'].sudo().search([])
        trailers = request.env['res.trailer'].sudo().search([])
        drivers = request.env['res.driver'].sudo().search([])
        depots = request.env['res.partner'].sudo().search([('is_company', '=', True)])
        bookings = request.env['res.booking.list'].sudo().search([], order="booking_date desc", limit=10)

        return request.render('slot_booking.slot_booking_form_template', {
            'slots': slots,
            'transporters': transporters,
            'containers': containers,
            'vehicles': vehicles,
            'trailers': trailers,
            'drivers': drivers,
            'depots': depots,
            'bookings': bookings,
        })

    @http.route(['/slot_booking/submit'], type='http', auth='public', website=True, csrf=True)
    def submit_slot_booking(self, **post):
        booking_number = f"BK-{date.today().strftime('%Y%m%d')}-{request.env['ir.sequence'].next_by_code('res.booking.list') or '001'}"
        request.env['res.booking.list'].sudo().create({
            'booking_number': booking_number,
            'booking_date': date.today(),
            'slot_id': int(post.get('slot_id')),
            'booking_type': post.get('booking_type'),
            'depot_id_from': int(post.get('depot_id_from')) if post.get('depot_id_from') else False,
            'depot_id_to': int(post.get('depot_id_to')) if post.get('depot_id_to') else False,
            'container_id': int(post.get('container_id')) if post.get('container_id') else False,
            'transporter_id': int(post.get('transporter_id')) if post.get('transporter_id') else False,
            'vehicle_id': int(post.get('vehicle_id')) if post.get('vehicle_id') else False,
            'trailer_id': int(post.get('trailer_id')) if post.get('trailer_id') else False,
            'driver_id': int(post.get('driver_id')) if post.get('driver_id') else False,
        })
        return request.render('slot_booking.slot_booking_thanks_template', {
            'booking_number': booking_number
        })



class SlotBookingController(http.Controller):

    @http.route('/slot_booking/get_slot_info', type='http', auth='public', csrf=False)
    def get_slot_info(self, slot_id=None, **kwargs):
        if not slot_id:
            return http.Response("{}", status=400)

        slot = request.env['res.slot'].sudo().browse(int(slot_id))
        if not slot.exists():
            return http.Response("{}", status=404)

        data = {
            "slot_time": dict(slot._fields['slot_time'].selection).get(slot.slot_time, ""),
            "criteria_content": slot.criteria_id.criteria_content if slot.criteria_id else "",
            "gate": dict(slot._fields['gate'].selection).get(slot.gate, "")
        }
        return http.Response(json.dumps(data), content_type='application/json')
