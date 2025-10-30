from odoo import http
from odoo.http import request


class SlotBookingController(http.Controller):
    @http.route(['/slot_booking/transporters'], type='http', auth='public', website=True)
    def list_transporters(self, **kwargs):
        """Render a simple frontend page listing all transporters."""
        transporters = request.env['res.transporter'].sudo().search([], order='name asc')
        return request.render('slot_booking.transporters_template', {
            'transporters': transporters,
        })

    @http.route(['/slot_booking/transporters/<int:transporter_id>'], type='http', auth='public', website=True)
    def transporter_detail(self, transporter_id, **kwargs):
        """Render a detail page for a single transporter."""
        transporter = request.env['res.transporter'].sudo().browse(transporter_id)
        if not transporter.exists():
            return request.not_found()
        return request.render('slot_booking.transporter_detail_template', {
            'transporter': transporter,
        })

