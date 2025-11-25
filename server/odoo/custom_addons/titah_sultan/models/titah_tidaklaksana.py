from odoo import models, fields, api

class TitahTidakLaksana(models.Model):
    _name = 'titah.tidaklaksana'
    _description = 'Laporan Tidak Laksana Titah'

    titah_id = fields.Many2one('senarai.titah', string='Titah Berkaitan', required=True)

    alasan = fields.Text(string='Alasan/Tindakan Tidak Laksana', required=True)

    lampiran_bukti = fields.Binary(string='Lampiran Bukti')
    filename = fields.Char(string='Nama Fail')

    created_by = fields.Many2one('res.users', string='Dilaporkan Oleh', default=lambda self: self.env.user, readonly=True)
    created_at = fields.Datetime(string='Tarikh Laporan', default=fields.Datetime.now, readonly=True)

    def write(self, vals):
        # Log update time for auditing
        vals['created_at'] = fields.Datetime.now()
        vals['created_by'] = self.env.user.id
        return super().write(vals)
