from odoo import fields, models, api  # type: ignore


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Computed fields for PLB calculations (stored for pivot aggregation)
    plb_ar = fields.Monetary(
        string='Annualized Revenue (AR)', currency_field='company_currency',
        compute='_compute_plb_revenues', store=True, group_operator='sum'
    )
    plb_mar = fields.Monetary(
        string='Monthly Annualized Revenue (MAR)', currency_field='company_currency',
        compute='_compute_plb_revenues', store=True, group_operator='sum'
    )
    plb_cf = fields.Monetary(
        string='Carry Forward (CF)', currency_field='company_currency',
        compute='_compute_plb_revenues', store=True, group_operator='sum'
    )

    # Monthly realized revenue (RR) per calendar month for the current fiscal year logic (stored for pivot)
    plb_rr_jan = fields.Monetary(string='RR Jan', currency_field='company_currency', compute='_compute_plb_rr_months', store=True, group_operator='sum')
    plb_rr_feb = fields.Monetary(string='RR Feb', currency_field='company_currency', compute='_compute_plb_rr_months', store=True, group_operator='sum')
    plb_rr_mar = fields.Monetary(string='RR Mar', currency_field='company_currency', compute='_compute_plb_rr_months', store=True, group_operator='sum')
    plb_rr_apr = fields.Monetary(string='RR Apr', currency_field='company_currency', compute='_compute_plb_rr_months', store=True, group_operator='sum')
    plb_rr_may = fields.Monetary(string='RR May', currency_field='company_currency', compute='_compute_plb_rr_months', store=True, group_operator='sum')
    plb_rr_jun = fields.Monetary(string='RR Jun', currency_field='company_currency', compute='_compute_plb_rr_months', store=True, group_operator='sum')
    plb_rr_jul = fields.Monetary(string='RR Jul', currency_field='company_currency', compute='_compute_plb_rr_months', store=True, group_operator='sum')
    plb_rr_aug = fields.Monetary(string='RR Aug', currency_field='company_currency', compute='_compute_plb_rr_months', store=True, group_operator='sum')
    plb_rr_sep = fields.Monetary(string='RR Sep', currency_field='company_currency', compute='_compute_plb_rr_months', store=True, group_operator='sum')
    plb_rr_oct = fields.Monetary(string='RR Oct', currency_field='company_currency', compute='_compute_plb_rr_months', store=True, group_operator='sum')
    plb_rr_nov = fields.Monetary(string='RR Nov', currency_field='company_currency', compute='_compute_plb_rr_months', store=True, group_operator='sum')
    plb_rr_dec = fields.Monetary(string='RR Dec', currency_field='company_currency', compute='_compute_plb_rr_months', store=True, group_operator='sum')

    # Total realized revenue for 2025 (sum of all monthly RR)
    plb_realized_revenue_2025 = fields.Monetary(
        string='Realized Revenue 2025', currency_field='company_currency',
        compute='_compute_plb_rr_months', store=True, group_operator='sum'
    )

    # Count field for pivot (always 1 per record, sums to total count)
    plb_count = fields.Integer(string='Count', default=1, store=True, group_operator='sum')

    @api.depends('expected_revenue', 'contract_months')
    def _compute_plb_revenues(self):
        for rec in self:
            ar = rec.expected_revenue or 0.0
            mar = ar / 12.0
            # RR = MAR * (12 - current_month + 1)
            current_month = int(rec.contract_months or 0)
            rr = mar * max(0, (12 - current_month + 1)) if current_month else 0.0
            cf = ar - rr
            rec.plb_ar = ar
            rec.plb_mar = mar
            rec.plb_cf = cf

    @api.depends('expected_revenue', 'contract_months')
    def _compute_plb_rr_months(self):
        for rec in self:
            # Reset all monthly RR
            months = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
            }
            for key in months.keys():
                setattr(rec, f'plb_rr_{key}', 0.0)
            ar = rec.expected_revenue or 0.0
            mar = ar / 12.0
            current_month = int(rec.contract_months or 0)

            # Calculate total realized revenue
            total_rr = 0.0

            if current_month:
                # Fill RR for remaining months including current month: current_month..Dec
                for mkey, mnum in months.items():
                    if mnum >= current_month:
                        setattr(rec, f'plb_rr_{mkey}', mar)
                        total_rr += mar

            rec.plb_realized_revenue_2025 = total_rr
