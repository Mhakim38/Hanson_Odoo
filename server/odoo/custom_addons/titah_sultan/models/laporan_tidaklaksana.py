from odoo import models, fields, api

class LaporanTidakLaksana(models.Model):
    _name = 'laporan.tidaklaksana'
    _description = 'Laporan Tidak Laksana'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reported_at desc'

    titah_id = fields.Many2one(
        'senarai.titah',
        string='Titah Berkaitan',
        required=True,
        ondelete='cascade',
        tracking=True
    )

    penerangan = fields.Text(
        string='Penerangan Ketidakpatuhan',
        required=True,
        tracking=True
    )

    lampiran_bukti = fields.Binary(
        string='Lampiran Bukti',
        tracking=True
    )

    lampiran_bukti_name = fields.Char(string='Nama Fail Lampiran')

    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Lampiran Tambahan',
        domain="[('res_model','=','laporan.tidaklaksana'), ('res_id','=',id)]"
    )

    reported_by = fields.Many2one(
        'res.users',
        string='Dilaporkan Oleh',
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True
    )

    reported_at = fields.Datetime(
        string='Dilaporkan Pada',
        default=lambda self: fields.Datetime.now(),
        readonly=True,
        tracking=True
    )

    updated_by = fields.Many2one(
        'res.users',
        string='Dikemaskini Oleh',
        readonly=True,
        tracking=True
    )

    updated_at = fields.Datetime(
        string='Dikemaskini Pada',
        readonly=True,
        tracking=True
    )

    @api.model
    def create(self, vals):
        vals['reported_by'] = self.env.uid
        vals['reported_at'] = fields.Datetime.now()
        vals['updated_by'] = self.env.uid
        vals['updated_at'] = fields.Datetime.now()
        return super().create(vals)

    def write(self, vals):
        vals['updated_by'] = self.env.uid
        vals['updated_at'] = fields.Datetime.now()
        return super().write(vals)
