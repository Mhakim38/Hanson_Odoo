from odoo import fields, models


class PlbPartnerReport(models.Model):
    _name = 'plb.partner.report'
    _description = 'PLB Partner Report (aggregated per customer)'
    _auto = False
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    salesperson_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    scope_of_service = fields.Char(string='Services', readonly=True)

    ar = fields.Monetary(string='AR', currency_field='company_currency', readonly=True)
    mar = fields.Monetary(string='MAR', currency_field='company_currency', readonly=True)

    rr_jan = fields.Monetary(string='RR Jan', currency_field='company_currency', readonly=True)
    rr_feb = fields.Monetary(string='RR Feb', currency_field='company_currency', readonly=True)
    rr_mar = fields.Monetary(string='RR Mar', currency_field='company_currency', readonly=True)
    rr_apr = fields.Monetary(string='RR Apr', currency_field='company_currency', readonly=True)
    rr_may = fields.Monetary(string='RR May', currency_field='company_currency', readonly=True)
    rr_jun = fields.Monetary(string='RR Jun', currency_field='company_currency', readonly=True)
    rr_jul = fields.Monetary(string='RR Jul', currency_field='company_currency', readonly=True)
    rr_aug = fields.Monetary(string='RR Aug', currency_field='company_currency', readonly=True)
    rr_sep = fields.Monetary(string='RR Sep', currency_field='company_currency', readonly=True)
    rr_oct = fields.Monetary(string='RR Oct', currency_field='company_currency', readonly=True)
    rr_nov = fields.Monetary(string='RR Nov', currency_field='company_currency', readonly=True)
    rr_dec = fields.Monetary(string='RR Dec', currency_field='company_currency', readonly=True)

    rr_total = fields.Monetary(string='RR Total', currency_field='company_currency', readonly=True)
    cf_total = fields.Monetary(string='CF Total', currency_field='company_currency', readonly=True)

    stage_id = fields.Many2one('crm.stage', string='Stage', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    company_currency = fields.Many2one('res.currency', string='Currency', readonly=True)

    def init(self):
        # SQL view that aggregates crm.lead per partner
        self.env.cr.execute('DROP VIEW IF EXISTS plb_partner_report')
        self.env.cr.execute('''
            CREATE VIEW plb_partner_report AS (
                SELECT
                    MIN(l.id) AS id,
                    l.partner_id AS partner_id,
                    CASE WHEN COUNT(DISTINCT l.user_id)=1 THEN MIN(l.user_id) ELSE NULL END AS salesperson_id,
                    CASE WHEN COUNT(DISTINCT l.scope_of_service)=1 THEN MIN(l.scope_of_service) ELSE NULL END AS scope_of_service,

                    SUM(COALESCE(l.plb_ar, 0.0)) AS ar,
                    SUM(COALESCE(l.plb_mar, 0.0)) AS mar,

                    SUM(COALESCE(l.plb_rr_jan, 0.0)) AS rr_jan,
                    SUM(COALESCE(l.plb_rr_feb, 0.0)) AS rr_feb,
                    SUM(COALESCE(l.plb_rr_mar, 0.0)) AS rr_mar,
                    SUM(COALESCE(l.plb_rr_apr, 0.0)) AS rr_apr,
                    SUM(COALESCE(l.plb_rr_may, 0.0)) AS rr_may,
                    SUM(COALESCE(l.plb_rr_jun, 0.0)) AS rr_jun,
                    SUM(COALESCE(l.plb_rr_jul, 0.0)) AS rr_jul,
                    SUM(COALESCE(l.plb_rr_aug, 0.0)) AS rr_aug,
                    SUM(COALESCE(l.plb_rr_sep, 0.0)) AS rr_sep,
                    SUM(COALESCE(l.plb_rr_oct, 0.0)) AS rr_oct,
                    SUM(COALESCE(l.plb_rr_nov, 0.0)) AS rr_nov,
                    SUM(COALESCE(l.plb_rr_dec, 0.0)) AS rr_dec,

                    SUM(COALESCE(l.plb_realized_revenue_2025, 0.0)) AS rr_total,
                    SUM(COALESCE(l.plb_cf, 0.0)) AS cf_total,

                    MAX(l.stage_id) AS stage_id,
                    MAX(l.company_id) AS company_id,
                    MAX(co.currency_id) AS company_currency
                FROM crm_lead l
                LEFT JOIN res_company co ON co.id = l.company_id
                WHERE l.partner_id IS NOT NULL
                GROUP BY l.partner_id
            )
        ''')
