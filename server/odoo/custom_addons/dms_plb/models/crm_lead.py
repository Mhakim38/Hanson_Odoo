from odoo import models, fields


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    has_quotation = fields.Boolean(
        string='Quotation Uploaded',
        compute='_compute_documents'
    )

    has_contract = fields.Boolean(
        string='Contract Uploaded',
        compute='_compute_documents'
    )

    dms_count = fields.Integer(
        string='Documents',
        compute='_compute_documents'
    )

    def _compute_documents(self):
        Dms = self.env['crm.lead.dms']
        for lead in self:
            records = Dms.search([('lead_id', '=', lead.id)])
            lead.has_quotation = any(
                r.document_type == 'quotation' for r in records
            )
            lead.has_contract = any(
                r.document_type == 'contract' for r in records
            )
            lead.dms_count = len(records)

    def action_open_dms(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'crm.lead.dms',
            'view_mode': 'tree,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {
                'default_lead_id': self.id,
            }
        }
