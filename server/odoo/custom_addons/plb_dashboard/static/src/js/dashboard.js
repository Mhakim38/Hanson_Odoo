/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, xml, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PLBDashboard extends Component {
    setup() {
        // reactive state
        this.state = useState({
            rows: [],
            years: [],
            // Total pipeline YTD series state
            pipelineSeries: { pathSegments: [], prevPathSegments: [], points: [], prevPoints: [], months: [], ticks: [], maxVal: 1 },
            // Hit rate series state
            hitRate: { year: null, months: [], hit_rate_percent: [], numerator: [], denominator: [] },
            hitRateSeries: { pathSegments: [], points: [] },
            // Hit rate by region state
            hitRateByRegion: { year: null, months: [], regions: {} },
            hitRateRegionSeries: { regions: [] },
            // filter options and current selection
            salespersons: [],
            stages: [],
            services: [],
            // default Year is current year — remove 'All' option from years
            filters: { salesperson: 'All', stage: 'All', service: 'All', year: String((new Date()).getFullYear()) },
            customers: [],
            stageCounts: {},
            revenueSummary: {
                total_expected_revenue: 0,
                total_annual_revenue: 0,
                total_realized_revenue: 0,
                lead_count: 0,
            },
            // monthly subtotals for Jan..Dec and cumulative
            monthlySubtotals: Array(12).fill(0),
            monthlyCumulative: Array(12).fill(0),
            // totalCarryForward is null when no data; computed after loading rows
            totalCarryForward: null,
            // Precomputed pie chart segments for services
            serviceSegments: [],
            // Tooltip for pie chart
            tooltip: { visible: false, left: 0, top: 0, title: '', value: 0, percent: 0, key: null },
            loading: true,
        });

        // rpc service for fetching model data
        this.rpc = useService("rpc");

        // Fetch all dashboard data on mount. Ensure default Year filter is current year.
        onMounted(async () => {
            if (!this.state.filters.year || this.state.filters.year === 'All') {
                this.state.filters.year = String((new Date()).getFullYear());
            }
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        try {
            this.state.loading = true;

            // Fetch dashboard data from controller endpoint (similar to /titah/status_counts)
            const dashboardData = await this.rpc("/plb/dashboard_data");
            if (dashboardData && dashboardData.rows) {
                this.state.rows = dashboardData.rows;
            }

            // Fetch customers
            const customersData = await this.rpc("/plb/customers");
            if (customersData && customersData.customers) {
                this.state.customers = customersData.customers;
            }

            // Fetch stage counts
            const stageCounts = await this.rpc("/plb/stage_counts");
            if (stageCounts) {
                this.state.stageCounts = stageCounts;
            }

            // Fetch revenue summary
            const revenueSummary = await this.rpc("/plb/revenue_summary");
            if (revenueSummary) {
                this.state.revenueSummary = revenueSummary;
            }

            // After rows loaded, compute filter options and monthly subtotals
            this.computeFilterOptions();
            this.computeTotals();
            // Compute hit rate and pie for the active year. Prefer server aggregation (more reliable),
            // but fall back to client-side computation from loaded rows if the server returns no data.
            const activeYear = (this.state.filters && this.state.filters.year && this.state.filters.year !== 'All') ? Number(this.state.filters.year) : (new Date()).getFullYear();
            try {
                // Try server-side first
                await this.loadHitRate(activeYear);
                // If server returned no meaningful series, fallback to client computation
                const s = this.state.hitRateSeries || {};
                if ((!s.pathSegments || s.pathSegments.length === 0) && (!s.prevPathSegments || s.prevPathSegments.length === 0)) {
                    console.debug('Server hit rate empty, falling back to client computation');
                    await this.loadHitRateFromRows(activeYear);
                }
            } catch (err) {
                console.warn('Server hit rate RPC failed, falling back to client-side computation', err);
                await this.loadHitRateFromRows(activeYear);
            }
             // load hit rate by region
             await this.loadHitRateByRegion(activeYear);
             // load total pipeline series (YTD)
             await this.loadPipelineSeries(activeYear);

            console.debug('PLB Dashboard loaded:', {
                rows: this.state.rows.length,
                customers: this.state.customers.length,
                stageCounts: this.state.stageCounts,
                revenueSummary: this.state.revenueSummary,
            });
            console.debug('PLB Dashboard state after load:', { filters: this.state.filters, hitRateExists: !!this.state.hitRate, hitRateByRegionExists: !!this.state.hitRateByRegion });

        } catch (err) {
            console.error('Failed to load PLB dashboard data:', err);
        } finally {
            this.state.loading = false;
        }
    }

    // Build unique filter option lists from rows
    computeFilterOptions() {
        const salesSet = new Set();
        const stageSet = new Set();
        const serviceSet = new Set();
        (this.state.rows || []).forEach(r => {
            if (r.salesperson) { salesSet.add(r.salesperson); }
            if (r.stage) { stageSet.add(r.stage); }
            if (r.services) { serviceSet.add(r.services); }
        });
        this.state.salespersons = ['All', ...Array.from(salesSet).sort()];
        this.state.stages = ['All', ...Array.from(stageSet).sort()];
        this.state.services = ['All', ...Array.from(serviceSet).sort()];
        // compute year options as well
        this.computeYearOptions();
    }

    // Scan rows for date-like fields and build a list of years
    computeYearOptions() {
        // Provide a stable year range from 2000 up to the current year (inclusive)
        const now = new Date();
        const currentYear = now.getFullYear();
        const years = [];
        for (let y = currentYear; y >= 2000; y--) {
            years.push(String(y));
        }
        // DO NOT include 'All' — the dropdown should only show actual years and default to current year
        this.state.years = years;
    }

    // Return rows filtered by current filters
    getFilteredRows() {
        const f = this.state.filters || {};
        return (this.state.rows || []).filter(r => {
            if (f.salesperson && f.salesperson !== 'All') {
                if ((r.salesperson || '') !== f.salesperson) return false;
            }
            if (f.stage && f.stage !== 'All') {
                if ((r.stage || '') !== f.stage) return false;
            }
            if (f.service && f.service !== 'All') {
                if ((r.services || '') !== f.service) return false;
            }
            if (f.year && f.year !== 'All') {
                // Filter by createDate (server-provided create_date) -> row.createDate
                const cd = r.createDate;
                if (!cd) return false;
                let year = null;
                if (typeof cd === 'string') {
                    const m = cd.match(/(20\d{2}|19\d{2})/);
                    if (m) { year = m[0]; }
                } else if (cd instanceof Date) {
                    year = String(cd.getFullYear());
                }
                if (String(year) !== String(f.year)) return false;
            }
            return true;
        });
    }

    // Table rows: filters include salesperson/stage/service and YEAR.
    // When year is 'All' treat it as the current year for table display.
    getFilteredTableRows() {
        const f = this.state.filters || {};
        const yearFilter = (f.year && f.year !== 'All') ? Number(f.year) : (new Date()).getFullYear();
        return (this.state.rows || []).filter(r => {
            if (f.salesperson && f.salesperson !== 'All') {
                if ((r.salesperson || '') !== f.salesperson) return false;
            }
            if (f.stage && f.stage !== 'All') {
                if ((r.stage || '') !== f.stage) return false;
            }
            if (f.service && f.service !== 'All') {
                if ((r.services || '') !== f.service) return false;
            }
            // Table filtering is strictly based on Expected Start Date year per your requirement.
            const es = r.expectedStartDate || r.expectedStartDate || r.expectedStartDate || '';
            if (!es) return false;
            let yy = null;
            if (typeof es === 'string') {
                // try ISO-like pattern first
                const m = es.match(/(\d{4})-(\d{2})-(\d{2})/);
                if (m) { yy = Number(m[1]); }
                else {
                    const m2 = es.match(/(20\d{2}|19\d{2})/);
                    if (m2) yy = Number(m2[0]);
                }
            } else if (es instanceof Date) {
                yy = es.getFullYear();
            }
            return yy === yearFilter;
        });
    }

    // Chart rows: filters only by salesperson/stage/service (year is provided separately when computing series)
    getFilteredChartRows() {
        const f = this.state.filters || {};
        return (this.state.rows || []).filter(r => {
            if (f.salesperson && f.salesperson !== 'All') {
                if ((r.salesperson || '') !== f.salesperson) return false;
            }
            if (f.stage && f.stage !== 'All') {
                if ((r.stage || '') !== f.stage) return false;
            }
            if (f.service && f.service !== 'All') {
                if ((r.services || '') !== f.service) return false;
            }
            return true;
        });
    }

    // Set a filter and recompute totals and charts (accept either event or direct value)
    setFilter = (name, evOrValue) => {
        const value = (evOrValue && evOrValue.target && evOrValue.target.value !== undefined) ? evOrValue.target.value : evOrValue;
        this.state.filters[name] = value;
        // recompute monthly totals (table) based on filtered rows
        this.computeTotals();
        // reload hit rate and pie based on filters (use selected year or current year)
        const yearToLoad = (this.state.filters && this.state.filters.year && this.state.filters.year !== 'All') ? Number(this.state.filters.year) : (new Date()).getFullYear();
        this.loadHitRateFromRows(yearToLoad);
        this.loadHitRateByRegion(yearToLoad);
        this.loadPipelineSeries(yearToLoad);
    }

    // Reset all filters to 'All' (include year) and recompute totals
    resetFilters = () => {
        // Reset filters but default year to the current year (no 'All')
        this.state.filters = { salesperson: 'All', stage: 'All', service: 'All', year: String((new Date()).getFullYear()) };
        this.computeTotals();
        const yearToLoad = Number(this.state.filters.year);
        this.loadHitRateFromRows(yearToLoad);
        this.loadHitRateByRegion(yearToLoad);
        this.loadPipelineSeries(yearToLoad);
    }

    // Helper: format a numeric value with 2 decimals, or return 'NULL' for missing/false values
    formatNumber(value) {
        if (value === false || value === null || value === undefined || value === '') {
            return 'NULL';
        }
        const n = Number(value);
        if (Number.isNaN(n)) {
            return 'NULL';
        }
        // Use locale-aware formatting with thousands separators and exactly two decimals
        return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    // Helper: format currency with RM prefix when value exists, otherwise 'NULL'
    formatCurrency(value) {
        const formatted = this.formatNumber(value);
        return formatted === 'NULL' ? 'NULL' : `${formatted}`;
    }

    // Helper: format text fields, show NULL for falsy (but allow 0)
    formatText(value) {
        if (value === false || value === null || value === undefined || value === '') {
            return 'NULL';
        }
        return value;
    }

    // Helper: format service key (e.g. 'freight_forwarding' -> 'Freight Forwarding')
    formatServiceName(key) {
        if (!key && key !== 0) return 'NULL';
        const s = String(key);
        // replace underscores, dashes with space and capitalize words
        return s.replace(/[_-]+/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase());
    }

    // Internal helper to build an SVG arc path for a pie slice (expects angles in radians)
    buildArcPath(cx, cy, r, startAngle, endAngle) {
        const startX = cx + r * Math.cos(startAngle);
        const startY = cy + r * Math.sin(startAngle);
        const endX = cx + r * Math.cos(endAngle);
        const endY = cy + r * Math.sin(endAngle);
        const largeArcFlag = (endAngle - startAngle) > Math.PI ? 1 : 0;
        return `M ${cx} ${cy} L ${startX} ${startY} A ${r} ${r} 0 ${largeArcFlag} 1 ${endX} ${endY} Z`;
    }

    // Compute monthly subtotals (Jan..Dec), running cumulative totals, total carry forward and service pie segments
    computeTotals() {
        const subtotals = Array(12).fill(0);
        //        let totalCarry = 0;

        // Sum carry forward for the filtered rows so the top card can display it
        let totalCarry = 0;
        let carryCount = 0;
        const rows = this.getFilteredTableRows();
        (rows || []).forEach(row => {
            // row.monthlyRevenue expected to be array of 12 numbers
            const months = Array.isArray(row.monthlyRevenue) ? row.monthlyRevenue : [];
            for (let i = 0; i < 12; i++) {
                const v = months[i] != null ? Number(months[i]) : 0;
                subtotals[i] += Number.isFinite(v) ? v : 0;
            }
            // accumulate carryForward (if present and numeric)
            const cfRaw = row.carryForward;
            if (cfRaw !== null && cfRaw !== undefined && cfRaw !== false && cfRaw !== '') {
                const cf = Number(cfRaw);
                if (Number.isFinite(cf)) {
                    totalCarry += cf;
                    carryCount += 1;
                }
            }
        });

        // build cumulative
        const cumulative = Array(12).fill(0);
        let run = 0;
        for (let i = 0; i < 12; i++) {
            run += subtotals[i];
            cumulative[i] = run;
        }

        // --- Build service totals and pie segments (based on wins in the selected year) ---
        const serviceMap = {}; // key -> numeric total
        let grandTotal = 0;
        const yearFilter = (this.state.filters && this.state.filters.year && this.state.filters.year !== 'All') ? Number(this.state.filters.year) : (new Date()).getFullYear();
        // Use chart-filtered rows (salesperson/stage/service) but aggregate only where dateSecured falls in yearFilter
        const chartRows = this.getFilteredChartRows();
        (chartRows || []).forEach(row => {
            const ds = row.dateSecured || row.dateSecured;
            let yy = null;
            if (ds) {
                if (typeof ds === 'string') {
                    const m = ds.match(/(20\d{2}|19\d{2})/);
                    if (m) yy = Number(m[0]);
                } else if (ds instanceof Date) {
                    yy = ds.getFullYear();
                }
            }
            if (yy !== yearFilter) return; // only count wins in selected year
            const key = (row.services || 'Unknown');
            const valRaw = row.sales;
            const val = (valRaw === false || valRaw === null || valRaw === undefined || valRaw === '') ? 0 : Number(valRaw);
            const num = Number.isFinite(val) ? val : 0;
            serviceMap[key] = (serviceMap[key] || 0) + num;
            grandTotal += num;
        });

        const colors = ["#0d6efd", "#198754", "#dc3545", "#6f42c1", "#fd7e14", "#20c997", "#6610f2", "#e83e8c", "#0dcaf0", "#adb5bd"];
        const segments = [];
        let angleStart = -Math.PI / 2; // start at top
        // Balanced radius so pie fits neatly within the 320x320 viewBox and card body
        const radius = 105;
        const cx = 0, cy = 0;
        const keys = Object.keys(serviceMap).sort();
        keys.forEach((k, idx) => {
            const v = serviceMap[k] || 0;
            if (!Number.isFinite(v) || v <= 0) {
                return; // skip zero entries to avoid degenerate arcs
            }
            const portion = grandTotal > 0 ? v / grandTotal : 0;
            const angle = portion * Math.PI * 2;
            const angleEnd = angleStart + angle;
            const path = this.buildArcPath(cx, cy, radius, angleStart, angleEnd);
            segments.push({
                name: this.formatServiceName(k),
                rawKey: k,
                value: v,
                percent: grandTotal > 0 ? (portion * 100) : 0,
                color: colors[idx % colors.length],
                path: path,
            });
            angleStart = angleEnd;
        });

        // Write back to reactive state
        this.state.monthlySubtotals = subtotals;
        this.state.monthlyCumulative = cumulative;
        // Only set totalCarryForward if at least one row provided a numeric carryForward; otherwise show NULL
        this.state.totalCarryForward = carryCount > 0 ? totalCarry : null;
        // set pie segments (empty if no positive data)
        this.state.serviceSegments = segments;
    }

    // Compute hit-rate numerator/denominator arrays from the currently loaded rows (apply chart filters)
    loadHitRateFromRows = async (year) => {
        try {
            if (!year || year === 'All') year = (new Date()).getFullYear();
            const lastYear = Number(year) - 1;
            console.debug('loadHitRateFromRows: computing for year', year, 'lastYear', lastYear, 'filtered rows', (this.getFilteredChartRows() || []).length);
            // build numerator/denominator for both years from filtered chart rows
            const rows = this.getFilteredChartRows();
            const computeForYear = (y) => {
                const monthly_numer = Array(12).fill(0);
                const monthly_denom = Array(12).fill(0);
                rows.forEach(r => {
                    const sales = (r.sales === false || r.sales === null || r.sales === undefined || r.sales === '') ? 0 : Number(r.sales) || 0;
                    // denom: expected_start_date
                    const es = r.expectedStartDate || r.expected_start_date || r.expectedStart || r.expected_start || r.expected_start_date || r.expectedStartDate;
                    if (es) {
                        let dt = null;
                        if (typeof es === 'string') {
                            const m = es.match(/(\d{4})-(\d{2})-(\d{2})/);
                            if (m) { dt = { year: Number(m[1]), month: Number(m[2]) }; }
                        } else if (es instanceof Date) {
                            dt = { year: es.getFullYear(), month: es.getMonth() + 1 };
                        }
                        if (dt && dt.year === Number(y)) {
                            monthly_denom[dt.month - 1] += Number(sales);
                        }
                    }
                    // numer: dateSecured
                    const ds = r.dateSecured || r.date_secured || r.dateSecured || r.date_secured;
                    if (ds) {
                        let dt2 = null;
                        if (typeof ds === 'string') {
                            const m2 = ds.match(/(\d{4})-(\d{2})-(\d{2})/);
                            if (m2) { dt2 = { year: Number(m2[1]), month: Number(m2[2]) }; }
                        } else if (ds instanceof Date) {
                            dt2 = { year: ds.getFullYear(), month: ds.getMonth() + 1 };
                        }
                        if (dt2 && dt2.year === Number(y)) {
                            monthly_numer[dt2.month - 1] += Number(sales);
                        }
                    }
                });
                const monthly_hit = [];
                for (let i = 0; i < 12; i++) {
                    const denom = monthly_denom[i];
                    const numer = monthly_numer[i];
                    if (denom && denom > 0) monthly_hit.push((Number(numer) / Number(denom)) * 100.0);
                    else if (numer && numer > 0) monthly_hit.push(0);
                    else monthly_hit.push(null);
                }
                return {
                    year: Number(y),
                    months: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
                    numerator: monthly_numer,
                    denominator: monthly_denom,
                    hit_rate_percent: monthly_hit,
                };
            };

            const resp = computeForYear(year);
            const respPrev = computeForYear(lastYear);
            this.state.hitRate = resp;
            this.state.hitRatePrev = respPrev;
            this.computeHitRateSeries(resp, respPrev);
            console.debug('loadHitRateFromRows: hitRate, hitRatePrev', resp, respPrev);
        } catch (e) {
            console.error('loadHitRateFromRows error', e);
            this.state.hitRateSeries = { pathSegments: [], prevPathSegments: [], points: [], prevPoints: [], months: [] };
        }
    }

    // Compute SVG series for current and previous year responses
    computeHitRateSeries = (resp, respPrev) => {
        try {
            console.debug('computeHitRateSeries called', { resp, respPrev });
            const months = resp && resp.months ? resp.months : (respPrev && respPrev.months ? respPrev.months : ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']);
            // Use same vertical sizing as Dept/Region chart: SVG height 320, axis from y=20..260 -> plotH = 240
            const marginLeft = 60, marginTop = 20, marginRight = 20, marginBottom = 60; // for the 600x320 chart
            const plotW = 600 - marginLeft - marginRight; // 520
            const plotH = 320 - marginTop - marginBottom; // 320 - 20 - 60 = 240
            const monthPositions = [];
            for (let i = 0; i < 12; i++) {
                const x = marginLeft + (i * (plotW / 11));
                monthPositions.push({ x: x, label: months[i] || '' });
            }

            // --- Current year series ---
            const sCur = { segments: [], flatPoints: [] };
            const valsCur = Array.isArray(resp.hit_rate_percent) && resp.hit_rate_percent.length === 12 ? resp.hit_rate_percent : Array(12).fill(null);
            for (let i = 0; i < 12; i++) {
                const v = valsCur[i];
                if (v === null || v === undefined) { sCur.flatPoints.push(null); continue; }
                const percent = Number(v);
                const clamped = Number.isFinite(percent) ? Math.max(0, Math.min(100, percent)) : 0;
                const x = monthPositions[i].x;
                const y = marginTop + ((100 - clamped) / 100) * plotH;
                sCur.flatPoints.push({ x: x, y: y, value: clamped, month: months[i], idx: i, numer: resp.numerator ? resp.numerator[i] : 0, denom: resp.denominator ? resp.denominator[i] : 0 });
                if (i === 0) continue; // skip first segment (0..1)
                // build line segments (M x1 y1 L x2 y2) for the path
                const p0 = sCur.flatPoints[i - 1];
                const p1 = sCur.flatPoints[i];
                if (p0 && p1) {
                    sCur.segments.push({ d: `M ${p0.x} ${p0.y} L ${p1.x} ${p1.y}` });
                }
            }

            // --- Previous year series ---
            const sPrev = { segments: [], flatPoints: [] };
            const valsPrev = Array.isArray(respPrev.hit_rate_percent) && respPrev.hit_rate_percent.length === 12 ? respPrev.hit_rate_percent : Array(12).fill(null);
            for (let i = 0; i < 12; i++) {
                const v = valsPrev[i];
                if (v === null || v === undefined) { sPrev.flatPoints.push(null); continue; }
                const percent = Number(v);
                const clamped = Number.isFinite(percent) ? Math.max(0, Math.min(100, percent)) : 0;
                const x = monthPositions[i].x;
                const y = marginTop + ((100 - clamped) / 100) * plotH;
                sPrev.flatPoints.push({ x: x, y: y, value: clamped, month: months[i], idx: i, numer: respPrev.numerator ? respPrev.numerator[i] : 0, denom: respPrev.denominator ? respPrev.denominator[i] : 0 });
                if (i === 0) continue; // skip first segment (0..1)
                // build line segments (M x1 y1 L x2 y2) for the path
                const p0 = sPrev.flatPoints[i - 1];
                const p1 = sPrev.flatPoints[i];
                if (p0 && p1) {
                    sPrev.segments.push({ d: `M ${p0.x} ${p0.y} L ${p1.x} ${p1.y}` });
                }
            }

             // Remove any null placeholders from the flatPoints arrays so template keys (pt.idx) won't access properties of null
             const filteredPoints = sCur.flatPoints.filter(p => p !== null && p !== undefined);
             const filteredPrevPoints = sPrev.flatPoints.filter(p => p !== null && p !== undefined);
             this.state.hitRateSeries = {
                 pathSegments: sCur.segments.map(s => ({ d: s.d, color: '#0d6efd' })),
                 prevPathSegments: sPrev.segments.map(s => ({ d: s.d, color: '#6c757d' })),
                 points: filteredPoints,
                 prevPoints: filteredPrevPoints,
                 months: monthPositions,
             };
             console.debug('computeHitRateSeries: computed hitRateSeries', this.state.hitRateSeries);
        } catch (e) {
            console.error('computeHitRateSeries error', e);
            this.state.hitRateSeries = { pathSegments: [], prevPathSegments: [], points: [], prevPoints: [], months: [] };
        }
    }

    // Load hit rate data for the requested year and the previous year, then compute both series
    loadHitRate = async (year) => {
        try {
            if (!year || year === 'All') {
                year = (new Date()).getFullYear();
            }
            const lastYear = Number(year) - 1;
            // fetch both years in parallel
            const [resp, respPrev] = await Promise.all([
                this.rpc('/plb/hit_rate', { year: year }),
                this.rpc('/plb/hit_rate', { year: lastYear }),
            ]);
            this.state.hitRate = resp || { year: year, months: [], hit_rate_percent: [], numerator: [], denominator: [] };
            this.state.hitRatePrev = respPrev || { year: lastYear, months: [], hit_rate_percent: [], numerator: [], denominator: [] };
            // compute both series for plotting
            this.computeHitRateSeries(this.state.hitRate, this.state.hitRatePrev);
        } catch (e) {
            console.error('Failed to load hit rate', e);
            this.state.hitRate = { year: year, months: [], hit_rate_percent: [], numerator: [], denominator: [] };
            this.state.hitRatePrev = { year: Number(year) - 1, months: [], hit_rate_percent: [], numerator: [], denominator: [] };
            this.state.hitRateSeries = { pathSegments: [], prevPathSegments: [], points: [], prevPoints: [], months: [] };
        }
    }

    // Load hit rate by region (computed client-side from filtered rows so filters apply)
    loadHitRateByRegion = async (year) => {
        try {
            if (!year || year === 'All') year = (new Date()).getFullYear();
            const curYear = Number(year);
            const prevYear = curYear - 1;
            const rows = this.getFilteredChartRows();
            // build regions map similar to server endpoint, but store both current and previous year buckets
            const mapping = { central: 'Central', northern: 'Northern', southern: 'Southern' };
            const regions = {};

            const safeNum = (v) => { const n = (v === false || v === null || v === undefined || v === '') ? 0 : Number(v); return Number.isFinite(n) ? n : 0; };

            rows.forEach(r => {
                const sales = safeNum(r.sales);
                let rkey = r.deptRegionKey || r.deptRegion || 'unknown';
                if (!rkey) rkey = 'unknown';
                if (Array.isArray(rkey)) rkey = rkey[0] || 'unknown';
                if (!(rkey in regions)) {
                    regions[rkey] = {
                        label: mapping[rkey] || (typeof r.deptRegion === 'string' ? r.deptRegion : String(rkey).charAt(0).toUpperCase() + String(rkey).slice(1)),
                        numerator: Array(12).fill(0),
                        denominator: Array(12).fill(0),
                        numeratorPrev: Array(12).fill(0),
                        denominatorPrev: Array(12).fill(0),
                    };
                }

                // expectedStartDate -> denominator for either current or prev year
                const es = r.expectedStartDate || r.expected_start_date || r.expectedStart || r.expected_start || r.expected_start_date || r.expectedStartDate;
                if (es) {
                    let yy = null, mm = null;
                    if (typeof es === 'string') {
                        const m = es.match(/(\d{4})-(\d{2})-(\d{2})/);
                        if (m) { yy = Number(m[1]); mm = Number(m[2]); }
                        else {
                            const m2 = es.match(/(20\d{2}|19\d{2})/);
                            if (m2) yy = Number(m2[0]);
                        }
                    } else if (es instanceof Date) {
                        yy = es.getFullYear(); mm = es.getMonth() + 1;
                    }
                    if (mm && (yy === curYear)) {
                        regions[rkey].denominator[mm-1] += sales;
                    } else if (mm && (yy === prevYear)) {
                        regions[rkey].denominatorPrev[mm-1] += sales;
                    }
                }

                // date_secured -> numerator
                const ds = r.dateSecured || r.date_secured || r.dateSecured;
                if (ds) {
                    let yy = null, mm = null;
                    if (typeof ds === 'string') {
                        const m = ds.match(/(\d{4})-(\d{2})-(\d{2})/);
                        if (m) { yy = Number(m[1]); mm = Number(m[2]); }
                        else {
                            const m2 = ds.match(/(20\d{2}|19\d{2})/);
                            if (m2) yy = Number(m2[0]);
                        }
                    } else if (ds instanceof Date) {
                        yy = ds.getFullYear(); mm = ds.getMonth() + 1;
                    }
                    if (mm && (yy === curYear)) {
                        regions[rkey].numerator[mm-1] += sales;
                    } else if (mm && (yy === prevYear)) {
                        regions[rkey].numeratorPrev[mm-1] += sales;
                    }
                }
            });

            // compute hit rates for current and previous year per region
            Object.keys(regions).forEach(k => {
                const v = regions[k];
                const months = 12;
                const hit = Array(months).fill(null);
                const hitPrev = Array(months).fill(null);
                for (let i = 0; i < months; i++) {
                    const denom = v.denominator[i];
                    const numer = v.numerator[i];
                    if (denom && denom > 0) hit[i] = (Number(numer) / Number(denom)) * 100.0;
                    else if (numer && numer > 0) hit[i] = 0;
                    else hit[i] = null;

                    const denomP = v.denominatorPrev[i];
                    const numerP = v.numeratorPrev[i];
                    if (denomP && denomP > 0) hitPrev[i] = (Number(numerP) / Number(denomP)) * 100.0;
                    else if (numerP && numerP > 0) hitPrev[i] = 0;
                    else hitPrev[i] = null;
                }
                v.hit_rate_percent = hit;
                v.hit_rate_percent_prev = hitPrev;
            });

            this.state.hitRateByRegion = { year: curYear, months: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], regions: regions };
            console.debug('loadHitRateByRegion: computed regions keys', Object.keys(regions));
            this.computeHitRateRegionSeries();
        } catch (e) {
            console.error('Failed to compute hit rate by region', e);
            this.state.hitRateByRegion = { year: year, months: [], regions: {} };
            this.state.hitRateRegionSeries = { regions: [] };
        }
    }

    // Load Total Pipeline (YTD) series computed from Expected Start Date (client-side)
    loadPipelineSeries = async (year) => {
        try {
            if (!year || year === 'All') year = (new Date()).getFullYear();
            const curYear = Number(year);
            const prevYear = curYear - 1;
            const rows = this.getFilteredChartRows();
            const safeNum = v => { const n = (v === false || v === null || v === undefined || v === '') ? 0 : Number(v); return Number.isFinite(n) ? n : 0; };

            const bucket = (arr, y, m, val) => { if (y === curYear) arr.cur[m-1] += val; else if (y === prevYear) arr.prev[m-1] += val; };

            const agg = { cur: Array(12).fill(0), prev: Array(12).fill(0) };
            (rows || []).forEach(r => {
                const es = r.expectedStartDate || r.expected_start_date || r.expectedStart || r.expected_start || r.expected_start_date || r.expectedStartDate;
                let yy = null, mm = null;
                if (es) {
                    if (typeof es === 'string') {
                        const m = es.match(/(\d{4})-(\d{2})-(\d{2})/);
                        if (m) { yy = Number(m[1]); mm = Number(m[2]); }
                        else { const m2 = es.match(/(20\d{2}|19\d{2})/); if (m2) yy = Number(m2[0]); }
                    } else if (es instanceof Date) { yy = es.getFullYear(); mm = es.getMonth() + 1; }
                }
                if (!mm || !yy) return;
                // expected revenue field: prefer expectedRevenue, fallback to sales
                const raw = (r.expectedRevenue !== undefined) ? r.expectedRevenue : (r.expected_revenue !== undefined ? r.expected_revenue : r.sales);
                const val = safeNum(raw);
                bucket(agg, yy, mm, val);
            });

            // build YTD cumulative sums (in MYR millions)
            const curMonthly = agg.cur.slice(); const prevMonthly = agg.prev.slice();
            const curYTD = Array(12).fill(0); const prevYTD = Array(12).fill(0);
            let runC = 0, runP = 0;
            for (let i = 0; i < 12; i++) { runC += curMonthly[i]; runP += prevMonthly[i]; curYTD[i] = runC / 1e6; prevYTD[i] = runP / 1e6; }

            // compute plotting series
            this.computePipelineSeries({ year: curYear, ytd: curYTD }, { year: prevYear, ytd: prevYTD });
        } catch (e) {
            console.error('loadPipelineSeries error', e);
            this.state.pipelineSeries = { pathSegments: [], prevPathSegments: [], points: [], prevPoints: [], months: [], ticks: [], maxVal: 1 };
        }
    }

    // Compute SVG series for the pipeline chart (months on X, revenue (MYR mil) on Y).
    computePipelineSeries = (respCur, respPrev) => {
        try {
            const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            const w = 600, h = 320;
            // margins chosen to leave space for left y-axis labels and bottom month labels
            const marginLeft = 80, marginRight = 20, marginTop = 20, marginBottom = 60;
            const plotW = w - marginLeft - marginRight; // horizontal for months
            const plotH = h - marginTop - marginBottom; // vertical for revenue

            // x positions for each month (evenly spaced)
            const monthPositions = [];
            for (let i = 0; i < 12; i++) {
                const x = marginLeft + (i * (plotW / 11));
                monthPositions.push({ x: x, label: months[i] });
            }

            const valsCur = Array.isArray(respCur.ytd) ? respCur.ytd : Array(12).fill(null);
            const valsPrev = Array.isArray(respPrev.ytd) ? respPrev.ytd : Array(12).fill(null);

            // compute max for scaling (avoid zero)
            const maxVal = Math.max(1, ...valsCur.map(v => v || 0), ...valsPrev.map(v => v || 0));

            // build points and segments (y coordinate decreases for larger values)
            const sCur = { segments: [], flatPoints: [] };
            for (let i = 0; i < 12; i++) {
                const v = valsCur[i];
                if (v === null || v === undefined) { sCur.flatPoints.push(null); continue; }
                const x = monthPositions[i].x;
                const y = marginTop + ((1 - Math.min(v / maxVal, 1)) * plotH);
                sCur.flatPoints.push({ x: x, y: y, value: v, month: months[i], idx: i });
                if (i === 0) continue;
                const p0 = sCur.flatPoints[i-1]; const p1 = sCur.flatPoints[i];
                if (p0 && p1) sCur.segments.push({ d: `M ${p0.x} ${p0.y} L ${p1.x} ${p1.y}` });
            }

            const sPrev = { segments: [], flatPoints: [] };
            for (let i = 0; i < 12; i++) {
                const v = valsPrev[i];
                if (v === null || v === undefined) { sPrev.flatPoints.push(null); continue; }
                const x = monthPositions[i].x;
                const y = marginTop + ((1 - Math.min(v / maxVal, 1)) * plotH);
                sPrev.flatPoints.push({ x: x, y: y, value: v, month: months[i], idx: i });
                if (i === 0) continue;
                const p0 = sPrev.flatPoints[i-1]; const p1 = sPrev.flatPoints[i];
                if (p0 && p1) sPrev.segments.push({ d: `M ${p0.x} ${p0.y} L ${p1.x} ${p1.y}` });
            }

            // ticks on Y axis: compute 4 ticks nicely (in MYR millions)
            const tickCount = 4;
            // choose step in 0.1 increments where appropriate
            const step = Math.ceil((maxVal) / tickCount * 10) / 10;
            const ticks = [];
            for (let i = 0; i <= tickCount; i++) {
                const val = i * step;
                const y = marginTop + ((1 - Math.min(val / maxVal, 1)) * plotH);
                ticks.push({ y: y, label: `${val.toFixed(1)}` });
            }

            const filteredPoints = sCur.flatPoints.filter(p => p); const filteredPrev = sPrev.flatPoints.filter(p => p);
            this.state.pipelineSeries = {
                pathSegments: sCur.segments.map(s => ({ d: s.d, color: '#0d6efd' })),
                prevPathSegments: sPrev.segments.map(s => ({ d: s.d, color: '#6c757d' })),
                points: filteredPoints,
                prevPoints: filteredPrev,
                months: monthPositions,
                ticks: ticks,
                maxVal: maxVal,
            };
        } catch (e) {
            console.error('computePipelineSeries error', e);
            this.state.pipelineSeries = { pathSegments: [], prevPathSegments: [], points: [], prevPoints: [], months: [], ticks: [], maxVal: 1 };
        }
    }

    // Tooltip for pipeline points
    showPipelinePoint = (pt, ev) => {
        try {
            if (!pt) return;
            ev = ev || window.event || {};
            const clientX = typeof ev.clientX === 'number' ? ev.clientX : (ev.pageX || 0) - (window.scrollX || 0);
            const clientY = typeof ev.clientY === 'number' ? ev.clientY : (ev.pageY || 0) - (window.scrollY || 0);
            const left = Math.max(4, Math.min(window.innerWidth - 240, clientX + 12));
            const top = Math.max(4, Math.min(window.innerHeight - 40, clientY + 12));
            const html = `${pt.month}: <strong>${Number(pt.value).toFixed(2)} M</strong>`;
            this._showTextTooltip('Pipeline (YTD)', html, left, top);
        } catch (e) { console.error('showPipelinePoint', e); }
    }

    // Return service segments sorted ascending by percent (smallest first)
    getSortedSegments() {
        return (this.state.serviceSegments || []).slice().sort((a, b) => (a.percent || 0) - (b.percent || 0));
    }

    // Use a DOM tooltip appended to document.body. This avoids issues with ancestor transforms/overflow
    showTooltip = (seg, ev) => {
        try {
            ev = ev || (window && window.event) || {};
            // compute client coords (fallback from page coords)
            const pageX = (ev && typeof ev.pageX === 'number') ? ev.pageX : undefined;
            const pageY = (ev && typeof ev.pageY === 'number') ? ev.pageY : undefined;
            const clientX = (typeof ev.clientX === 'number') ? ev.clientX : (typeof pageX === 'number' ? (pageX - (window.scrollX || window.pageXOffset || 0)) : 0);
            const clientY = (typeof ev.clientY === 'number') ? ev.clientY : (typeof pageY === 'number' ? (pageY - (window.scrollY || window.pageYOffset || 0)) : 0);
            const offsetX = 12, offsetY = 12;
            let left = clientX + offsetX;
            let top = clientY + offsetY;
            const maxLeft = Math.max(4, window.innerWidth - 260);
            const maxTop = Math.max(4, window.innerHeight - 40);
            left = Math.max(4, Math.min(left, maxLeft));
            top = Math.max(4, Math.min(top, maxTop));
            // update small state markers (useful for dimming slices)
            this.state.tooltip.title = seg && seg.name ? seg.name : '';
            this.state.tooltip.value = seg && seg.value ? seg.value : 0;
            this.state.tooltip.percent = seg && seg.percent ? seg.percent : 0;
            this.state.tooltip.key = (seg && seg.rawKey) ? seg.rawKey : (seg && seg.name) || null;
            this._showDomTooltip(this.state.tooltip.title, this.state.tooltip.value, this.state.tooltip.percent, left, top);
            this.state.tooltip.visible = true;
        } catch (e) {
            console.error('showTooltip error', e);
        }
    }

    moveTooltip = (seg, ev) => {
        try {
            ev = ev || (window && window.event) || {};
            const pageX = (ev && typeof ev.pageX === 'number') ? ev.pageX : undefined;
            const pageY = (ev && typeof ev.pageY === 'number') ? ev.pageY : undefined;
            const clientX = (typeof ev.clientX === 'number') ? ev.clientX : (typeof pageX === 'number' ? (pageX - (window.scrollX || window.pageXOffset || 0)) : 0);
            const clientY = (typeof ev.clientY === 'number') ? ev.clientY : (typeof pageY === 'number' ? (pageY - (window.scrollY || window.pageYOffset || 0)) : 0);
            const offsetX = 12, offsetY = 12;
            let left = clientX + offsetX;
            let top = clientY + offsetY;
            const maxLeft = Math.max(4, window.innerWidth - 260);
            const maxTop = Math.max(4, window.innerHeight - 40);
            left = Math.max(4, Math.min(left, maxLeft));
            top = Math.max(4, Math.min(top, maxTop));
            this._moveDomTooltip(left, top);
        } catch (e) {
            // ignore
        }
    }

    hideTooltip = () => {
        try {
            this.state.tooltip.visible = false;
            this.state.tooltip.key = null;
            this._hideDomTooltip();
        } catch (e) { }
    }

    // DOM tooltip helpers
    _getDomTooltip() {
        return document.getElementById('plb-dashboard-tooltip');
    }

    _showDomTooltip(title, value, percent, left, top) {
        try {
            const escapeHtml = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[c]);
            let el = this._getDomTooltip();
            if (!el) {
                el = document.createElement('div');
                el.id = 'plb-dashboard-tooltip';
                el.className = 'badge bg-dark text-white';
                el.style.position = 'fixed';
                el.style.zIndex = '1200';
                el.style.whiteSpace = 'nowrap';
                el.style.padding = '6px 8px';
                el.style.pointerEvents = 'none';
                document.body.appendChild(el);
            }
            el.style.left = `${left}px`;
            el.style.top = `${top}px`;
            el.innerHTML = `<div style="font-weight:600;">${escapeHtml(title)}</div><div style="font-size:12px; opacity:0.95;">${this.formatCurrency(value)} (${Number(percent).toFixed(2)}%)</div>`;
            el.style.display = 'block';
        } catch (e) {
            console.error('_showDomTooltip', e);
        }
    }

    // Show a tooltip with arbitrary HTML content (used by hit rate points)
    _showTextTooltip(title, htmlContent, left, top) {
        try {
            let el = document.getElementById('plb-dashboard-tooltip');
            if (!el) {
                el = document.createElement('div');
                el.id = 'plb-dashboard-tooltip';
                el.className = 'badge bg-dark text-white';
                el.style.position = 'fixed';
                el.style.zIndex = '1200';
                el.style.whiteSpace = 'nowrap';
                el.style.padding = '6px 8px';
                el.style.pointerEvents = 'none';
                document.body.appendChild(el);
            }
            el.style.left = `${left}px`;
            el.style.top = `${top}px`;
            el.innerHTML = `<div style="font-weight:600;">${String(title)}</div><div style="font-size:12px; opacity:0.95;">${String(htmlContent)}</div>`;
            el.style.display = 'block';
        } catch (e) { console.error('_showTextTooltip', e); }
    }

    _moveDomTooltip(left, top) {
        try {
            const el = this._getDomTooltip();
            if (el) { el.style.left = `${left}px`; el.style.top = `${top}px`; }
        } catch (e) { }
    }

    _hideDomTooltip() {
        try {
            const el = this._getDomTooltip();
            if (el) { el.style.display = 'none'; }
        } catch (e) { }
    }

    // Handlers for hit rate point hover
    showPoint = (pt, ev) => {
        try {
            if (!pt) return;
            ev = ev || window.event || {};
            const clientX = typeof ev.clientX === 'number' ? ev.clientX : (ev.pageX || 0) - (window.scrollX || 0);
            const clientY = typeof ev.clientY === 'number' ? ev.clientY : (ev.pageY || 0) - (window.scrollY || 0);
            const left = Math.max(4, Math.min(window.innerWidth - 240, clientX + 12));
            const top = Math.max(4, Math.min(window.innerHeight - 40, clientY + 12));
            const yearLabel = pt && pt.year ? ` ${pt.year}` : '';
            const html = `${pt.month}${yearLabel}: <strong>${Number(pt.value).toFixed(2)}%</strong><br/>Win: ${this.formatNumber(pt.numer)} / Expected: ${this.formatNumber(pt.denom)}`;
            this._showTextTooltip('Hit Rate', html, left, top);
        } catch (e) { console.error('showPoint', e); }
    }

    movePoint = (pt, ev) => {
        try {
            ev = ev || window.event || {};
            const clientX = typeof ev.clientX === 'number' ? ev.clientX : (ev.pageX || 0) - (window.scrollX || 0);
            const clientY = typeof ev.clientY === 'number' ? ev.clientY : (ev.pageY || 0) - (window.scrollY || 0);
            const left = Math.max(4, Math.min(window.innerWidth - 240, clientX + 12));
            const top = Math.max(4, Math.min(window.innerHeight - 40, clientY + 12));
            const el = this._getDomTooltip(); if (el) { el.style.left = `${left}px`; el.style.top = `${top}px`; }
        } catch (e) { }
    }

    hidePoint = () => { this._hideDomTooltip(); }

    // Handlers for regional hit rate point hover
    showRegionPoint = (pt, reg, ev) => {
        try {
            if (!pt || !reg) return;
            ev = ev || window.event || {};
            const clientX = typeof ev.clientX === 'number' ? ev.clientX : (ev.pageX || 0) - (window.scrollX || 0);
            const clientY = typeof ev.clientY === 'number' ? ev.clientY : (ev.pageY || 0) - (window.scrollY || 0);
            const left = Math.max(4, Math.min(window.innerWidth - 240, clientX + 12));
            const top = Math.max(4, Math.min(window.innerHeight - 40, clientY + 12));
            const title = `Hit Rate — ${reg.label || reg.key}`;
            const html = `${pt.month}: <strong>${Number(pt.value).toFixed(2)}%</strong><br/>Win: ${this.formatNumber(pt.numer)} / Expected: ${this.formatNumber(pt.denom)}`;
            this._showTextTooltip(title, html, left, top);
        } catch (e) { console.error('showRegionPoint', e); }
    }

    // Compute plotting series for Hit Rate by Dept/Region from this.state.hitRateByRegion
    computeHitRateRegionSeries = () => {
        try {
            const data = this.state.hitRateByRegion || { months: [], regions: {} };
            const months = data.months && data.months.length ? data.months : ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            const marginLeft = 60, marginTop = 20, marginRight = 20, marginBottom = 60;
            const plotW = 600 - marginLeft - marginRight; // 520
            const plotH = 320 - marginTop - marginBottom; // 240
            const monthPositions = [];
            for (let i = 0; i < 12; i++) {
                const x = marginLeft + (i * (plotW / 11));
                monthPositions.push({ x: x, label: months[i] || '' });
            }

            const palette = ["#0d6efd", "#198754", "#dc3545", "#6f42c1", "#fd7e14", "#20c997", "#6610f2", "#e83e8c", "#0dcaf0", "#adb5bd"];
            const regionsArr = [];
            const regionKeys = Object.keys(data.regions || {});
            regionKeys.forEach((k, idx) => {
                const reg = data.regions[k];
                const color = palette[idx % palette.length];
                const vals = Array.isArray(reg.hit_rate_percent) ? reg.hit_rate_percent : Array(12).fill(null);
                const valsPrev = Array.isArray(reg.hit_rate_percent_prev) ? reg.hit_rate_percent_prev : Array(12).fill(null);
                // build current series
                const sCur = { segments: [], points: [] };
                const flatCur = [];
                for (let i = 0; i < 12; i++) {
                    const v = vals[i];
                    if (v === null || v === undefined) { flatCur.push(null); continue; }
                    const percent = Number(v);
                    const clamped = Number.isFinite(percent) ? Math.max(0, Math.min(100, percent)) : 0;
                    const x = monthPositions[i].x;
                    const y = marginTop + ((100 - clamped) / 100) * plotH;
                    flatCur.push({ x: x, y: y, value: clamped, month: months[i], idx: i, numer: reg.numerator ? reg.numerator[i] : 0, denom: reg.denominator ? reg.denominator[i] : 0 });
                    if (i > 0) {
                        const p0 = flatCur[i-1]; const p1 = flatCur[i];
                        if (p0 && p1) sCur.segments.push({ d: `M ${p0.x} ${p0.y} L ${p1.x} ${p1.y}` });
                    }
                }
                sCur.points = flatCur.filter(p => p);

                // build previous series
                const sPrev = { segments: [], points: [] };
                const flatPrev = [];
                for (let i = 0; i < 12; i++) {
                    const v = valsPrev[i];
                    if (v === null || v === undefined) { flatPrev.push(null); continue; }
                    const percent = Number(v);
                    const clamped = Number.isFinite(percent) ? Math.max(0, Math.min(100, percent)) : 0;
                    const x = monthPositions[i].x;
                    const y = marginTop + ((100 - clamped) / 100) * plotH;
                    flatPrev.push({ x: x, y: y, value: clamped, month: months[i], idx: i, numer: reg.numeratorPrev ? reg.numeratorPrev[i] : 0, denom: reg.denominatorPrev ? reg.denominatorPrev[i] : 0 });
                    if (i > 0) {
                        const p0 = flatPrev[i-1]; const p1 = flatPrev[i];
                        if (p0 && p1) sPrev.segments.push({ d: `M ${p0.x} ${p0.y} L ${p1.x} ${p1.y}` });
                    }
                }
                sPrev.points = flatPrev.filter(p => p);

                regionsArr.push({ key: k, label: reg.label || k, color: color, segments: sCur.segments, points: sCur.points, prevSegments: sPrev.segments, prevPoints: sPrev.points });
            });

            this.state.hitRateRegionSeries = { regions: regionsArr, months: monthPositions };
        } catch (e) {
            console.error('computeHitRateRegionSeries error', e);
            this.state.hitRateRegionSeries = { regions: [], months: [] };
        }
    }
}

PLBDashboard.template = xml/* xml */ `
<div class="container-fluid p-4" style="height:100%; overflow:auto;">
    <h3 class="mb-3">PLB Dashboard</h3>

    <!-- Loading state -->
    <t t-if="state.loading">
        <div class="text-center my-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading dashboard data...</p>
        </div>
    </t>

    <t t-else="">
        <!-- Revenue Summary Cards -->
        <div class="row mb-4">
            <div class="col-md-3 col-lg-3">
                <div class="card text-center" style="border-left: 4px solid #007bff;">
                    <div class="card-body">
                        <h6 class="card-subtitle mb-2 text-muted">Total Leads</h6>
                        <h3 class="card-title"><t t-esc="state.revenueSummary.lead_count"/></h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3 col-lg-3">
                <div class="card text-center" style="border-left: 4px solid #28a745;">
                    <div class="card-body">
                        <h6 class="card-subtitle mb-2 text-muted">Expected Revenue</h6>
                        <h3 class="card-title"><t t-esc="formatCurrency(state.revenueSummary.total_expected_revenue)"/></h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3 col-lg-3">
                <div class="card text-center" style="border-left: 4px solid #dc3545;">
                    <div class="card-body">
                        <h6 class="card-subtitle mb-2 text-muted">Realized FY2025</h6>
                        <h3 class="card-title"><t t-esc="formatCurrency(state.revenueSummary.total_realized_revenue)"/></h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3 col-lg-3">
                <div class="card text-center" style="border-left: 4px solid #6f42c1;">
                    <div class="card-body">
                        <h6 class="card-subtitle mb-2 text-muted">Carry Forward</h6>
                        <h3 class="card-title"><t t-esc="formatCurrency(state.totalCarryForward)"/></h3>
                    </div>
                </div>
            </div>
        </div>

        <!-- Stage Counts -->
        <div class="mb-3">
            <!-- Filters: Salesperson, Stage, Service -->
            <div class="d-flex mb-2" style="gap:12px; align-items:center;">
                <div>
                    <label class="form-label mb-0 small">Salesperson</label>
                    <select class="form-select form-select-sm" t-att-value="state.filters.salesperson" t-on-change="ev => this.setFilter('salesperson', ev.target.value)">
                        <t t-foreach="state.salespersons" t-as="sp" t-key="sp">
                            <option t-att-value="sp"><t t-esc="sp"/></option>
                        </t>
                    </select>
                </div>
                <div>
                    <label class="form-label mb-0 small">Stage</label>
                    <select class="form-select form-select-sm" t-att-value="state.filters.stage" t-on-change="ev => this.setFilter('stage', ev.target.value)">
                        <t t-foreach="state.stages" t-as="st" t-key="st">
                            <option t-att-value="st"><t t-esc="st"/></option>
                        </t>
                    </select>
                </div>
                <div>
                    <label class="form-label mb-0 small">Service</label>
                    <select class="form-select form-select-sm" t-att-value="state.filters.service" t-on-change="ev => this.setFilter('service', ev.target.value)">
                        <t t-foreach="state.services" t-as="sv" t-key="sv">
                            <option t-att-value="sv"><t t-esc="sv"/></option>
                        </t>
                    </select>
                </div>
                <div>
                    <label class="form-label mb-0 small">Year</label>
                    <select class="form-select form-select-sm" t-att-value="state.filters.year" t-on-change="ev => this.setFilter('year', ev.target.value)">
                        <t t-foreach="state.years" t-as="yr" t-key="yr">
                            <option t-att-value="yr"><t t-esc="yr"/></option>
                        </t>
                    </select>
                </div>
            </div>

            <h5>Pipeline Stages</h5>
            <t t-if="Object.keys(state.stageCounts).length">
                <div style="display:flex; flex-wrap:wrap; gap:12px;">
                    <t t-foreach="Object.entries(state.stageCounts)" t-as="entry" t-key="entry[0]">
                        <div style="padding:8px 16px; background:#e9ecef; border-radius:20px; font-size:14px;">
                            <strong><t t-esc="entry[0]"/>:</strong> <t t-esc="entry[1]"/>
                        </div>
                    </t>
                </div>
            </t>
            <t t-else="">
                <div class="text-muted">No stage data available.</div>
            </t>
        </div>

        <!-- Three-column layout: Services Pie | Hit Rate Trend | Hit Rate by Dept/Region -->
        <div class="row mb-4 g-3">
            <div class="col-12 col-lg-4">
                <div class="card h-100 shadow-sm">
                    <div class="card-header bg-white">
                        <h5 class="mb-0">New wins by Product</h5>
                    </div>
                    <!-- Make the pie card the same height as the line charts so visuals match -->
                    <!-- Use a column flex layout: svg area grows, legend sits at the bottom inside the card -->
                    <div class="card-body d-flex flex-column" style="height:320px; padding:12px;">
                        <t t-if="state.serviceSegments &amp;&amp; state.serviceSegments.length">
                            <div class="d-flex flex-column" style="width:100%; height:100%;">
                                <!-- SVG container grows to fill available space -->
                                <div class="d-flex align-items-center justify-content-center" style="flex:1 1 auto; width:100%; overflow:hidden; max-height:100%;">
                                    <!-- Larger SVG: use 320x320 viewBox centered at 160,160
                                         preserveAspectRatio and width:auto keep the pie from stretching beyond the card -->
                                    <svg preserveAspectRatio="xMidYMid meet" style="height:100%; width:auto; display:block; margin:0 auto;" viewBox="0 0 320 320" aria-label="Services pie chart">
                                        <g transform="translate(160,160)">
                                            <t t-foreach="state.serviceSegments" t-as="seg" t-key="seg.name">
                                                <path t-att-d="seg.path" t-att-fill="seg.color" stroke="#fff"
                                                      t-att-stroke-width="state.tooltip.key === seg.rawKey ? '3' : '1'"
                                                      t-att-opacity="state.tooltip.key ? (state.tooltip.key !== seg.rawKey ? '0.45' : '1') : '1'"
                                                      style="cursor:pointer; pointer-events:auto; vector-effect:non-scaling-stroke;" t-on-mouseenter="ev => this.showTooltip(seg, ev)"
                                                      t-on-mousemove="ev => this.moveTooltip(seg, ev)" t-on-mouseleave="this.hideTooltip"/>
                                            </t>
                                        </g>
                                    </svg>
                                </div>

                                <!-- Legend/footer area: does not grow beyond its content and stays inside the card -->
                                <div class="pt-2" style="flex:0 0 auto; width:100%;">
                                    <div class="w-100 d-flex flex-wrap justify-content-center" style="gap:8px;">
                                        <t t-foreach="this.getSortedSegments()" t-as="seg" t-key="seg.rawKey">
                                            <span class="badge bg-light text-dark d-inline-flex align-items-center" style="gap:6px; cursor:default; font-size:11px; padding:4px 6px;" t-on-mouseenter="ev => this.showTooltip(seg, ev)" t-on-mouseleave="this.hideTooltip">
                                                 <span t-att-style="'display:inline-block;width:12px;height:12px;background:'+seg.color+';border-radius:2px;box-shadow:0 0 0 1px rgba(0,0,0,0.05) inset;' "></span>
                                                 <strong style="font-weight:600; font-size:12px;"><t t-esc="seg.percent.toFixed(2)"/>%</strong>
                                             </span>
                                         </t>
                                     </div>
                                 </div>
                             </div>
                         </t>
                         <t t-else="">
                             <div class="text-muted">No service data available.</div>
                         </t>
                     </div>
                 </div>
             </div>

            <div class="col-12 col-lg-4">
                <div class="card h-100 shadow-sm">
                    <div class="card-header bg-white">
                        <h5 class="mb-0">Hit Rate Trend</h5>
                    </div>
                    <div class="card-body">
                        <div class="position-relative" style="height:320px;">
                            <!-- Trend SVG now matches Dept/Region vertical size -->
                            <svg width="100%" height="100%" viewBox="0 0 600 320" aria-label="Hit rate trend chart">
                                <g class="grid" stroke="#e0e0e0" stroke-width="0.6">
                                    <t t-foreach="[100,80,60,40,20,0]" t-as="v" t-key="v">
                                        <line t-att-x1="60" t-att-y1="20 + (100 - v) * 2.4" t-att-x2="580" t-att-y2="20 + (100 - v) * 2.4"/>
                                    </t>
                                </g>
                                <g class="axis" fill="none" stroke="#333" stroke-width="0.9">
                                    <line x1="60" y1="20" x2="60" y2="260"/>
                                </g>

                                <t t-if="state.hitRateSeries &amp;&amp; state.hitRateSeries.prevPathSegments &amp;&amp; state.hitRateSeries.prevPathSegments.length">
                                    <g class="data-line-prev">
                                        <t t-foreach="state.hitRateSeries.prevPathSegments" t-as="seg" t-key="'prev-'+seg.d">
                                            <path t-att-d="seg.d" fill="none" t-att-stroke="seg.color" stroke-width="2" stroke-dasharray="6 4"/>
                                        </t>
                                    </g>
                                    <g class="data-points-prev">
                                        <t t-foreach="state.hitRateSeries.prevPoints" t-as="pt" t-key="'prevpt-'+pt.idx">
                                            <circle t-att-cx="pt.x" t-att-cy="pt.y" r="4" fill="#6c757d" opacity="0.85"
                                                    style="cursor:pointer; pointer-events:auto;" t-on-mouseenter="ev => this.showPoint(pt, ev)"
                                                    t-on-mousemove="ev => this.movePoint(pt, ev)" t-on-mouseleave="this.hidePoint"/>
                                        </t>
                                    </g>
                                </t>

                                <t t-if="state.hitRateSeries &amp;&amp; state.hitRateSeries.pathSegments &amp;&amp; state.hitRateSeries.pathSegments.length">
                                    <g class="data-line">
                                        <t t-foreach="state.hitRateSeries.pathSegments" t-as="seg" t-key="seg.d">
                                            <path t-att-d="seg.d" fill="none" t-att-stroke="seg.color" stroke-width="2"/>
                                        </t>
                                    </g>
                                    <g class="data-points">
                                        <t t-foreach="state.hitRateSeries.points" t-as="pt" t-key="pt.idx">
                                            <circle t-att-cx="pt.x" t-att-cy="pt.y" r="4" fill="#0d6efd"
                                                    style="cursor:pointer; pointer-events:auto;" t-on-mouseenter="ev => this.showPoint(pt, ev)"
                                                    t-on-mousemove="ev => this.movePoint(pt, ev)" t-on-mouseleave="this.hidePoint"/>
                                        </t>
                                    </g>
                                </t>
                                <t t-if="!(state.hitRateSeries &amp;&amp; state.hitRateSeries.pathSegments &amp;&amp; state.hitRateSeries.pathSegments.length) &amp;&amp; !(state.hitRateSeries &amp;&amp; state.hitRateSeries.prevPathSegments &amp;&amp; state.hitRateSeries.prevPathSegments.length)">
                                    <g>
                                        <text x="300" y="110" text-anchor="middle" fill="#888" font-size="14px">No hit rate data to display</text>
                                    </g>
                                </t>

                                <text x="320" y="295" text-anchor="middle" fill="#333" font-size="14px">Months</text>
                                <text x="18" y="140" text-anchor="middle" fill="#333" font-size="14px" transform="rotate(-90,18,160)">Hit Rate (%)</text>

                                <t t-foreach="[100,80,60,40,20,0]" t-as="v" t-key="'yt'+v">
                                    <text t-att-x="36" t-att-y="20 + (100 - v) * 2.4 + 4" text-anchor="end" fill="#333" font-size="12px"><t t-esc="v"/>%</text>
                                </t>

                                <t t-if="state.hitRateSeries &amp;&amp; state.hitRateSeries.months &amp;&amp; state.hitRateSeries.months.length">
                                    <t t-foreach="state.hitRateSeries.months" t-as="mpos" t-key="mpos.label">
                                        <text t-att-x="mpos.x" t-att-y="275" text-anchor="middle" fill="#333" font-size="11px"><t t-esc="mpos.label"/></text>
                                    </t>
                                </t>
                            </svg>
                        </div>

                        <div class="mt-3 d-flex gap-3 justify-content-center">
                            <div class="d-flex align-items-center gap-2"><span style="width:12px;height:12px;background:#0d6efd;border-radius:2px;display:inline-block;"></span><small class="mb-0">This Year</small></div>
                            <div class="d-flex align-items-center gap-2"><span style="width:12px;height:12px;background:#6c757d;border-radius:2px;display:inline-block;"></span><small class="mb-0">Last Year</small></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-12 col-lg-4">
                <div class="card h-100 shadow-sm">
                    <div class="card-header bg-white">
                        <h5 class="mb-0">Hit Rate by Dept/Region</h5>
                    </div>
                    <div class="card-body">
                        <div class="position-relative" style="height:320px;">
                            <svg width="100%" height="100%" viewBox="0 0 600 320" aria-label="Hit rate by dept region chart">
                                <!-- grid -->
                                <g class="grid" stroke="#e0e0e0" stroke-width="0.6">
                                    <t t-foreach="[100,80,60,40,20,0]" t-as="v" t-key="v">
                                        <line t-att-x1="60" t-att-y1="20 + (100 - v) * 2.4" t-att-x2="580" t-att-y2="20 + (100 - v) * 2.4"/>
                                    </t>
                                </g>
                                <g class="axis" fill="none" stroke="#333" stroke-width="0.9">
                                    <line x1="60" y1="20" x2="60" y2="260"/>
                                </g>

                                <!-- Render each region series -->
                                <t t-if="state.hitRateRegionSeries &amp;&amp; state.hitRateRegionSeries.regions &amp;&amp; state.hitRateRegionSeries.regions.length">
                                    <t t-foreach="state.hitRateRegionSeries.regions" t-as="reg" t-key="reg.key">
                                        <!-- Previous year (dashed gray) -->
                                        <g class="region-line-prev">
                                            <t t-foreach="reg.prevSegments || []" t-as="seg" t-key="'prev-'+reg.key+'-'+seg.d">
                                                <path t-att-d="seg.d" fill="none" stroke="#6c757d" stroke-width="2" stroke-dasharray="6 4" opacity="0.9"/>
                                            </t>
                                        </g>
                                        <g class="region-points-prev">
                                            <t t-foreach="reg.prevPoints || []" t-as="pt" t-key="'prevpt-'+reg.key+'-'+pt.idx">
                                                <circle t-att-cx="pt.x" t-att-cy="pt.y" r="3" fill="#6c757d" opacity="0.6"
                                                        style="cursor:pointer; pointer-events:auto;" t-on-mouseenter="ev => this.showRegionPoint(pt, reg, ev)"
                                                        t-on-mousemove="ev => this.movePoint(pt, ev)" t-on-mouseleave="this.hidePoint"/>
                                            </t>
                                        </g>

                                        <!-- Current year -->
                                        <g class="region-line">
                                            <t t-foreach="reg.segments || []" t-as="seg" t-key="reg.key+'-'+seg.d">
                                                <path t-att-d="seg.d" fill="none" t-att-stroke="reg.color" stroke-width="2"/>
                                            </t>
                                        </g>
                                        <g class="region-points">
                                            <t t-foreach="reg.points || []" t-as="pt" t-key="reg.key+'-pt-'+pt.idx">
                                                <circle t-att-cx="pt.x" t-att-cy="pt.y" r="4" t-att-fill="reg.color" opacity="0.95"
                                                        style="cursor:pointer; pointer-events:auto;" t-on-mouseenter="ev => this.showRegionPoint(pt, reg, ev)"
                                                        t-on-mousemove="ev => this.movePoint(pt, ev)" t-on-mouseleave="this.hidePoint"/>
                                            </t>
                                        </g>
                                    </t>
                                </t>
                                <t t-else="">
                                    <g>
                                        <text x="300" y="160" text-anchor="middle" fill="#888" font-size="14px">No region data to display</text>
                                    </g>
                                </t>

                                 <!-- labels -->
                                 <text x="320" y="295" text-anchor="middle" fill="#333" font-size="14px">Months</text>
                                 <text x="18" y="140" text-anchor="middle" fill="#333" font-size="14px" transform="rotate(-90,18,160)">Hit Rate (%)</text>

                                <!-- Y tick labels -->
                                <t t-foreach="[100,80,60,40,20,0]" t-as="v" t-key="'ryt'+v">
                                    <text t-att-x="36" t-att-y="20 + (100 - v) * 2.4 + 4" text-anchor="end" fill="#333" font-size="12px"><t t-esc="v"/>%</text>
                                </t>

                                <!-- X month labels -->
                                <t t-if="state.hitRateRegionSeries &amp;&amp; state.hitRateRegionSeries.months &amp;&amp; state.hitRateRegionSeries.months.length">
                                    <t t-foreach="state.hitRateRegionSeries.months" t-as="mpos" t-key="mpos.label">
                                        <text t-att-x="mpos.x" t-att-y="275" text-anchor="middle" fill="#333" font-size="11px"><t t-esc="mpos.label"/></text>
                                    </t>
                                </t>
                            </svg>
                        </div>
                        <!-- Legend: placed after the chart container so it is visible inside the card body -->
                        <div class="mt-3 d-flex gap-3 justify-content-center flex-wrap">
                            <t t-foreach="state.hitRateRegionSeries.regions || []" t-as="reg" t-key="reg.key">
                                <div class="d-flex align-items-center gap-2" style="cursor:default;">
                                    <span t-att-style="'display:inline-block;width:12px;height:12px;background:'+reg.color+';border-radius:2px;display:inline-block;'">
                                    </span>
                                    <small class="mb-0"><t t-esc="reg.label"/></small>
                                </div>
                            </t>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Total pipeline (YTD) chart -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card h-100 shadow-sm">
                    <div class="card-header bg-white">
                        <h5 class="mb-0">Total pipeline (YTD)</h5>
                    </div>
                    <div class="card-body">
                        <div class="position-relative" style="height:320px;">
                            <svg width="100%" height="100%" viewBox="0 0 600 320" aria-label="Total pipeline YTD chart">
                                <!-- horizontal month axis (x) and vertical revenue grid (y) -->
                                <g class="grid" stroke="#e9ecef" stroke-width="0.6">
                                    <t t-foreach="state.pipelineSeries &amp;&amp; state.pipelineSeries.ticks || []" t-as="tk" t-key="tk.y">
                                        <line t-att-x1="60" t-att-y1="tk.y" t-att-x2="580" t-att-y2="tk.y"/>
                                    </t>
                                </g>
                                <g class="axis" fill="none" stroke="#333" stroke-width="0.9">
                                    <!-- y axis baseline -->
                                    <line x1="60" y1="20" x2="60" y2="300"/>
                                </g>

                                <!-- previous year dashed -->
                                <t t-if="state.pipelineSeries &amp;&amp; state.pipelineSeries.prevPathSegments &amp;&amp; state.pipelineSeries.prevPathSegments.length">
                                    <g class="data-line-prev">
                                        <t t-foreach="state.pipelineSeries.prevPathSegments" t-as="seg" t-key="'pp-'+seg.d">
                                            <path t-att-d="seg.d" fill="none" stroke="#6c757d" stroke-width="2" stroke-dasharray="6 4"/>
                                        </t>
                                    </g>
                                    <g class="data-points-prev">
                                        <t t-foreach="state.pipelineSeries.prevPoints" t-as="pt" t-key="'ppt-'+pt.idx">
                                            <circle t-att-cx="pt.x" t-att-cy="pt.y" r="4" fill="#6c757d" opacity="0.7"
                                                    style="cursor:pointer; pointer-events:auto;" t-on-mouseenter="ev => this.showPipelinePoint(pt, ev)" t-on-mousemove="ev => this.movePoint(pt, ev)" t-on-mouseleave="this.hidePoint"/>
                                        </t>
                                    </g>
                                </t>

                                <!-- current year -->
                                <t t-if="state.pipelineSeries &amp;&amp; state.pipelineSeries.pathSegments &amp;&amp; state.pipelineSeries.pathSegments.length">
                                    <g class="data-line">
                                        <t t-foreach="state.pipelineSeries.pathSegments" t-as="seg" t-key="seg.d">
                                            <path t-att-d="seg.d" fill="none" stroke="#0d6efd" stroke-width="2"/>
                                        </t>
                                    </g>
                                    <g class="data-points">
                                        <t t-foreach="state.pipelineSeries.points" t-as="pt" t-key="'pt-'+pt.idx">
                                            <circle t-att-cx="pt.x" t-att-cy="pt.y" r="4" fill="#0d6efd" opacity="0.95"
                                                    style="cursor:pointer; pointer-events:auto;" t-on-mouseenter="ev => this.showPipelinePoint(pt, ev)" t-on-mousemove="ev => this.movePoint(pt, ev)" t-on-mouseleave="this.hidePoint"/>
                                        </t>
                                    </g>
                                </t>

                                <!-- month labels on X axis -->
                                <t t-foreach="state.pipelineSeries &amp;&amp; state.pipelineSeries.months || []" t-as="mpos" t-key="mpos.label">
                                    <text t-att-x="mpos.x" t-att-y="312" text-anchor="middle" fill="#333" font-size="11px"><t t-esc="mpos.label"/></text>
                                </t>

                                <!-- y ticks labels -->
                                <t t-foreach="state.pipelineSeries &amp;&amp; state.pipelineSeries.ticks || []" t-as="tk" t-key="tk.y">
                                    <text t-att-x="48" t-att-y="tk.y + 4" text-anchor="end" fill="#333" font-size="11px"><t t-esc="tk.label"/>M</text>
                                </t>

                                <!-- axis label -->
                                <text x="30" y="16" text-anchor="start" fill="#333" font-size="12px">Expected Revenue (MYR (mil))</text>
                            </svg>
                        </div>

                        <div class="mt-3 d-flex gap-3 justify-content-center">
                            <div class="d-flex align-items-center gap-2"><span style="width:12px;height:12px;background:#0d6efd;border-radius:2px;display:inline-block;"></span><small class="mb-0">Pipeline (Current year)</small></div>
                            <div class="d-flex align-items-center gap-2"><span style="width:12px;height:12px;background:#6c757d;border-radius:2px;display:inline-block;"></span><small class="mb-0">Last year Pipeline</small></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Data Table -->
        <div class="table-responsive">
            <style>
                /* Ensure table-bordered shows regular borders (Bootstrap may set these elsewhere) */
                table.table-bordered th, table.table-bordered td { border: 1px solid #dee2e6 !important; }
                /* Double border only on monthly subtotal cells (Jan..Dec) */
                .plb-footer .plb-month-border { border-top: 3px double #333 !important; border-bottom: 3px double #333 !important; }
                /* Remove the bottom border of subtotal's non-month cells so the double line doesn't continue across */
                .plb-footer .plb-subtotal-no-bottom { border-bottom: none !important; }
                /* Remove the top border of the cumulative row cells to avoid a full-width line between subtotal &amp; cumulative */
                .plb-footer .plb-cumulative-no-top { border-top: none !important; }
            </style>
            <table class="table table-bordered table-hover table-sm sticky-head" style="border-collapse:collapse; border-spacing:0;">
                <thead class="table-light">
                    <tr>
                        <th rowspan="2">Company</th>
                        <th rowspan="2">Project Name</th>
                        <th rowspan="2">Salesperson</th>
                        <th rowspan="2">Stage</th>
                        <th rowspan="2">Expected Revenue</th>
                        <th rowspan="2">Services</th>
                        <!-- Dept/Region column removed -->
                        <th colspan="12" class="text-center">Realized Revenue (Months)</th>
                        <th rowspan="2">Realized FY2025</th>
                        <th rowspan="2">Carry Forward</th>
                         <!-- Profit Margin column removed -->
                     </tr>
                    <tr>
                        <th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th>
                        <th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th>
                    </tr>
                </thead>
                <tbody>
                    <t t-if="getFilteredTableRows() &amp;&amp; getFilteredTableRows().length">
                        <tr t-foreach="getFilteredTableRows()" t-as="row" t-key="row.id">
                            <td><t t-esc="row.company || 'NULL'"/></td>
                            <td><t t-esc="row.customer || 'NULL'"/></td>
                            <td><t t-esc="formatText(row.salesperson)"/></td>
                            <td><t t-esc="row.stage || 'NULL'"/></td>
                            <td class="text-end"><t t-esc="formatCurrency(row.sales)"/></td>
                            <td><t t-esc="formatText(row.services)"/></td>

                            <!-- Loop for monthly revenue -->
                            <t t-foreach="row.monthlyRevenue || []" t-as="month" t-key="month">
                                <td class="text-end"><t t-esc="formatCurrency(month)"/></td>
                            </t>
                            <td class="text-end"><t t-esc="formatCurrency(row.realizedRevenue)"/></td>
                            <td class="text-end"><t t-esc="formatCurrency(row.carryForward)"/></td>
                         </tr>
                     </t>
                     <t t-else="">
                         <tr>
                            <td colspan="20" class="text-center text-muted">No data available</td>
                         </tr>
                     </t>
                 </tbody>
                 <tfoot class="plb-footer">
                     <!-- Emphasized subtotal row: double top/bottom border only on monthly columns -->
                     <tr style="font-weight:700; background:#f8f9fa;">
                         <!-- remove bottom border on the leading label cell so the double line won't continue across -->
                         <td colspan="6" class="text-end plb-subtotal-no-bottom"><strong>Monthly Subtotal</strong></td>
                         <!-- Double top and bottom border only on monthly columns (Jan..Dec) -->
                         <t t-foreach="state.monthlySubtotals" t-as="m" t-key="m">
                             <td class="text-end plb-month-border" style="font-weight:700;"><t t-esc="formatCurrency(m)"/></td>
                         </t>
                     </tr>

                     <!-- Cumulative row: slightly lighter styling, no full-width top border so the double line appears only under monthly columns -->
                     <tr style="font-weight:600; background:#ffffff;">
                         <td colspan="6" class="text-end plb-cumulative-no-top"><strong>Cumulative</strong></td>
                         <t t-foreach="state.monthlyCumulative" t-as="c" t-key="c">
                             <td class="text-end plb-cumulative-no-top" style="font-weight:600;"><t t-esc="formatCurrency(c)"/></td>
                         </t>
                     </tr>
                 </tfoot>
             </table>
         </div>
     </t>
 </div>
 `;

 registry.category("actions").add("PLB_dashboard_tag", PLBDashboard);

