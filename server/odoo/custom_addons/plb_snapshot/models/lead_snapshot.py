from odoo import models, fields, api
from datetime import date, timedelta

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
    # New snapshot fields requested
    user_id = fields.Many2one('res.users', string='Salesperson')
    created_date = fields.Datetime(string='Date Funnel')
    expected_start_date = fields.Date(string='Expected Start Date')
    date_go_live = fields.Date(string='Date Go Live')
    # Latest activity snapshot fields (only date + activity type as requested)
    last_activity_date = fields.Datetime(string='Last Activity Date')
    last_activity_type_id = fields.Many2one('mail.activity.type', string='Last Activity Type')
    # Week number (Mon-Fri week) based on snapshot_date
    plb_week = fields.Integer(string='Week', compute='_compute_plb_week', store=True)

    @api.depends('snapshot_date')
    def _compute_plb_week(self):
        """Compute week number in year where a week runs from Monday to Friday.
        Assumption: week 1 starts on the first Monday on or after Jan 1. Dates before
        that first Monday are assigned to week 1.
        """
        for rec in self:
            sd = rec.snapshot_date
            if not sd:
                rec.plb_week = False
                continue
            # Map weekend (Sat=5, Sun=6) to previous Friday so weekend days belong to the
            # preceding Mon-Fri business week.
            if sd.weekday() >= 5:
                # move back to Friday
                sd_adj = sd - timedelta(days=(sd.weekday() - 4))
            else:
                sd_adj = sd

            year = sd_adj.year
            first = date(year, 1, 1)
            # find first Monday on or after Jan 1
            if first.weekday() == 0:
                first_monday = first
            else:
                first_monday = first + timedelta(days=(7 - first.weekday()))

            if sd_adj < first_monday:
                rec.plb_week = 1
            else:
                rec.plb_week = ((sd_adj - first_monday).days // 7) + 1


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def action_create_weekly_snapshot(self):
        """Trigger the weekly batch snapshot for all leads.
        This makes `action_create_weekly_snapshot` behave as a model-level "Snapshot Week" action
        so both the kanban menu item and the form header call the same logic.
        """
        return self.env['crm.lead'].cron_create_weekly_snapshot()

    def action_generate_leads(self):
        """Stub method to satisfy views that reference `action_generate_leads` on crm.lead.
        Some third-party kanban views (e.g. crm_iap_mine) reference this method in their header;
        providing a no-op here prevents validation errors during module install/upgrade.
        Implement real logic elsewhere if needed.
        """
        return True

    @api.model
    def cron_create_weekly_snapshot(self):
        """Cron entry point: create snapshots for all CRM leads created within the current week.
        For the automatic weekly job and for the kanban "Snapshot Week" button we capture leads
        whose `create_date` falls within the current ISO week (Mon-Sun). Adjust this logic if you
        prefer a Friday-centric week boundary.
        """
        Snapshot = self.env['crm.lead.snapshot']
        Lead = self.env['crm.lead']
        today = date.today()
        # Compute week start (Monday) and end (Sunday)
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        # domain expects datetime strings; use full-day bounds
        start_dt = week_start.strftime('%Y-%m-%d 00:00:00')
        end_dt = week_end.strftime('%Y-%m-%d 23:59:59')
        leads = Lead.search([('create_date', '>=', start_dt), ('create_date', '<=', end_dt)])
        if not leads:
            return 0
        vals_list = []
        for lead in leads:
            # fetch latest activity for the lead (by create_date desc)
            act = self.env['mail.activity'].search([('res_model', '=', 'crm.lead'), ('res_id', '=', lead.id)], order='create_date desc', limit=1)
            last_act_date = act.date_deadline or act.create_date if act else False
            last_act_type = act.activity_type_id and act.activity_type_id.id or False

            vals_list.append({
                'lead_id': lead.id,
                'stage_id': lead.stage_id and lead.stage_id.id or False,
                'expected_revenue': lead.expected_revenue or 0.0,
                'probability': lead.probability or 0.0,
                'snapshot_date': today,
                # populate requested fields
                'user_id': lead.user_id and lead.user_id.id or False,
                'created_date': lead.create_date,
                'expected_start_date': lead.expected_start_date or False,
                'date_go_live': lead.date_go_live or False,
                # populate latest activity fields (date + type)
                'last_activity_date': last_act_date,
                'last_activity_type_id': last_act_type,
            })
        # create in batch
        created = Snapshot.create(vals_list)
        # created may be a recordset; return number created
        return len(created)
