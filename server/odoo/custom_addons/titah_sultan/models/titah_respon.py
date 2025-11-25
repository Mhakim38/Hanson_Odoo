from odoo import models, fields, api
from datetime import datetime

class TitahRespon(models.Model):
    _name = 'titah.respon'
    _description = 'Maklum Balas terhadap Titah'
    _order = 'create_date desc'

    titah_id = fields.Many2one(
        'senarai.titah',
        string='Titah Berkaitan',
        required=True,
        ondelete='cascade'
    )

    maklum_balas = fields.Text(
        string='Maklum Balas',
        required=True
    )

    status_tindakan = fields.Selection([
        ('belum', 'Belum Ada Tindakan'),
        ('sedang', 'Sedang Diproses'),
        ('selesai', 'Telah Selesai'),
    ], string='Status Tindakan', default='belum', required=True)

    status_tindakan_color = fields.Char(compute='_compute_status_tindakan_color', store=False)

    @api.depends('status_tindakan')
    def _compute_status_tindakan_color(self):
        for rec in self:
            if rec.status_tindakan == 'selesai':
                rec.status_tindakan_color = 'success'
            elif rec.status_tindakan == 'sedang':
                rec.status_tindakan_color = 'info'
            elif rec.status_tindakan == 'belum':
                rec.status_tindakan_color = 'warning'
            else:
                rec.status_tindakan_color = 'secondary'

    updated_by = fields.Many2one(
        'res.users',
        string='Dikemaskini Oleh',
        readonly=True
    )

    updated_at = fields.Datetime(
        string='Dikemaskini Pada',
        readonly=True
    )

    @api.model
    def create(self, vals):
        vals['updated_by'] = self.env.uid
        vals['updated_at'] = fields.Datetime.now()
        return super().create(vals)

    def write(self, vals):
        vals['updated_by'] = self.env.uid
        vals['updated_at'] = fields.Datetime.now()
        return super().write(vals)
