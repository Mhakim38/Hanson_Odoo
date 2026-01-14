from odoo import models, fields


class CrmLeadDms(models.Model):
    _name = 'crm.lead.dms'
    _description = 'CRM Lead Document Management'
    _order = 'create_date desc'

    lead_id = fields.Many2one(
        'crm.lead',
        string='CRM Lead',
        required=True,
        ondelete='cascade'
    )

    name = fields.Char(required=True)

    document_type = fields.Selection(
        [
            ('quotation', 'Quotation'),
            ('contract', 'Contract'),
        ],
        required=True
    )

    file = fields.Binary(string='File', required=True)
    filename = fields.Char(string='Filename')
