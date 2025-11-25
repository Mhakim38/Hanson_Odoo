from odoo import models, fields, api
from datetime import date

class LeadSnapshot(models.Model):
    _name = "crm.lead.snapshot"
    _description = "Weekly Snapshot of CRM Leads"
    _order = "snapshot_date desc"

    lead_id = fields.Many2one("crm.lead", required=True, ondelete="cascade")
    name = fields.Char(related="lead_id.name", store=True)
    stage_id = fields.Many2one("crm.stage")
    expected_revenue = fields.Float()
    probability = fields.Float()
    snapshot_date = fields.Date(default=fields.Date.today, required=True)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def action_create_weekly_snapshot(self):
        """
        Create a single crm.lead.snapshot for this lead (used by the manual "Snapshot Now" button for testing).
        For testing we'll set snapshot_date to today's date. In the full implementation, a cron
        can call a batch method to snapshot all leads for a week.
        """
        Snapshot = self.env['crm.lead.snapshot']
        records = []
        for lead in self:
            vals = {
                'lead_id': lead.id,
                'stage_id': lead.stage_id and lead.stage_id.id or False,
                'expected_revenue': lead.expected_revenue or 0.0,
                'probability': lead.probability or 0.0,
                'snapshot_date': date.today(),
            }
            rec = Snapshot.create(vals)
            records.append(rec)
        return True

    @api.model
    def cron_create_weekly_snapshot(self):
        """Cron entry point: create snapshots for all CRM leads.
        Currently this creates one snapshot per lead using today's date. For a true weekly
        snapshot (e.g. always Friday), refine the snapshot_date logic and filtering later.
        """
        Snapshot = self.env['crm.lead.snapshot']
        Lead = self.env['crm.lead']
        leads = Lead.search([])
        if not leads:
            return True
        vals_list = []
        today = date.today()
        for lead in leads:
            vals_list.append({
                'lead_id': lead.id,
                'stage_id': lead.stage_id and lead.stage_id.id or False,
                'expected_revenue': lead.expected_revenue or 0.0,
                'probability': lead.probability or 0.0,
                'snapshot_date': today,
            })
        # create in batch
        Snapshot.create(vals_list)
        return True
