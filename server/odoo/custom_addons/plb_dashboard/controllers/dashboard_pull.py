from odoo import http
from odoo.http import request


class PLBDashboardController(http.Controller):

    @http.route('/plb/dashboard_data', type='json', auth='user')
    def get_dashboard_data(self):
        """
        Fetch aggregated data from crm.lead for the PLB dashboard.
        Returns structured data similar to the mock rows in dashboard.js
        """
        Lead = request.env['crm.lead'].sudo()

        # Fetch all leads with necessary fields
        leads = Lead.search_read(
            domain=[],
            fields=[
                'name',
                'partner_id',
                'stage_id',
                'expected_revenue',
                'expected_revenue_annum',
                'realized_revenue_fy2025',
                'scope_of_service',
                'contract_type',
                'contract_months',
                'expected_start_date',
                'date_go_live',
                'date_secured',
                'dept_region',
                'operating_profit_margin',
            ]
        )

        # Transform the data into dashboard rows
        rows = []
        for lead in leads:
            # Extract partner info
            partner_name = ''
            if lead.get('partner_id'):
                if isinstance(lead['partner_id'], (list, tuple)):
                    partner_name = lead['partner_id'][1] if len(lead['partner_id']) > 1 else ''
                elif isinstance(lead['partner_id'], dict):
                    partner_name = lead['partner_id'].get('name', '')

            # Extract stage info
            stage_name = ''
            if lead.get('stage_id'):
                if isinstance(lead['stage_id'], (list, tuple)):
                    stage_name = lead['stage_id'][1] if len(lead['stage_id']) > 1 else ''
                elif isinstance(lead['stage_id'], dict):
                    stage_name = lead['stage_id'].get('name', '')

            # Build row data
            row = {
                'id': lead.get('id'),
                'company': lead.get('name', ''),
                'customer': partner_name,
                'stage': stage_name,
                'sales': lead.get('expected_revenue', 0),
                'annualRevenue': lead.get('expected_revenue_annum', 0),
                'realizedRevenue': lead.get('realized_revenue_fy2025', 0),
                'services': lead.get('scope_of_service', ''),
                'contractType': lead.get('contract_type', ''),
                'contractMonths': lead.get('contract_months', 0),
                'deptRegion': lead.get('dept_region', ''),
                'profitMargin': lead.get('operating_profit_margin', 0),
                'expectedStartDate': lead.get('expected_start_date', ''),
                'dateGoLive': lead.get('date_go_live', ''),
                'dateSecured': lead.get('date_secured', ''),
                # Monthly revenue placeholder - will be calculated separately if needed
                'monthlyRevenue': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            }
            rows.append(row)

        return {
            'rows': rows,
            'total_count': len(rows),
        }

    @http.route('/plb/stage_counts', type='json', auth='user')
    def get_stage_counts(self):
        """
        Get count of leads grouped by stage
        """
        Lead = request.env['crm.lead'].sudo()

        # Get all stages
        stages = Lead.search_read([], ['stage_id'])

        # Count by stage
        stage_counts = {}
        for lead in stages:
            stage = lead.get('stage_id')
            if stage:
                stage_name = stage[1] if isinstance(stage, (list, tuple)) and len(stage) > 1 else str(stage)
                stage_counts[stage_name] = stage_counts.get(stage_name, 0) + 1

        return stage_counts

    @http.route('/plb/revenue_summary', type='json', auth='user')
    def get_revenue_summary(self):
        """
        Get aggregated revenue statistics
        """
        Lead = request.env['crm.lead'].sudo()

        leads = Lead.search_read(
            domain=[],
            fields=['expected_revenue', 'expected_revenue_annum', 'realized_revenue_fy2025']
        )

        total_expected = sum(l.get('expected_revenue', 0) for l in leads)
        total_annual = sum(l.get('expected_revenue_annum', 0) for l in leads)
        total_realized = sum(l.get('realized_revenue_fy2025', 0) for l in leads)

        return {
            'total_expected_revenue': total_expected,
            'total_annual_revenue': total_annual,
            'total_realized_revenue': total_realized,
            'lead_count': len(leads),
        }

    @http.route('/plb/customers', type='json', auth='user')
    def get_customers(self):
        """
        Get unique customers from crm.lead partner_id
        """
        Lead = request.env['crm.lead'].sudo()

        leads = Lead.search_read(
            domain=[('partner_id', '!=', False)],
            fields=['partner_id']
        )

        # Deduplicate partners
        partner_map = {}
        for lead in leads:
            partner = lead.get('partner_id')
            if partner and isinstance(partner, (list, tuple)) and len(partner) >= 2:
                pid = partner[0]
                pname = partner[1]
                if pid not in partner_map:
                    partner_map[pid] = {'id': pid, 'name': pname}

        customers = sorted(partner_map.values(), key=lambda x: x['name'])

        return {
            'customers': customers,
            'count': len(customers),
        }

