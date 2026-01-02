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
                'realized_revenue',
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

            # Calculate week, month, quarter from expected_start_date
            week_of_year = None
            month_name = None
            quarter = None
            if expected_start:
                if isinstance(expected_start, str):
                    try:
                        from datetime import datetime
                        dt = datetime.strptime(expected_start, '%Y-%m-%d')
                        week_of_year = dt.isocalendar()[1]  # ISO week number
                        month_name = dt.strftime('%B')  # Full month name (e.g., 'January')
                        quarter = f"Q{(dt.month - 1) // 3 + 1}"  # Q1, Q2, Q3, Q4
                    except Exception:
                        pass
                else:
                    try:
                        week_of_year = expected_start.isocalendar()[1]
                        month_name = expected_start.strftime('%B')
                        quarter = f"Q{(expected_start.month - 1) // 3 + 1}"
                    except Exception:
                        pass

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
                # New fields: week, month, quarter
                'week': week_of_year,
                'month': month_name,
                'quarter': quarter,
            }
            rows.append(row)

        return {
            'rows': rows,
            'total_count': len(rows),
        }

    @http.route('/plb/stage_counts', type='json', auth='user')
    def get_stage_counts(self, year=None):
        """
        Get count of leads grouped by stage, filtered by expected_start_date year
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

        # Get all leads with stage and expected_start_date
        stages = Lead.search_read([], ['stage_id', 'expected_start_date'])

        # Count by stage, filtering by expected_start_date year
        stage_counts = {}
        for lead in stages:
            # Filter by expected_start_date year
            expected_start = lead.get('expected_start_date')
            start_year = None
            if expected_start:
                if isinstance(expected_start, str):
                    try:
                        start_year = int(expected_start.split('-')[0])
                    except Exception:
                        start_year = None
                else:
                    try:
                        start_year = expected_start.year
                    except Exception:
                        start_year = None

            # Only count leads with expected_start_date in the specified year
            if start_year != y:
                continue

            stage = lead.get('stage_id')
            if stage:
                stage_name = stage[1] if isinstance(stage, (list, tuple)) and len(stage) > 1 else str(stage)
                stage_counts[stage_name] = stage_counts.get(stage_name, 0) + 1

        return stage_counts

    @http.route('/plb/revenue_summary', type='json', auth='user')
    def get_revenue_summary(self, year=None):
        """
        Get aggregated revenue statistics, filtered by expected_start_date year
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

        leads = Lead.search_read(
            domain=[],
            fields=['expected_revenue', 'expected_revenue_annum', 'realized_revenue', 'contract_months', 'expected_start_date']
        )

        total_expected = 0.0
        total_realized = 0.0
        total_leads = 0

        for l in leads:
            expected_start = l.get('expected_start_date')

            # Filter by expected_start_date year
            start_year = None
            if expected_start:
                if isinstance(expected_start, str):
                    try:
                        start_year = int(expected_start.split('-')[0])
                    except Exception:
                        start_year = None
                else:
                    try:
                        start_year = expected_start.year
                    except Exception:
                        start_year = None

            # Only process leads with expected_start_date in the specified year
            if start_year != y:
                continue

            sales = l.get('expected_revenue', 0) or 0
            contract_months = l.get('contract_months', 0) or 0

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

    @http.route('/plb/pipeline_ytd_by_region', type='json', auth='user')
    def get_pipeline_ytd_by_region(self, year=None):
        """
        Return monthly pipeline (YTD) series grouped by dept_region for a given year.
        Similar to Total pipeline (YTD) but broken down by region.
        Response format:
        {
            'year': y,
            'months': [...],
            'regions': {
                'central': { 'label': 'Central', 'monthly': [...], 'ytd': [...] },
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

        # Regions map: key -> {'label':..., 'monthly':[0]*12}
        regions = {}

        leads = Lead.search_read(
            domain=[],
            fields=['expected_revenue', 'expected_start_date', 'dept_region']
        )

        for l in leads:
            sales = l.get('expected_revenue', 0) or 0
            rkey = l.get('dept_region') or 'unknown'
            if isinstance(rkey, (list, tuple)):
                if len(rkey) > 0:
                    rkey = rkey[0]
                else:
                    rkey = 'unknown'
            rkey = rkey if rkey else 'unknown'

            if rkey not in regions:
                regions[rkey] = {
                    'label': mapping.get(rkey, (str(rkey).title() if rkey != 'unknown' else 'Unknown')),
                    'monthly': [0.0] * 12,
                }

            # expected_start_date -> attribute revenue to that month
            es = l.get('expected_start_date')
            if es:
                try:
                    if isinstance(es, str):
                        dt = datetime.strptime(es.split('+')[0].split('Z')[0].strip(), '%Y-%m-%d %H:%M:%S') if ' ' in es else datetime.strptime(es, '%Y-%m-%d')
                    else:
                        dt = es
                    if dt.year == y:
                        m = dt.month
                        regions[rkey]['monthly'][m-1] += float(sales)
                except Exception:
                    try:
                        s = str(es)
                        mm = int(s.split('-')[1])
                        yy = int(s.split('-')[0])
                        if yy == y:
                            regions[rkey]['monthly'][mm-1] += float(sales)
                    except Exception:
                        pass

        # compute YTD cumulative for each region (convert to millions)
        months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        for k, v in regions.items():
            ytd = [0.0] * 12
            running = 0.0
            for i in range(12):
                running += v['monthly'][i]
                ytd[i] = running / 1e6  # convert to millions
            v['ytd'] = ytd

        return {
            'year': y,
            'months': months,
            'regions': regions,
        }

    @http.route('/plb/avg_pipeline_per_person', type='json', auth='user')
    def get_avg_pipeline_per_person(self, year=None):
        """
        Return average pipeline per person (YTD) for a given year.
        Formula: For each month, calculate total pipeline / number of unique salespersons with leads in that month
        Response format:
        {
            'year': y,
            'months': [...],
            'monthly': [...],  # monthly pipeline values
            'ytd': [...],      # YTD cumulative pipeline values
            'person_count': [...],  # number of people per month
            'avg_per_person': [...]  # average pipeline per person (YTD / person count)
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

        # Monthly aggregations
        monthly_pipeline = [0.0] * 12
        monthly_people = [set() for _ in range(12)]  # track unique user_ids per month

        leads = Lead.search_read(
            domain=[],
            fields=['expected_revenue', 'expected_start_date', 'user_id']
        )

        for l in leads:
            sales = l.get('expected_revenue', 0) or 0
            user_id = l.get('user_id')

            # Extract user_id (it's usually a tuple [id, name])
            uid = None
            if user_id:
                if isinstance(user_id, (list, tuple)) and len(user_id) > 0:
                    uid = user_id[0]
                elif isinstance(user_id, int):
                    uid = user_id

            # expected_start_date -> attribute revenue to that month
            es = l.get('expected_start_date')
            if es:
                try:
                    if isinstance(es, str):
                        dt = datetime.strptime(es.split('+')[0].split('Z')[0].strip(), '%Y-%m-%d %H:%M:%S') if ' ' in es else datetime.strptime(es, '%Y-%m-%d')
                    else:
                        dt = es
                    if dt.year == y:
                        m = dt.month
                        monthly_pipeline[m-1] += float(sales)
                        if uid:
                            monthly_people[m-1].add(uid)
                except Exception:
                    try:
                        s = str(es)
                        mm = int(s.split('-')[1])
                        yy = int(s.split('-')[0])
                        if yy == y:
                            monthly_pipeline[mm-1] += float(sales)
                            if uid:
                                monthly_people[mm-1].add(uid)
                    except Exception:
                        pass

        # Compute YTD cumulative pipeline (in millions)
        ytd = [0.0] * 12
        running = 0.0
        for i in range(12):
            running += monthly_pipeline[i]
            ytd[i] = running / 1e6  # convert to millions

        # Count unique people cumulative (YTD)
        cumulative_people = [set() for _ in range(12)]
        all_people = set()
        for i in range(12):
            all_people = all_people.union(monthly_people[i])
            cumulative_people[i] = all_people.copy()

        # Calculate avg pipeline per person
        person_count = [len(cumulative_people[i]) for i in range(12)]
        avg_per_person = [0.0] * 12
        for i in range(12):
            if person_count[i] > 0:
                avg_per_person[i] = ytd[i] / person_count[i]
            else:
                avg_per_person[i] = 0.0

        months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

        return {
            'year': y,
            'months': months,
            'monthly': monthly_pipeline,
            'ytd': ytd,
            'person_count': person_count,
            'avg_per_person': avg_per_person,
        }

    @http.route('/plb/avg_pipeline_per_person_by_region', type='json', auth='user')
    def get_avg_pipeline_per_person_by_region(self, year=None):
        """
        Return average pipeline per person (YTD) by region for a given year.
        Similar to avg_pipeline_per_person but broken down by dept_region.
        Response format:
        {
            'year': y,
            'months': [...],
            'regions': {
                'central': { 'label': 'Central', 'avg_per_person': [...] },
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

        # Regions map: key -> {'label':..., 'monthly_pipeline':[0]*12, 'monthly_people':[set()]*12}
        regions = {}

        leads = Lead.search_read(
            domain=[],
            fields=['expected_revenue', 'expected_start_date', 'user_id', 'dept_region']
        )

        for l in leads:
            sales = l.get('expected_revenue', 0) or 0
            user_id = l.get('user_id')
            rkey = l.get('dept_region') or 'unknown'

            if isinstance(rkey, (list, tuple)):
                if len(rkey) > 0:
                    rkey = rkey[0]
                else:
                    rkey = 'unknown'
            rkey = rkey if rkey else 'unknown'

            # Skip unknown region
            if rkey == 'unknown':
                continue

            if rkey not in regions:
                regions[rkey] = {
                    'label': mapping.get(rkey, str(rkey).title()),
                    'monthly_pipeline': [0.0] * 12,
                    'monthly_people': [set() for _ in range(12)],
                }

            # Extract user_id (it's usually a tuple [id, name])
            uid = None
            if user_id:
                if isinstance(user_id, (list, tuple)) and len(user_id) > 0:
                    uid = user_id[0]
                elif isinstance(user_id, int):
                    uid = user_id

            # expected_start_date -> attribute revenue to that month
            es = l.get('expected_start_date')
            if es:
                try:
                    if isinstance(es, str):
                        dt = datetime.strptime(es.split('+')[0].split('Z')[0].strip(), '%Y-%m-%d %H:%M:%S') if ' ' in es else datetime.strptime(es, '%Y-%m-%d')
                    else:
                        dt = es
                    if dt.year == y:
                        m = dt.month
                        regions[rkey]['monthly_pipeline'][m-1] += float(sales)
                        if uid:
                            regions[rkey]['monthly_people'][m-1].add(uid)
                except Exception:
                    try:
                        s = str(es)
                        mm = int(s.split('-')[1])
                        yy = int(s.split('-')[0])
                        if yy == y:
                            regions[rkey]['monthly_pipeline'][mm-1] += float(sales)
                            if uid:
                                regions[rkey]['monthly_people'][mm-1].add(uid)
                    except Exception:
                        pass

        # Compute YTD cumulative and avg per person for each region
        months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        for k, v in regions.items():
            # Compute YTD cumulative pipeline (in millions)
            ytd = [0.0] * 12
            running = 0.0
            for i in range(12):
                running += v['monthly_pipeline'][i]
                ytd[i] = running / 1e6  # convert to millions

            # Count unique people cumulative (YTD)
            cumulative_people = [set() for _ in range(12)]
            all_people = set()
            for i in range(12):
                all_people = all_people.union(v['monthly_people'][i])
                cumulative_people[i] = all_people.copy()

            # Calculate avg pipeline per person
            person_count = [len(cumulative_people[i]) for i in range(12)]
            avg_per_person = [0.0] * 12
            for i in range(12):
                if person_count[i] > 0:
                    avg_per_person[i] = ytd[i] / person_count[i]
                else:
                    avg_per_person[i] = 0.0

            v['ytd'] = ytd
            v['person_count'] = person_count
            v['avg_per_person'] = avg_per_person
            # Clean up temporary data
            del v['monthly_pipeline']
            del v['monthly_people']

        return {
            'year': y,
            'months': months,
            'regions': regions,
        }

    @http.route('/plb/gauge_data', type='json', auth='user')
    def get_gauge_data(self, year=None):
        """
        Fetch gauge meter data for dashboard (YTD Rev Target and Realized Rev Target)
        Returns percentage and values for both gauges
        """
        from datetime import datetime
        Lead = request.env['crm.lead'].sudo()
        TargetKPISettings = request.env['target.kpi.settings'].sudo()

        try:
            if year:
                y = int(year)
            else:
                y = datetime.now().year
        except Exception:
            y = datetime.now().year

        # Get company yearly target
        company_yearly_target = 0
        settings = TargetKPISettings.search([('year', '=', y)], limit=1)
        if settings:
            company_yearly_target = settings.yearly_target or 0
        else:
            # If no settings for this year, create with auto-populated employees
            settings = request.env['target.kpi.settings'].get_settings_for_year(y)
            company_yearly_target = settings.yearly_target or 0

        # Get all leads for contract stage
        Stage = request.env['crm.stage'].sudo()
        contract_stages = Stage.search([('name', 'ilike', 'contract')])
        contract_stage_ids = [s.id for s in contract_stages]

        leads = Lead.search_read(
            domain=[('stage_id', 'in', contract_stage_ids)] if contract_stage_ids else [('id', '=', False)],
            fields=['expected_revenue', 'expected_start_date', 'contract_months', 'realized_revenue']
        )

        total_expected_revenue = 0.0  # Direct sum of expected_revenue
        total_realized_revenue_ytd = 0.0  # Sum of MAR (Monthly Annualized Revenue)

        for lead in leads:
            sales = lead.get('expected_revenue', 0) or 0
            contract_months = lead.get('contract_months', 0) or 0
            expected_start = lead.get('expected_start_date')

            # Parse start date
            start_year = None
            start_month = None
            if expected_start:
                if isinstance(expected_start, str):
                    try:
                        parts = expected_start.split('-')
                        start_year = int(parts[0])
                        start_month = int(parts[1])
                    except Exception:
                        start_year = None
                        start_month = None
                else:
                    try:
                        start_year = expected_start.year
                        start_month = expected_start.month
                    except Exception:
                        start_year = None
                        start_month = None

            # Only process leads with expected_start_date in the specified year
            if start_year != y:
                continue

            # Accumulate expected revenue for YTD gauge (direct sum)
            total_expected_revenue += sales

            # Calculate MAR for realized revenue gauge
            mar = 0.0
            if contract_months and contract_months > 0:
                try:
                    mar = float(sales) / float(contract_months)
                except Exception:
                    mar = 0.0

            # Calculate total MAR for months in the year
            if start_month and 1 <= start_month <= 12:
                for month_idx in range(12):
                    actual_month = month_idx + 1
                    if actual_month >= start_month:
                        months_from_start = actual_month - start_month
                        if months_from_start < contract_months:
                            total_realized_revenue_ytd += mar

        # Calculate percentages
        ytd_percentage = 0.0
        realized_percentage = 0.0

        if company_yearly_target > 0:
            ytd_percentage = (total_expected_revenue / company_yearly_target) * 100
            realized_percentage = (total_realized_revenue_ytd / company_yearly_target) * 100

        return {
            'year': y,
            'company_yearly_target': company_yearly_target / 1000000,  # In millions
            'total_ytd_revenue': total_expected_revenue / 1000000,  # Expected Revenue in millions
            'total_realized_revenue': total_realized_revenue_ytd / 1000000,  # Realized revenue in millions
            'ytd_percentage': ytd_percentage,
            'realized_percentage': realized_percentage,
        }

