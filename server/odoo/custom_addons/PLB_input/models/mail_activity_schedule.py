from odoo import models, fields, api


class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    def _get_plb_why_selection(self):
        # Mirror selection values from mail.activity.plb_why so choices stay in sync
        return self.env['mail.activity']._fields['plb_why'].selection

    # Additional fields to be propagated to created mail.activity records
    plb_why = fields.Selection(
        selection=lambda self: self._get_plb_why_selection(),
        string='Why'
    )

    contact_id = fields.Many2one('res.partner', string='Who (Contact)')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Prefill contact for single lead
        ctx = self.env.context or {}
        active_model = ctx.get('active_model') or ctx.get('params', {}).get('active_model')
        active_id = ctx.get('active_id')
        if 'contact_id' in fields_list and not res.get('contact_id') and active_model == 'crm.lead' and active_id:
            lead = self.env['crm.lead'].sudo().browse(active_id)
            if lead.exists():
                contact = lead.partner_id.child_ids[:1] or lead.partner_id
                res['contact_id'] = contact and contact.id or False
        return res

    def _action_schedule_activities(self):
        # Use wizard helper to obtain target records and pass extra vals
        return self._get_applied_on_records().activity_schedule(
            activity_type_id=self.activity_type_id.id,
            automated=False,
            summary=self.summary,
            note=self.note,
            user_id=self.activity_user_id.id,
            date_deadline=self.date_deadline,
            plb_why=self.plb_why,
            contact_id=self.contact_id.id,
        )
