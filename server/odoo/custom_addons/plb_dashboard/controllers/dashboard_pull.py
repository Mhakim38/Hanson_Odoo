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
                'user_id',
                'stage_id',
                'expected_revenue',
                'expected_revenue_annum',
                'realized_revenue_fy2025',
                'scope_of_service',
                'contract_type',
                'contract_months',
                'expected_start_date',
                'create_date',
                'date_go_live',
                'date_secured',
                'operating_profit_margin',
                'dept_region',
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

            # Extract salesperson (user_id)
            salesperson_name = ''
            if lead.get('user_id'):
                if isinstance(lead['user_id'], (list, tuple)):
                    salesperson_name = lead['user_id'][1] if len(lead['user_id']) > 1 else ''
                elif isinstance(lead['user_id'], dict):
                    salesperson_name = lead['user_id'].get('name', '')

            # Extract stage info
            stage_name = ''
            if lead.get('stage_id'):
                if isinstance(lead['stage_id'], (list, tuple)):
                    stage_name = lead['stage_id'][1] if len(lead['stage_id']) > 1 else ''
                elif isinstance(lead['stage_id'], dict):
                    stage_name = lead['stage_id'].get('name', '')

            # Normalize scope_of_service to a readable label (e.g., 'freight_forwarding' -> 'Freight Forwarding')
            raw_service = lead.get('scope_of_service')
            service_label = ''
            if raw_service:
                if isinstance(raw_service, (list, tuple)):
                    # sometimes search_read returns [key, label]
                    service_label = raw_service[1] if len(raw_service) > 1 else raw_service[0]
                else:
                    try:
                        service_label = str(raw_service).replace('_', ' ').title()
                    except Exception:
                        service_label = str(raw_service)

            # Dept/Region (selection) - preserve raw key and a readable label
            raw_dept = lead.get('dept_region')
            dept_label = ''
            if raw_dept:
                if isinstance(raw_dept, (list, tuple)):
                    dept_label = raw_dept[1] if len(raw_dept) > 1 else raw_dept[0]
                    dept_key = raw_dept[0] if len(raw_dept) > 0 else ''
                else:
                    # map known keys to labels; fallback to title-case
                    dept_key = raw_dept
                    try:
                        mapping = {
                            'central': 'Central',
                            'northern': 'Northern',
                            'southern': 'Southern',
                        }
                        dept_label = mapping.get(str(raw_dept), str(raw_dept).title())
                    except Exception:
                        dept_label = str(raw_dept)
            else:
                dept_key = ''

            # Financial calculations based on user's spec:
            # MAR (Monthly Annualized Revenue) = Expected Revenue / Contract Months
            # Realized Revenue (RR) = MAR * (12 - Expected Start Date month + 1) BUT capped by contract months
            # Carry Forward = Expected Revenue - RR

            sales = lead.get('expected_revenue', 0) or 0
            contract_months = lead.get('contract_months', 0) or 0
            expected_start = lead.get('expected_start_date')

            # Parse start month robustly (Odoo may return date or string)
            start_month = None
            if expected_start:
                if isinstance(expected_start, str):
                    try:
                        # expecting format YYYY-MM-DD
                        start_month = int(expected_start.split('-')[1])
                    except Exception:
                        start_month = None
                else:
                    try:
                        start_month = expected_start.month
                    except Exception:
                        start_month = None

            mar = 0.0
            if contract_months and contract_months > 0:
                try:
                    mar = float(sales) / float(contract_months)
                except Exception:
                    mar = 0.0

            # months available within FY (from start_month to Dec inclusive)
            months_available = 0
            if start_month and 1 <= start_month <= 12:
                months_available = max(0, 12 - start_month + 1)

            months_active_in_year = 0
            if contract_months and contract_months > 0 and months_available > 0:
                months_active_in_year = min(int(contract_months), int(months_available))

            realized_revenue = mar * months_active_in_year

            carry_forward = (float(sales) - realized_revenue) if sales is not None else 0.0

            # Build monthlyRevenue array for Jan..Dec
            monthly_revenue = []
            for m in range(1, 13):
                amount = 0.0
                if start_month and 1 <= start_month <= 12:
                    # month index relative to start (0-based)
                    rel_index = m - start_month
                    if rel_index >= 0 and rel_index < contract_months:
                        amount = mar
                monthly_revenue.append(amount)

            # Build row data
            row = {
                'id': lead.get('id'),
                'company': lead.get('name', ''),
                'customer': partner_name,
                'salesperson': salesperson_name,
                'stage': stage_name,
                'sales': sales,
                # remove annualRevenue (it's actually expected revenue)
                'realizedRevenue': realized_revenue,
                'carryForward': carry_forward,
                'mar': mar,
                'services': service_label,
                'contractType': lead.get('contract_type', ''),
                'contractMonths': contract_months,
                'profitMargin': lead.get('operating_profit_margin', 0),
                'expectedStartDate': lead.get('expected_start_date', ''),
                'createDate': lead.get('create_date', ''),
                'dateGoLive': lead.get('date_go_live', ''),
                'dateSecured': lead.get('date_secured', ''),
                # Monthly revenue calculated from MAR and expected start date
                'monthlyRevenue': monthly_revenue,
                # Dept/Region
                'deptRegion': dept_label,
                'deptRegionKey': dept_key,
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
            fields=['expected_revenue', 'expected_revenue_annum', 'realized_revenue_fy2025', 'contract_months', 'expected_start_date']
        )

        total_expected = 0.0
        total_realized = 0.0
        total_leads = 0

        for l in leads:
            sales = l.get('expected_revenue', 0) or 0
            contract_months = l.get('contract_months', 0) or 0
            expected_start = l.get('expected_start_date')

            # determine start month
            start_month = None
            if expected_start:
                if isinstance(expected_start, str):
                    try:
                        start_month = int(expected_start.split('-')[1])
                    except Exception:
                        start_month = None
                else:
                    try:
                        start_month = expected_start.month
                    except Exception:
                        start_month = None

            mar = 0.0
            if contract_months and contract_months > 0:
                try:
                    mar = float(sales) / float(contract_months)
                except Exception:
                    mar = 0.0

            months_available = 0
            if start_month and 1 <= start_month <= 12:
                months_available = max(0, 12 - start_month + 1)

            months_active_in_year = 0
            if contract_months and contract_months > 0 and months_available > 0:
                months_active_in_year = min(int(contract_months), int(months_available))

            realized = mar * months_active_in_year

            total_expected += float(sales)
            total_realized += float(realized)
            total_leads += 1

        return {
            'total_expected_revenue': total_expected,
            'total_annual_revenue': 0.0,
            'total_realized_revenue': total_realized,
            'lead_count': total_leads,
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

    @http.route('/plb/hit_rate', type='json', auth='user')
    def get_hit_rate(self, year=None):
        """
        Return monthly hit rate series for a given year.
        Hit Rate per month = Sum(expected_revenue for leads secured in month) / Sum(expected_revenue for leads created in month)
        Year param (int or string) is optional and defaults to current year.
        """
        from datetime import datetime
        Lead = request.env['crm.lead'].sudo()

        try:
            if year:
                y = int(year)
            else:
                y = datetime.now().year
        except Exception:
            y = datetime.now().year

        # initialize counters
        monthly_numer = [0.0] * 12  # secured in month
        monthly_denom = [0.0] * 12  # created in month

        leads = Lead.search_read(
            domain=[],
            fields=['expected_revenue', 'expected_start_date', 'date_secured']
        )

        for l in leads:
            sales = l.get('expected_revenue', 0) or 0
            # expected_start_date -> denominator (use expected start month to attribute expected revenue)
            es = l.get('expected_start_date')
            if es:
                try:
                    if isinstance(es, str):
                        # format YYYY-MM-DD or with time
                        dt = datetime.strptime(es.split('+')[0].split('Z')[0].strip(), '%Y-%m-%d %H:%M:%S') if ' ' in es else datetime.strptime(es, '%Y-%m-%d')
                    else:
                        dt = es
                    if dt.year == y:
                        m = dt.month
                        monthly_denom[m-1] += float(sales)
                except Exception:
                    # fallback: try find year/month via string
                    try:
                        s = str(es)
                        mm = int(s.split('-')[1])
                        yy = int(s.split('-')[0])
                        if yy == y:
                            monthly_denom[mm-1] += float(sales)
                    except Exception:
                        pass
            # date_secured -> numerator
            ds = l.get('date_secured')
            if ds:
                try:
                    if isinstance(ds, str):
                        dt = datetime.strptime(ds.split('+')[0].split('Z')[0].strip(), '%Y-%m-%d %H:%M:%S') if ' ' in ds else datetime.strptime(ds, '%Y-%m-%d')
                    else:
                        dt = ds
                    if dt.year == y:
                        m = dt.month
                        monthly_numer[m-1] += float(sales)
                except Exception:
                    try:
                        s = str(ds)
                        mm = int(s.split('-')[1])
                        yy = int(s.split('-')[0])
                        if yy == y:
                            monthly_numer[mm-1] += float(sales)
                    except Exception:
                        pass

        # calculate hit rate percentages (NULL when denom is zero)
        monthly_hit = []
        for i in range(12):
            denom = monthly_denom[i]
            numer = monthly_numer[i]
            if denom and denom > 0:
                monthly_hit.append((float(numer) / float(denom)) * 100.0)
            else:
                monthly_hit.append(None)

        months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        return {
            'year': y,
            'months': months,
            'numerator': monthly_numer,
            'denominator': monthly_denom,
            'hit_rate_percent': monthly_hit,
        }

    @http.route('/plb/hit_rate_by_region', type='json', auth='user')
    def get_hit_rate_by_region(self, year=None):
        """
        Return monthly hit rate series grouped by dept_region for a given year.
        Response format:
        {
            'year': y,
            'months': [...],
            'regions': {
                'central': { 'label': 'Central', 'numerator': [...], 'denominator': [...], 'hit_rate_percent': [...] },
                ...
            }
        }
        """
        from datetime import datetime
        Lead = request.env['crm.lead'].sudo()

        try:
            if year:
                y = int(year)
            else:
                y = datetime.now().year
        except Exception:
            y = datetime.now().year

        # Prepare mapping of known selection keys to labels
        mapping = {
            'central': 'Central',
            'northern': 'Northern',
            'southern': 'Southern',
        }

        # Regions map: key -> {'label':..., 'numerator':[0]*12, 'denominator':[0]*12}
        regions = {}

        leads = Lead.search_read(
            domain=[],
            fields=['expected_revenue', 'expected_start_date', 'date_secured', 'dept_region']
        )

        for l in leads:
            sales = l.get('expected_revenue', 0) or 0
            rkey = l.get('dept_region') or 'unknown'
            if isinstance(rkey, (list, tuple)):
                # search_read sometimes returns [key, label]
                if len(rkey) > 0:
                    rkey = rkey[0]
                else:
                    rkey = 'unknown'
            rkey = rkey if rkey else 'unknown'
            if rkey not in regions:
                regions[rkey] = {
                    'label': mapping.get(rkey, (str(rkey).title() if rkey != 'unknown' else 'Unknown')),
                    'numerator': [0.0] * 12,
                    'denominator': [0.0] * 12,
                }

            # expected_start_date -> denominator
            es = l.get('expected_start_date')
            if es:
                try:
                    if isinstance(es, str):
                        dt = datetime.strptime(es.split('+')[0].split('Z')[0].strip(), '%Y-%m-%d %H:%M:%S') if ' ' in es else datetime.strptime(es, '%Y-%m-%d')
                    else:
                        dt = es
                    if dt.year == y:
                        m = dt.month
                        regions[rkey]['denominator'][m-1] += float(sales)
                except Exception:
                    try:
                        s = str(es)
                        mm = int(s.split('-')[1])
                        yy = int(s.split('-')[0])
                        if yy == y:
                            regions[rkey]['denominator'][mm-1] += float(sales)
                    except Exception:
                        pass

            # date_secured -> numerator
            ds = l.get('date_secured')
            if ds:
                try:
                    if isinstance(ds, str):
                        dt = datetime.strptime(ds.split('+')[0].split('Z')[0].strip(), '%Y-%m-%d %H:%M:%S') if ' ' in ds else datetime.strptime(ds, '%Y-%m-%d')
                    else:
                        dt = ds
                    if dt.year == y:
                        m = dt.month
                        regions[rkey]['numerator'][m-1] += float(sales)
                except Exception:
                    try:
                        s = str(ds)
                        mm = int(s.split('-')[1])
                        yy = int(s.split('-')[0])
                        if yy == y:
                            regions[rkey]['numerator'][mm-1] += float(sales)
                    except Exception:
                        pass

        # compute hit rates for each region
        months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        for k, v in regions.items():
            monthly_hit = []
            for i in range(12):
                denom = v['denominator'][i]
                numer = v['numerator'][i]
                if denom and denom > 0:
                    monthly_hit.append((float(numer) / float(denom)) * 100.0)
                else:
                    monthly_hit.append(None)
            v['hit_rate_percent'] = monthly_hit

        return {
            'year': y,
            'months': months,
            'regions': regions,
        }
