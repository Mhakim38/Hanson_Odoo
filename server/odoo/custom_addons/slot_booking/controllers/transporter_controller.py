from odoo import http
from odoo.http import request


class SlotBookingController(http.Controller):
    @http.route(['/slot_booking/transporters'], type='http', auth='public', website=True)
    def list_transporters(self, page=1, limit=12, q=None, active='1', **kwargs):
        """Render a frontend page listing transporters with optional search, active filter and pagination.

        Query params:
        - page: page number (1-based)
        - limit: items per page
        - q: search term (searches company name and transporter_code)
        - active: '1' (only active, default), '0' (only inactive), 'all' (both)
        """
        # normalize inputs
        try:
            page = int(page)
        except Exception:
            page = 1
        try:
            limit = int(limit)
        except Exception:
            limit = 12

        domain = []
        if str(active).lower() in ("1", "true", "yes"):
            domain.append(("active", "=", True))
        elif str(active).lower() in ("0", "false", "no"):
            domain.append(("active", "=", False))
        # search by transporter company name or code
        if q:
            # name is a many2one to res.partner; searching on the name field works with 'ilike'
            domain += ["|", ("name", "ilike", q), ("transporter_code", "ilike", q)]

        Transporter = request.env['res.transporter'].sudo()
        total = Transporter.search_count(domain)
        offset = max(0, (page - 1) * limit)
        transporters = Transporter.search(domain, order='name asc', limit=limit, offset=offset)

        pager = {
            'page': page,
            'pages': max(1, (total + limit - 1) // limit),
            'limit': limit,
            'total': total,
        }

        return request.render('slot_booking.transporters_template', {
            'transporters': transporters,
            'pager': pager,
            'q': q or '',
            'active': str(active),
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
