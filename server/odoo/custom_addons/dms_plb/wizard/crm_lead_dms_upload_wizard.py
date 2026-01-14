# wizard/crm_lead_dms_upload_wizard.py
from odoo import models, fields

class CrmLeadDmsUploadWizard(models.TransientModel):
    _name = 'crm.lead.dms.upload.wizard'
    _description = 'Upload Quotation and Contract to CRM Lead DMS'

    lead_id = fields.Many2one('crm.lead', string='Lead', required=True)

    # Fields for the wizard form
    quotation_file = fields.Binary(string='Quotation File')
    quotation_filename = fields.Char(string='Quotation Filename')

    contract_file = fields.Binary(string='Contract File')
    contract_filename = fields.Char(string='Contract Filename')

    def action_upload(self):
        """Upload files to crm.lead.dms and mark the lead"""
        Dms = self.env['crm.lead.dms']

        if self.quotation_file:
            Dms.create({
                'lead_id': self.lead_id.id,
                'type': 'quotation',
                'attachment': self.quotation_file,
                'name': self.quotation_filename,
            })
            self.lead_id.quotation_uploaded = True

        if self.contract_file:
            Dms.create({
                'lead_id': self.lead_id.id,
                'type': 'contract',
                'attachment': self.contract_file,
                'name': self.contract_filename,
            })
            self.lead_id.contract_uploaded = True

        return {'type': 'ir.actions.act_window_close'}
