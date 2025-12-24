from odoo import models, fields, api
from datetime import date, timedelta

class LeadSnapshot(models.Model):
    _name = "crm.lead.snapshot"
    _description = "Weekly Snapshot of CRM Leads"
    _order = "snapshot_date desc"

    lead_id = fields.Many2one("crm.lead", required=True, ondelete="cascade")
    name = fields.Char(related="lead_id.name", store=True)
    partner_id = fields.Many2one('res.partner', related='lead_id.partner_id', string='Customer', store=True)
    stage_id = fields.Many2one("crm.stage")
    expected_revenue = fields.Float()
    probability = fields.Float()
    priority = fields.Selection(related='lead_id.priority', string='Priority', store=True)
    snapshot_date = fields.Date(default=fields.Date.today, required=True)
    # New snapshot fields requested
    user_id = fields.Many2one('res.users', string='Salesperson')
    # Use create_date (related from lead) so column aligns with CRM's create_date "Date Funnel"
    create_date = fields.Datetime(related='lead_id.create_date', string='Date Funnel', store=True)
    expected_start_date = fields.Date(string='Expected Start Date')
    date_secured = fields.Date(related='lead_id.date_secured', string='Date Secured', store=True)
    date_go_live = fields.Date(string='Date Go Live')
    # Latest activity snapshot fields (only date + activity type as requested)
    last_activity_date = fields.Datetime(string='Last Activity Date')
    last_activity_type_id = fields.Many2one('mail.activity.type', string='Last Activity Type')
    # Week number (Mon-Fri week) based on snapshot_date
    plb_week = fields.Integer(string='Week', compute='_compute_plb_week', store=True)

    # Related fields from lead so views can reference them directly
    team_id = fields.Many2one('crm.team', related='lead_id.team_id', string='Sales Team', store=True)
    # crm.lead.description is fields.Html, so the related field must also be Html
    description = fields.Html(related='lead_id.description', string='Remarks', store=True)
    # Copy these values at snapshot time so the snapshot becomes an independent historical record
    SCOPE_SELECTION = [
        ('haulage', 'Haulage'),
        ('freight_forwarding', 'Freight Forwarding'),
        ('warehousing', 'Warehousing'),
        ('depot_yard', 'Depot / Yard'),
        ('distribution', 'Distribution'),
    ]
    scope_of_service = fields.Selection(SCOPE_SELECTION, string='Scope of Service')
    product = fields.Char(string='Product')
    DEPT_SELECTION = [
        ('central', 'Central'),
        ('northern', 'Northern'),
        ('southern', 'Southern'),
    ]
    dept_region = fields.Selection(DEPT_SELECTION, string='Dept/Region')
    contact_name = fields.Char(related='lead_id.contact_name', string='Contact Name', store=True)
    email_from = fields.Char(related='lead_id.email_from', string='Email', store=True)
    # Present lead tag names as a single string on the snapshot (avoids M2M related storage issues)
    tag_list = fields.Char(string='Other Emails', compute='_compute_tag_list', store=True)
    # Currency helper - match crm.lead.company_currency_id so Monetary related field type matches
    company_currency_id = fields.Many2one('res.currency', related='lead_id.company_currency_id', string='Currency', readonly=True, store=True)
    # Realized revenue must be Monetary and use the currency_field to match the crm.lead definition
    realized_revenue_fy2025 = fields.Monetary(related='lead_id.realized_revenue_fy2025', currency_field='company_currency_id', string='Realized Revenue FY2025', store=True)

    @api.depends('lead_id.tag_ids')
    def _compute_tag_list(self):
        for rec in self:
            if rec.lead_id and rec.lead_id.tag_ids:
                rec.tag_list = ', '.join(rec.lead_id.tag_ids.mapped('name'))
            else:
                rec.tag_list = False

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
        """Cron entry point: create snapshots for all CRM leads.
        When run manually (via button/wizard), snapshots all existing leads.
        When run via cron, snapshots leads created in the current week.
        Returns the number of snapshot records created.
        """
        Snapshot = self.env['crm.lead.snapshot']
        Lead = self.env['crm.lead']
        today = date.today()

        # Check if being called from context (manual run vs cron)
        # For manual runs, snapshot all leads
        # For cron runs, snapshot leads created this week
        context_manual = self.env.context.get('snapshot_manual', False)

        if context_manual:
            # Manual run: snapshot all leads
            leads = Lead.search([])
        else:
            # Cron run: snapshot leads created this week
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            start_dt = week_start.strftime('%Y-%m-%d 00:00:00')
            end_dt = week_end.strftime('%Y-%m-%d 23:59:59')
            leads = Lead.search([('create_date', '>=', start_dt), ('create_date', '<=', end_dt)])

            # If no leads this week, snapshot all leads
            if not leads:
                leads = Lead.search([])

        if not leads:
            return 0

        # Create snapshot records for every lead
        vals_list = []
        for lead in leads:
             # fetch latest activity for the lead (by create_date desc)
             act = self.env['mail.activity'].search([
                 ('res_model', '=', 'crm.lead'),
                 ('res_id', '=', lead.id)
             ], order='create_date desc', limit=1)

             if act:
                 last_act_date = act.date_deadline or act.create_date
                 last_act_type = act.activity_type_id.id if act.activity_type_id else False
             else:
                 last_act_date = False
                 last_act_type = False

             vals_list.append({
                 'lead_id': lead.id,
                 'stage_id': lead.stage_id.id or False,
                 'expected_revenue': lead.expected_revenue or 0.0,
                 'probability': lead.probability or 0.0,
                 'snapshot_date': today,
                 # populate requested fields
                 'user_id': lead.user_id.id or False,
                 # 'create_date' is a related field on the snapshot; do not write it here
                 'expected_start_date': lead.expected_start_date or False,
                 'date_go_live': lead.date_go_live or False,
                 'scope_of_service': lead.scope_of_service or False,
                 'product': lead.product or False,
                 'dept_region': lead.dept_region or False,
                 # populate latest activity fields (date + type)
                 'last_activity_date': last_act_date,
                 'last_activity_type_id': last_act_type,
             })

        if not vals_list:
            return 0

        try:
            created = Snapshot.create(vals_list)
            created_count = len(created)
            return created_count
        except Exception as e:
            # Log the error for debugging
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error('Snapshot creation failed: %s', str(e))
            raise


