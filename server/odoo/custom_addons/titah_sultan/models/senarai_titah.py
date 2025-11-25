from odoo import models, fields, api
from datetime import datetime

class SenaraiTitah(models.Model):
    _name = 'senarai.titah'
    _description = 'Senarai Titah DYMM Sultan Selangor'

    name = fields.Char(string='Tajuk Titah', required=True)

    tahun = fields.Selection(
        [(str(y), str(y)) for y in range(2000, datetime.now().year + 2)],
        string='Tahun',
        required=True
    )

    AGENSI_SELECTION = [
        ('jais', 'Jabatan Agama Islam Selangor (JAIS)'),
        ('lzs', 'Lembaga Zakat Selangor (LZS)'),
        ('yide', 'Yayasan Islam Darul Ehsan (YIDE)'),
        ('maissb', 'MAIS Holding Sdn. Bhd.'),
        ('yayasan_mais', 'Yayasan MAIS'),
        ('pusat_pemulihan', 'Pusat Pemulihan Baitul Ehsan'),
        ('infaq', 'Unit Infaq & Wakaf MAIS'),
        ('kolej_kais', 'Kolej Universiti Islam Antarabangsa Selangor (KUIS)'),
        ('pusat_pungutan', 'Pusat Pungutan Zakat MAIS'),
        ('lain_lain', 'Lain-lain'),
    ]

    mais_agensi = fields.Selection(
        selection=AGENSI_SELECTION,
        string="Nama Agensi",
        required=True
    )

    filename = fields.Char(string='Nama Fail')

    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Lampiran',
        domain="[('res_model','=','senarai.titah'), ('res_id','=',id)]"
    )

    status = fields.Selection([
        ('hijau', 'Selesai'),
        ('kuning', 'Dalam Tindakan'),
        ('merah', 'Tidak Dilaksanakan'),
    ], string='Status Pelaksanaan', default='kuning', required=True, group_expand='_group_expand_status')

    status_color = fields.Char(compute='_compute_status_color', store=False)

    @api.depends('status')
    def _compute_status_color(self):
        for rec in self:
            if rec.status == 'hijau':
                rec.status_color = 'success'  # green
            elif rec.status == 'kuning':
                rec.status_color = 'warning'  # yellow
            elif rec.status == 'merah':
                rec.status_color = 'danger'   # red
            else:
                rec.status_color = 'secondary'  # grey fallback

    respon_ids = fields.One2many('titah.respon', 'titah_id', string='Maklum Balas')

    kanban_color = fields.Integer(compute="_compute_kanban_color", store=True)

    _sql_constraints = [
        ('unique_titah_per_agency_year', 'unique(name, tahun, agensi_id)', 'Titah untuk agensi dan tahun ini sudah wujud.')
    ]

    @api.model
    def _group_expand_status(self, statuses, domain, order):
        return ['hijau', 'kuning', 'merah']

    @api.depends('status')
    def _compute_kanban_color(self):
        for record in self:
            if record.status == 'hijau':
                record.kanban_color = 2  # green
            elif record.status == 'kuning':
                record.kanban_color = 3  # yellow
            elif record.status == 'merah':
                record.kanban_color = 1  # red
            else:
                record.kanban_color = 0  # default

    hijau_count = fields.Integer(string='Selesai', compute='_compute_status_counters')
    kuning_count = fields.Integer(string='Dalam Tindakan', compute='_compute_status_counters')
    merah_count = fields.Integer(string='Tidak Dilaksanakan', compute='_compute_status_counters')

    @api.depends()
    def _compute_status_counters(self):
        counts = self.env['senarai.titah'].read_group(
            domain=[],
            fields=['status'],
            groupby=['status']
        )
        status_map = {'hijau': 0, 'kuning': 0, 'merah': 0}
        for count in counts:
            status = count['status']
            if status in status_map:
                status_map[status] = count['__count']
        for rec in self:
            rec.hijau_count = status_map['hijau']
            rec.kuning_count = status_map['kuning']
            rec.merah_count = status_map['merah']