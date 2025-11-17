from odoo import api, fields, models  # type: ignore
from datetime import datetime, date


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    partner_id = fields.Many2one(
        'res.partner',
        string='Who (Company)',
        compute='_compute_partner_id',
        compute_sudo=True,
        readonly=True,
        store=True,
        index=True,
        help='Related partner when the activity targets a record that has a partner.'
    )

    # Assigned contact (a specific person/contact) linked to this activity.
    contact_id = fields.Many2one(
        'res.partner',
        string='Who (Contact)',
        index=True,
        help='Specific contact person assigned for this activity. Editable in the activity form.'
    )

    # Position / job title of the contact (related field for display in tree)
    contact_position = fields.Char(
        related='contact_id.function',
        string='Position',
        readonly=True,
        store=False
    )

    # PLB reason/category for the activity
    plb_why = fields.Selection([
        ('sales', 'SALES'),
        ('rfq', 'RFQ'),
        ('ops', 'OPS'),
        ('debts', 'DEBTS'),
        ('oth', 'OTH'),
    ], string='Why', index=True, help='Category for PLB activities')

    # Computed week number from date_deadline (not stored, not searchable/groupable)
    plb_week = fields.Char(
        string='Week',
        compute='_compute_plb_week',
        store=False,
        readonly=True,
    )

    @api.onchange('res_model', 'res_id')
    def _onchange_set_contact_from_target(self):
        for rec in self:
            # only set default if not already set
            if rec.contact_id:
                continue
            if rec.res_model == 'crm.lead' and rec.res_id:
                lead = self.env['crm.lead'].sudo().browse(rec.res_id)
                if lead and lead.partner_id:
                    # Prefer an actual contact (child partner) of the company if present
                    contacts = lead.partner_id.child_ids
                    rec.contact_id = contacts and contacts[0] or lead.partner_id
                else:
                    rec.contact_id = False

    @api.depends('res_model', 'res_id')
    def _compute_partner_id(self):
        for rec in self:
            rec.partner_id = False
            if not rec.res_model or not rec.res_id:
                continue
            # Prefer a targeted lookup for crm.lead to be explicit and efficient
            if rec.res_model == 'crm.lead':
                lead = self.env['crm.lead'].sudo().browse(rec.res_id)
                if lead:
                    rec.partner_id = lead.partner_id
                continue
            # Generic fallback: try to read common partner fields on the target record
            try:
                model = self.env[rec.res_model]
            except Exception:
                model = None
            if not model:
                continue
            target = model.sudo().browse(rec.res_id)
            if not target:
                continue
            # Prefer explicit partner_id field on the target record
            if 'partner_id' in getattr(target, '_fields', {}):
                rec.partner_id = target.partner_id
            # If the target has invoice_partner_id (some models), prefer that
            elif 'invoice_partner_id' in getattr(target, '_fields', {}):
                rec.partner_id = target.invoice_partner_id
            # If the target defines a commercial_partner_id, use it as fallback
            elif 'commercial_partner_id' in getattr(target, '_fields', {}):
                rec.partner_id = target.commercial_partner_id
            else:
                # No known partner field on the target model
                rec.partner_id = False

    @api.depends('date_deadline')
    def _compute_plb_week(self):
        """Compute the week number (ISO week within year) from date_deadline.

        - If date_deadline is a datetime, convert to user's timezone before extracting week.
        - Result is string of the week number (e.g. '5' or '52'). Empty when no deadline.
        """
        for rec in self:
            rec.plb_week = False
            dd = rec.date_deadline
            if not dd:
                continue
            try:
                # If it's a datetime-like value, convert to user tz
                if isinstance(dd, datetime):
                    user_dt = fields.Datetime.context_timestamp(rec, dd)
                    rec.plb_week = str(user_dt.isocalendar()[1])
                elif isinstance(dd, date):
                    rec.plb_week = str(dd.isocalendar()[1])
                else:
                    # Fallback: try to parse when it's a string (shouldn't normally happen)
                    from dateutil import parser

                    parsed = parser.parse(str(dd))
                    # parser gives datetime; convert to date
                    rec.plb_week = str(parsed.isocalendar()[1])
            except Exception:
                rec.plb_week = False