class PlbSnapshotWizard(models.TransientModel):
    _name = 'plb.snapshot.wizard'
    _description = 'Run Weekly CRM Lead Snapshot (PLB)'

    note = fields.Char(string='Info', readonly=True, default='Run the weekly CRM lead snapshot now.')

    def action_run_snapshot(self):
        """Run the snapshot and display a client notification with the created count and diagnostics."""
        Snapshot = self.env['crm.lead.snapshot']
        Lead = self.env['crm.lead']
        today = date.today()
        # Compute week start (Monday) and end (Sunday)
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        start_dt = week_start.strftime('%Y-%m-%d 00:00:00')
        end_dt = week_end.strftime('%Y-%m-%d 23:59:59')

        leads_in_week = Lead.search([('create_date', '>=', start_dt), ('create_date', '<=', end_dt)])
        leads_in_week_count = len(leads_in_week)
        total_leads_count = Lead.search_count([])
        existing_today = Snapshot.search([('snapshot_date', '=', today)])
        existing_today_count = len(existing_today)
        existing_today_lead_ids = existing_today.mapped('lead_id').ids[:10]

        # Call snapshot with manual context flag to snapshot all leads
        try:
            created_count = self.env['crm.lead'].with_context(snapshot_manual=True).cron_create_weekly_snapshot()
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error('Snapshot failed with error: %s', str(e))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Snapshot Error',
                    'message': 'Snapshot failed: %s' % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

        if created_count > 0:
            message = 'Created %s snapshot record(s) for %s leads.' % (created_count, total_leads_count)
            mtype = 'success'
        else:
            # created_count == 0 -> provide diagnostics for debugging
            parts = [
                'Created 0 snapshots.',
                'Leads in this week: %s.' % (leads_in_week_count,),
                'Total leads: %s.' % (total_leads_count,),
                'Existing snapshots for today: %s.' % (existing_today_count,),
            ]
            if existing_today_lead_ids:
                parts.append('Example lead ids already snapped today: %s' % (existing_today_lead_ids,))
            message = ' '.join(parts)
            mtype = 'warning'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Snapshot Result',
                'message': message,
                'type': mtype,
                'sticky': False,
            }
        }
