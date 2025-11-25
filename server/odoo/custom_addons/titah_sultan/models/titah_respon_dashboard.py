from odoo import models, fields, api

class TitahResponDashboard(models.TransientModel):
    _name = 'titah.respon.dashboard'
    _description = 'Dashboard Titah Respon'

    total_hijau = fields.Integer(string="Telah Dilaksanakan", compute='_compute_totals')
    total_kuning = fields.Integer(string="Dalam Tindakan", compute='_compute_totals')
    total_merah = fields.Integer(string="Tidak Dilaksanakan", compute='_compute_totals')

    @api.depends()
    def _compute_totals(self):
        model = self.env['titah.respon']
        self.total_hijau = model.search_count([('status', '=', 'hijau')])
        self.total_kuning = model.search_count([('status', '=', 'kuning')])
        self.total_merah = model.search_count([('status', '=', 'merah')])

    @api.model
    def default_get(self, fields):
        """Auto-generate a transient dashboard record when the action is opened."""
        res = super().default_get(fields)
        return res