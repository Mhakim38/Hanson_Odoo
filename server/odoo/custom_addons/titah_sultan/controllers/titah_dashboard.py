from odoo import http
from odoo.http import Controller, route, request

class TitahDashboardController(http.Controller):
    @http.route('/titah/status_counts', type='json', auth='user')
    def status_counts(self):
        model = request.env['senarai.titah'].sudo()
        statuses = ['hijau', 'kuning', 'merah']

        counts = {
            status: model.search_count([('status', '=', status)])
            for status in statuses
        }

        return counts


class TitahResponController(Controller):

    @route('/titah/respon_status_counts', type='json', auth='user')
    def respon_status_counts(self):
        model = request.env['titah.respon']
        return {
            'selesai': model.search_count([('status_tindakan', '=', 'selesai')]),
            'sedang': model.search_count([('status_tindakan', '=', 'sedang')]),
            'belum': model.search_count([('status_tindakan', '=', 'belum')]),
        }
