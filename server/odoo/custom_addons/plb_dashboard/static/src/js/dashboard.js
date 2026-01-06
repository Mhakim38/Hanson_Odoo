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
            // Pipeline YTD by region state
            pipelineByRegion: { year: null, months: [], regions: {} },
            pipelineRegionSeries: { regions: [], months: [], ticks: [], maxVal: 1 },
            // Avg pipeline per person state
            avgPipelinePerPerson: { year: null, months: [], avg_per_person: [] },
            avgPipelinePerPersonSeries: { pathSegments: [], points: [], months: [], ticks: [], maxVal: 1 },
            // Avg pipeline per person by region state
            avgPipelinePerPersonByRegion: { year: null, months: [], regions: {} },
            avgPipelinePerPersonByRegionSeries: { regions: [], months: [], ticks: [], maxVal: 1 },
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
            // Gauge meter data
            company_yearly_target: 0,
            total_ytd_revenue: 0,
            total_realized_revenue: 0,
            ytd_percentage: 0,
            realized_percentage: 0,
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

            // Get the active year for filtering
            const activeYear = (this.state.filters && this.state.filters.year && this.state.filters.year !== 'All') ? Number(this.state.filters.year) : (new Date()).getFullYear();

            // Fetch stage counts (filtered by year)
            const stageCounts = await this.rpc("/plb/stage_counts", { year: activeYear });
            if (stageCounts) {
                this.state.stageCounts = stageCounts;
            }

            // Fetch revenue summary (filtered by year)
            const revenueSummary = await this.rpc("/plb/revenue_summary", { year: activeYear });
            if (revenueSummary) {
                this.state.revenueSummary = revenueSummary;
            }

            // After rows loaded, compute filter options and monthly subtotals
            this.computeFilterOptions();
            this.computeTotals();
            // Compute hit rate and pie for the active year. Prefer server aggregation (more reliable),
            // but fall back to client-side computation from loaded rows if the server returns no data.
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
             // load pipeline YTD by region
             await this.loadPipelineByRegion(activeYear);
             // load avg pipeline per person
             await this.loadAvgPipelinePerPerson(activeYear);
             // load avg pipeline per person by region
             await this.loadAvgPipelinePerPersonByRegion(activeYear);
             // load gauge meter data
             await this.loadGaugeData(activeYear);

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
    setFilter = async (name, evOrValue) => {
        const value = (evOrValue && evOrValue.target && evOrValue.target.value !== undefined) ? evOrValue.target.value : evOrValue;
        this.state.filters[name] = value;

        // Get the active year for filtering
        const yearToLoad = (this.state.filters && this.state.filters.year && this.state.filters.year !== 'All') ? Number(this.state.filters.year) : (new Date()).getFullYear();

        // If year filter changed, reload stage counts and revenue summary
        if (name === 'year') {
            try {
                const stageCounts = await this.rpc("/plb/stage_counts", { year: yearToLoad });
                if (stageCounts) {
                    this.state.stageCounts = stageCounts;
                }

                const revenueSummary = await this.rpc("/plb/revenue_summary", { year: yearToLoad });
                if (revenueSummary) {
                    this.state.revenueSummary = revenueSummary;
                }
            } catch (err) {
                console.error('Failed to reload stage counts or revenue summary:', err);
            }
        }

        // recompute monthly totals (table) based on filtered rows
        this.computeTotals();
        // reload hit rate and pie based on filters (use selected year or current year)
        this.loadHitRateFromRows(yearToLoad);
        this.loadHitRateByRegion(yearToLoad);
        this.loadPipelineSeries(yearToLoad);
        this.loadPipelineByRegion(yearToLoad);
        this.loadAvgPipelinePerPerson(yearToLoad);
        this.loadAvgPipelinePerPersonByRegion(yearToLoad);
        this.loadGaugeData(yearToLoad);
    }

    // Reset all filters to 'All' (include year) and recompute totals
    resetFilters = async () => {
        // Reset filters but default year to the current year (no 'All')
        this.state.filters = { salesperson: 'All', stage: 'All', service: 'All', year: String((new Date()).getFullYear()) };
        const yearToLoad = Number(this.state.filters.year);

        // Reload stage counts and revenue summary for the current year
        try {
            const stageCounts = await this.rpc("/plb/stage_counts", { year: yearToLoad });
            if (stageCounts) {
                this.state.stageCounts = stageCounts;
            }

            const revenueSummary = await this.rpc("/plb/revenue_summary", { year: yearToLoad });
            if (revenueSummary) {
                this.state.revenueSummary = revenueSummary;
            }
        } catch (err) {
            console.error('Failed to reload stage counts or revenue summary:', err);
        }

        this.computeTotals();
        this.loadHitRateFromRows(yearToLoad);
        this.loadHitRateByRegion(yearToLoad);
        this.loadPipelineSeries(yearToLoad);
        this.loadPipelineByRegion(yearToLoad);
        this.loadAvgPipelinePerPerson(yearToLoad);
        this.loadAvgPipelinePerPersonByRegion(yearToLoad);
        this.loadGaugeData(yearToLoad);
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

    // Helper: get gauge color based on percentage zones
    getGaugeColor(percentage) {
        if (percentage < 50) {
            return '#C62828'; // Red - Fail
        } else if (percentage >= 50 && percentage < 70) {
            return '#F57C00'; // Orange - Entry
        } else if (percentage >= 70 && percentage <= 100) {
            return '#0D47A1'; // Blue - Target (70-100%)
        } else {
            return '#2E7D32'; // Green - Exceeded (>100%)
        }
    }

    // Helper: get status label based on percentage
    getGaugeStatus(percentage) {
        if (percentage < 50) {
            return 'FAIL';
        } else if (percentage >= 50 && percentage < 70) {
            return 'ENTRY';
        } else if (percentage >= 70 && percentage <= 100) {
            return 'TARGET';
        } else {
            return 'EXCEEDED';
        }
    }

    // Helper: generate gauge arc path
    getGaugeArcPath(percentage) {
        // Semi-circle gauge with flat side at Y=100 (bottom)
        // Arc goes from left (180°) to right (0° or 360°)
        // Support up to 120% to show exceeded performance
        const maxPercentage = 120; // Extended to 120% to show exceeded
        const clampedPercentage = Math.min(maxPercentage, Math.max(0, percentage));

        // If percentage is 0, return empty path
        if (clampedPercentage === 0) {
            return '';
        }

        // Convert percentage to angle (180° to 360°, or equivalently 180° to 0°)
        // At 0%: angle = 180° (left side)
        // At 60%: angle = 270° (bottom/center) - maps 50% of 120% range
        // At 100%: angle = 330° (83.33% of arc)
        // At 120%: angle = 360° (0°, right side - full arc)
        const startAngle = 180; // degrees
        const endAngle = 180 + (clampedPercentage / maxPercentage) * 180; // 180° to 360° for 0-120%
        const endAngleRad = (endAngle * Math.PI) / 180;

        const cx = 100; // center x
        const cy = 100; // center y
        const radius = 80;

        const startX = cx - radius; // Start at 180° (left side) = 20
        const startY = cy; // Y = 100
        const endX = cx + radius * Math.cos(endAngleRad);
        const endY = cy + radius * Math.sin(endAngleRad);

        // For half-circle, largeArcFlag should always be 0 (since we never go more than 180°)
        // sweepFlag should be 1 (clockwise)
        return `M ${startX} ${startY} A ${radius} ${radius} 0 0 1 ${endX} ${endY}`;
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

    // Load Pipeline YTD by Region from server
    loadPipelineByRegion = async (year) => {
        try {
            if (!year || year === 'All') year = (new Date()).getFullYear();
            const resp = await this.rpc("/plb/pipeline_ytd_by_region", { year: Number(year) });
            if (resp && resp.regions) {
                this.state.pipelineByRegion = resp;
                this.computePipelineRegionSeries(resp);
            } else {
                this.state.pipelineByRegion = { year: year, months: [], regions: {} };
                this.state.pipelineRegionSeries = { regions: [], months: [], ticks: [], maxVal: 1 };
            }
        } catch (e) {
            console.error('loadPipelineByRegion error', e);
            this.state.pipelineByRegion = { year: year, months: [], regions: {} };
            this.state.pipelineRegionSeries = { regions: [], months: [], ticks: [], maxVal: 1 };
        }
    }

    // Compute bar chart series for pipeline YTD by region
    computePipelineRegionSeries = (resp) => {
        try {
            const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            const w = 600, h = 320;
            const marginLeft = 80, marginRight = 20, marginTop = 20, marginBottom = 60;
            const plotW = w - marginLeft - marginRight;
            const plotH = h - marginTop - marginBottom;

            const regions = resp.regions || {};
            // Filter out 'unknown' regions and sort in specific order: Central, Southern, Northern
            const regionOrder = ['central', 'southern', 'northern'];
            const regionKeys = regionOrder.filter(k => regions[k] && k !== 'unknown');

            // Define specific colors for regions using brand palette
            const colorMap = {
                'southern': '#2E7D32',  // Professional green (complementary)
                'northern': '#C62828',  // Primary Red (brand)
                'central': '#0D47A1'    // Primary Blue (brand)
            };

            // Compute max value across all regions and months (excluding unknown)
            let maxVal = 1;
            regionKeys.forEach(key => {
                const ytd = regions[key].ytd || [];
                ytd.forEach(v => { if (v > maxVal) maxVal = v; });
            });

            // X positions for each month (center of bar group)
            const monthWidth = plotW / 12;
            const barGroupWidth = monthWidth * 0.9; // 90% of month space
            const barWidth = regionKeys.length > 0 ? barGroupWidth / regionKeys.length : 20;

            const monthPositions = [];
            for (let i = 0; i < 12; i++) {
                const x = marginLeft + (i * monthWidth) + (monthWidth / 2);
                monthPositions.push({ x: x, label: months[i] });
            }

            // Build bar data for each region
            const regionSeries = regionKeys.map((key, regionIdx) => {
                const data = regions[key];
                const ytd = data.ytd || [];
                const bars = [];

                for (let i = 0; i < 12; i++) {
                    const val = ytd[i] || 0;
                    if (val > 0) {
                        // Calculate bar position and dimensions
                        const barX = marginLeft + (i * monthWidth) + (regionIdx * barWidth);
                        const barHeight = (val / maxVal) * plotH;
                        const barY = marginTop + plotH - barHeight;

                        bars.push({
                            x: barX,
                            y: barY,
                            width: barWidth,
                            height: barHeight,
                            value: val,
                            month: months[i],
                            monthIdx: i,
                        });
                    }
                }

                return {
                    key: key,
                    label: data.label || key,
                    color: colorMap[key] || '#6f42c1',  // fallback to purple for any other regions
                    bars: bars,
                };
            });

            // Y-axis ticks
            const tickCount = 4;
            const step = Math.ceil((maxVal) / tickCount * 10) / 10;
            const ticks = [];
            for (let i = 0; i <= tickCount; i++) {
                const val = i * step;
                const y = marginTop + plotH - ((val / maxVal) * plotH);
                ticks.push({ y: y, label: `${val.toFixed(1)}` });
            }

            this.state.pipelineRegionSeries = {
                regions: regionSeries,
                months: monthPositions,
                ticks: ticks,
                maxVal: maxVal,
            };
        } catch (e) {
            console.error('computePipelineRegionSeries error', e);
            this.state.pipelineRegionSeries = { regions: [], months: [], ticks: [], maxVal: 1 };
        }
    }

    // Load gauge data for the YTD Rev Target and Realized Rev Target gauges
    loadGaugeData = async (year) => {
        try {
            if (!year || year === 'All') year = (new Date()).getFullYear();
            const gaugeData = await this.rpc('/plb/gauge_data', { year: Number(year) });
            if (gaugeData) {
                this.state.company_yearly_target = gaugeData.company_yearly_target || 0;
                this.state.total_ytd_revenue = gaugeData.total_ytd_revenue || 0;
                this.state.total_realized_revenue = gaugeData.total_realized_revenue || 0;
                this.state.ytd_percentage = gaugeData.ytd_percentage || 0;
                this.state.realized_percentage = gaugeData.realized_percentage || 0;
            }
            console.debug('loadGaugeData: loaded gauge data', gaugeData);
        } catch (e) {
            console.error('loadGaugeData error', e);
            this.state.company_yearly_target = 0;
            this.state.total_ytd_revenue = 0;
            this.state.total_realized_revenue = 0;
            this.state.ytd_percentage = 0;
            this.state.realized_percentage = 0;
        }
    }

    // Tooltip for pipeline region bars
    showPipelineRegionBar = (bar, region, ev) => {
        try {
            if (!bar || !region) return;
            ev = ev || window.event || {};
            const clientX = typeof ev.clientX === 'number' ? ev.clientX : (ev.pageX || 0) - (window.scrollX || 0);
            const clientY = typeof ev.clientY === 'number' ? ev.clientY : (ev.pageY || 0) - (window.scrollY || 0);
            const left = Math.max(4, Math.min(window.innerWidth - 240, clientX + 12));
            const top = Math.max(4, Math.min(window.innerHeight - 40, clientY + 12));
            const html = `${bar.month} - ${region.label}: <strong>${Number(bar.value).toFixed(2)} M</strong>`;
            this._showTextTooltip('Pipeline YTD by Region', html, left, top);
        } catch (e) { console.error('showPipelineRegionBar', e); }
    }

    // Load Avg Pipeline per Person from server
    loadAvgPipelinePerPerson = async (year) => {
        try {
            if (!year || year === 'All') year = (new Date()).getFullYear();
            const resp = await this.rpc("/plb/avg_pipeline_per_person", { year: Number(year) });
            if (resp && resp.avg_per_person) {
                this.state.avgPipelinePerPerson = resp;
                this.computeAvgPipelinePerPersonSeries(resp);
            } else {
                this.state.avgPipelinePerPerson = { year: year, months: [], avg_per_person: [] };
                this.state.avgPipelinePerPersonSeries = { pathSegments: [], points: [], months: [], ticks: [], maxVal: 1 };
            }
        } catch (e) {
            console.error('loadAvgPipelinePerPerson error', e);
            this.state.avgPipelinePerPerson = { year: year, months: [], avg_per_person: [] };
            this.state.avgPipelinePerPersonSeries = { pathSegments: [], points: [], months: [], ticks: [], maxVal: 1 };
        }
    }

    // Compute line chart series for avg pipeline per person
    computeAvgPipelinePerPersonSeries = (resp) => {
        try {
            const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            const w = 600, h = 320;
            const marginLeft = 80, marginRight = 20, marginTop = 20, marginBottom = 60;
            const plotW = w - marginLeft - marginRight;
            const plotH = h - marginTop - marginBottom;

            const avgData = resp.avg_per_person || [];

            // Compute max value for scaling
            let maxVal = 1;
            avgData.forEach(v => { if (v > maxVal) maxVal = v; });

            // X positions for each month (evenly spaced)
            const monthPositions = [];
            for (let i = 0; i < 12; i++) {
                const x = marginLeft + (i * (plotW / 11));
                monthPositions.push({ x: x, label: months[i] });
            }

            // Build points and line segments
            const points = [];
            const segments = [];

            for (let i = 0; i < 12; i++) {
                const val = avgData[i] || 0;
                if (val > 0) {
                    const x = monthPositions[i].x;
                    const y = marginTop + ((1 - Math.min(val / maxVal, 1)) * plotH);
                    points.push({
                        x: x,
                        y: y,
                        value: val,
                        month: months[i],
                        idx: i,
                    });
                }
            }

            // Create line segments connecting points
            for (let i = 1; i < points.length; i++) {
                const p0 = points[i-1];
                const p1 = points[i];
                segments.push({ d: `M ${p0.x} ${p0.y} L ${p1.x} ${p1.y}` });
            }

            // Compute Y-axis ticks
            const tickCount = 4;
            const step = Math.ceil((maxVal) / tickCount * 10) / 10;
            const ticks = [];
            for (let i = 0; i <= tickCount; i++) {
                const val = i * step;
                const y = marginTop + ((1 - Math.min(val / maxVal, 1)) * plotH);
                ticks.push({ y: y, label: `${val.toFixed(1)}` });
            }

            this.state.avgPipelinePerPersonSeries = {
                pathSegments: segments,
                points: points,
                months: monthPositions,
                ticks: ticks,
                maxVal: maxVal,
            };
        } catch (e) {
            console.error('computeAvgPipelinePerPersonSeries error', e);
            this.state.avgPipelinePerPersonSeries = { pathSegments: [], points: [], months: [], ticks: [], maxVal: 1 };
        }
    }

    // Tooltip for avg pipeline per person points
    showAvgPipelinePoint = (pt, ev) => {
        try {
            if (!pt) return;
            ev = ev || window.event || {};
            const clientX = typeof ev.clientX === 'number' ? ev.clientX : (ev.pageX || 0) - (window.scrollX || 0);
            const clientY = typeof ev.clientY === 'number' ? ev.clientY : (ev.pageY || 0) - (window.scrollY || 0);
            const left = Math.max(4, Math.min(window.innerWidth - 240, clientX + 12));
            const top = Math.max(4, Math.min(window.innerHeight - 40, clientY + 12));
            const html = `${pt.month}: <strong>${Number(pt.value).toFixed(2)} M</strong>`;
            this._showTextTooltip('Avg Pipeline/Person', html, left, top);
        } catch (e) { console.error('showAvgPipelinePoint', e); }
    }

    // Load Avg Pipeline per Person by Region from server
    loadAvgPipelinePerPersonByRegion = async (year) => {
        try {
            if (!year || year === 'All') year = (new Date()).getFullYear();
            const resp = await this.rpc("/plb/avg_pipeline_per_person_by_region", { year: Number(year) });
            if (resp && resp.regions) {
                this.state.avgPipelinePerPersonByRegion = resp;
                this.computeAvgPipelinePerPersonByRegionSeries(resp);
            } else {
                this.state.avgPipelinePerPersonByRegion = { year: year, months: [], regions: {} };
                this.state.avgPipelinePerPersonByRegionSeries = { regions: [], months: [], ticks: [], maxVal: 1 };
            }
        } catch (e) {
            console.error('loadAvgPipelinePerPersonByRegion error', e);
            this.state.avgPipelinePerPersonByRegion = { year: year, months: [], regions: {} };
            this.state.avgPipelinePerPersonByRegionSeries = { regions: [], months: [], ticks: [], maxVal: 1 };
        }
    }

    // Compute line chart series for avg pipeline per person by region
    computeAvgPipelinePerPersonByRegionSeries = (resp) => {
        try {
            const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            const w = 600, h = 320;
            const marginLeft = 80, marginRight = 20, marginTop = 20, marginBottom = 60;
            const plotW = w - marginLeft - marginRight;
            const plotH = h - marginTop - marginBottom;

            const regions = resp.regions || {};
            // Filter out 'unknown' regions and sort in specific order: Central, Southern, Northern
            const regionOrder = ['central', 'southern', 'northern'];
            const regionKeys = regionOrder.filter(k => regions[k] && k !== 'unknown');

            // Define specific colors for regions using brand palette
            const colorMap = {
                'southern': '#2E7D32',  // Professional green (complementary)
                'northern': '#C62828',  // Primary Red (brand)
                'central': '#0D47A1'    // Primary Blue (brand)
            };

            // Compute max value across all regions and months
            let maxVal = 1;
            regionKeys.forEach(key => {
                const avgData = regions[key].avg_per_person || [];
                avgData.forEach(v => { if (v > maxVal) maxVal = v; });
            });

            // X positions for each month (evenly spaced)
            const monthPositions = [];
            for (let i = 0; i < 12; i++) {
                const x = marginLeft + (i * (plotW / 11));
                monthPositions.push({ x: x, label: months[i] });
            }

            // Build line data for each region
            const regionSeries = regionKeys.map((key) => {
                const data = regions[key];
                const avgData = data.avg_per_person || [];
                const points = [];
                const segments = [];

                for (let i = 0; i < 12; i++) {
                    const val = avgData[i] || 0;
                    if (val > 0) {
                        const x = monthPositions[i].x;
                        const y = marginTop + ((1 - Math.min(val / maxVal, 1)) * plotH);
                        points.push({
                            x: x,
                            y: y,
                            value: val,
                            month: months[i],
                            idx: i,
                        });
                    }
                }

                // Create line segments connecting points
                for (let i = 1; i < points.length; i++) {
                    const p0 = points[i-1];
                    const p1 = points[i];
                    segments.push({ d: `M ${p0.x} ${p0.y} L ${p1.x} ${p1.y}` });
                }

                return {
                    key: key,
                    label: data.label || key,
                    color: colorMap[key] || '#6f42c1',  // fallback to purple
                    points: points,
                    segments: segments,
                };
            });

            // Compute Y-axis ticks
            const tickCount = 4;
            const step = Math.ceil((maxVal) / tickCount * 10) / 10;
            const ticks = [];
            for (let i = 0; i <= tickCount; i++) {
                const val = i * step;
                const y = marginTop + ((1 - Math.min(val / maxVal, 1)) * plotH);
                ticks.push({ y: y, label: `${val.toFixed(1)}` });
            }

            this.state.avgPipelinePerPersonByRegionSeries = {
                regions: regionSeries,
                months: monthPositions,
                ticks: ticks,
                maxVal: maxVal,
            };
        } catch (e) {
            console.error('computeAvgPipelinePerPersonByRegionSeries error', e);
            this.state.avgPipelinePerPersonByRegionSeries = { regions: [], months: [], ticks: [], maxVal: 1 };
        }
    }

    // Tooltip for avg pipeline per person by region points
    showAvgPipelineRegionPoint = (pt, region, ev) => {
        try {
            if (!pt || !region) return;
            ev = ev || window.event || {};
            const clientX = typeof ev.clientX === 'number' ? ev.clientX : (ev.pageX || 0) - (window.scrollX || 0);
            const clientY = typeof ev.clientY === 'number' ? ev.clientY : (ev.pageY || 0) - (window.scrollY || 0);
            const left = Math.max(4, Math.min(window.innerWidth - 240, clientX + 12));
            const top = Math.max(4, Math.min(window.innerHeight - 40, clientY + 12));
            const html = `${pt.month} - ${region.label}: <strong>${Number(pt.value).toFixed(2)} M</strong>`;
            this._showTextTooltip('Avg Pipeline/Person by Region', html, left, top);
        } catch (e) { console.error('showAvgPipelineRegionPoint', e); }
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

            // Use same color mapping as Pipeline by Region chart - brand palette
            const colorMap = {
                'southern': '#2E7D32',  // Professional green (complementary)
                'northern': '#C62828',  // Primary Red (brand)
                'central': '#0D47A1'    // Primary Blue (brand)
            };
            const regionsArr = [];
            // Filter out 'unknown' regions
            const regionKeys = Object.keys(data.regions || {}).filter(k => k !== 'unknown');
            regionKeys.forEach((k, idx) => {
                const reg = data.regions[k];
                const color = colorMap[k] || '#4A4A4A';  // fallback to secondary text color for any other regions
                const vals = Array.isArray(reg.hit_rate_percent) ? reg.hit_rate_percent : Array(12).fill(null);
                const valsPrev = Array.isArray(reg.hit_rate_percent_prev) ? reg.hit_rate_percent_prev : Array(12).fill(null);
                // build current series
                const sCur = { segments: [], flatPoints: [] };
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
                const sPrev = { segments: [], flatPoints: [] };
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
<style>
    /* ===== BRAND COLOR PALETTE ===== */
    /* Core Brand Colors */
    /* Primary Red: #C62828 - CTAs, alerts, highlights */
    /* Primary Blue: #0D47A1 - Headers, navigation, links */
    /* White: #FFFFFF - Backgrounds, cards */

    /* Supporting Neutrals */
    /* Primary Text: #1A1A1A - Main body text */
    /* Secondary Text: #4A4A4A - Subtext, captions */
    /* Light Gray: #F2F4F7 - Section backgrounds */
    /* Border Gray: #D0D5DD - Borders, dividers */

    /* Global Dashboard Styles */
    .plb-dashboard-container {
        background: #F2F4F7;
        min-height: 100vh;
        padding: 1.5rem;
    }

    /* Mobile optimizations */
    @media (max-width: 768px) {
        .plb-dashboard-container {
            padding: 1rem;
        }
    }

    /* Header styling */
    .plb-dashboard-header {
        background: #0D47A1;
        color: #FFFFFF;
        padding: 2rem;
        border-radius: 8px;
        margin-bottom: 2rem;
        box-shadow: 0 2px 8px rgba(13, 71, 161, 0.2);
        border: 1px solid #0D47A1;
    }

    @media (max-width: 768px) {
        .plb-dashboard-header {
            padding: 1.5rem 1rem;
            margin-bottom: 1.5rem;
        }
        .plb-dashboard-header h3 {
            font-size: 1.5rem !important;
        }
    }

    /* Summary Cards */
    .plb-summary-card {
        border: 1px solid #D0D5DD;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
        overflow: hidden;
        margin-bottom: 1rem;
        background: #FFFFFF;
    }

    .plb-summary-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        border-color: #0D47A1;
    }

    .plb-summary-card .card-body {
        padding: 1.5rem;
        border-left: 4px solid transparent;
    }

    .plb-summary-card.card-blue .card-body {
        border-left-color: #0D47A1;
    }

    .plb-summary-card.card-red .card-body {
        border-left-color: #C62828;
    }

    .plb-summary-card h6 {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
        color: #4A4A4A;
        margin-bottom: 0.5rem;
    }

    .plb-summary-card h3 {
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0;
        color: #1A1A1A;
    }

    @media (max-width: 768px) {
        .plb-summary-card h3 {
            font-size: 1.5rem;
        }
    }

    /* Filter Section */
    .plb-filters-card {
        background: #FFFFFF;
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 2rem;
        border: 1px solid #D0D5DD;
        border-top: 3px solid #0D47A1;
    }

    .plb-filters-row {
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .plb-filter-item {
        flex: 1;
        min-width: 150px;
    }

    @media (max-width: 768px) {
        .plb-filter-item {
            flex: 1 1 100%;
            min-width: 100%;
        }
    }

    .plb-filter-item label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
        color: #4A4A4A;
        margin-bottom: 0.5rem;
    }

    .plb-filter-item select {
        border-radius: 6px;
        border: 1px solid #D0D5DD;
        transition: all 0.2s ease;
        color: #1A1A1A;
    }

    .plb-filter-item select:focus {
        border-color: #0D47A1;
        box-shadow: 0 0 0 3px rgba(13, 71, 161, 0.1);
        outline: none;
    }

    /* Pipeline Stages Pills */
    .plb-stages-header {
        font-size: 1rem;
        font-weight: 600;
        color: #1A1A1A;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #D0D5DD;
    }

    .plb-stages-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
    }

    .plb-stage-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border-radius: 50px;
        font-size: 0.875rem;
        font-weight: 500;
        background: #0D47A1;
        color: #FFFFFF;
        box-shadow: 0 2px 4px rgba(13, 71, 161, 0.2);
        transition: all 0.3s ease;
        border: none;
    }

    .plb-stage-pill:hover {
        background: #0B3A82;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(13, 71, 161, 0.3);
    }

    .plb-stage-pill .badge {
        background: #C62828;
        color: #FFFFFF;
        padding: 0.25rem 0.5rem;
        border-radius: 50px;
        font-size: 0.75rem;
        font-weight: 600;
        min-width: 24px;
        text-align: center;
    }

    /* Chart Cards */
    .plb-chart-card {
        border: 1px solid #D0D5DD;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
        background: #FFFFFF;
    }

    .plb-chart-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        border-top-color: #C62828;
    }

    .plb-chart-card .card-header {
        background: #FFFFFF;
        border-bottom: 2px solid #F2F4F7;
        padding: 1.25rem 1.5rem;
        border-radius: 8px 8px 0 0;
    }

    .plb-chart-card .card-header h5 {
        font-size: 1rem;
        font-weight: 600;
        color: #1A1A1A;
        margin: 0;
    }

    .plb-chart-card .card-body {
        padding: 1.5rem;
    }

    /* Responsive chart containers */
    @media (max-width: 768px) {
        .plb-chart-card .card-body {
            padding: 1rem;
        }
        .plb-chart-card .position-relative {
            height: 250px !important;
        }
        .plb-chart-card .card-header h5 {
            font-size: 0.9rem;
        }
    }

    /* Legend responsive styles */
    .plb-legend {
        display: flex;
        gap: 1rem;
        justify-content: center;
        flex-wrap: wrap;
        margin-top: 1rem;
    }

    .plb-legend-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .plb-legend-color {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 2px;
    }

    .plb-legend-label {
        font-size: 0.875rem;
        margin: 0;
        color: #1A1A1A;
    }

    @media (max-width: 576px) {
        .plb-legend {
            gap: 0.5rem;
        }
        .plb-legend-label {
            font-size: 0.75rem;
        }
    }

    /* Table responsive improvements */
    .plb-table-container {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }

    @media (max-width: 992px) {
        .plb-data-table {
            font-size: 11px;
        }
        .plb-data-table th,
        .plb-data-table td {
            padding: 6px 4px;
            white-space: nowrap;
        }
    }

    /* Loading state */
    .plb-loading {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 400px;
    }

    .plb-loading .spinner-border {
        width: 3rem;
        height: 3rem;
        border-width: 0.3rem;
        color: #0D47A1;
    }

    .plb-loading p {
        color: #4A4A4A;
    }

    /* Smooth transitions */
    * {
        transition: background-color 0.2s ease, border-color 0.2s ease;
    }

    /* Scrollbar styling */
    .plb-table-container::-webkit-scrollbar {
        height: 8px;
    }

    .plb-table-container::-webkit-scrollbar-track {
        background: #F2F4F7;
        border-radius: 10px;
    }

    .plb-table-container::-webkit-scrollbar-thumb {
        background: #0D47A1;
        border-radius: 10px;
    }

    .plb-table-container::-webkit-scrollbar-thumb:hover {
        background: #0B3A82;
    }

    /* Gauge Meter Styles */
    .plb-gauge-container {
        display: flex;
        gap: 2rem;
        justify-content: center;
        margin-bottom: 2rem;
        flex-wrap: wrap;
    }

    .plb-gauge-card {
        background: #FFFFFF;
        border: 1px solid #D0D5DD;
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        text-align: center;
        min-width: 280px;
        flex: 1;
        max-width: 400px;
    }

    .plb-gauge-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #1A1A1A;
        margin-bottom: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .plb-gauge-svg {
        width: 100%;
        height: auto;
        max-width: 200px;
        margin: 0 auto;
        display: block;
        overflow: hidden;
    }

    .plb-gauge-background {
        fill: none;
        stroke: #F2F4F7;
        stroke-width: 12;
        stroke-linecap: round;
    }

    .plb-gauge-arc {
        fill: none;
        stroke-width: 12;
        stroke-linecap: round;
        transition: stroke 0.3s ease;
    }

    .plb-gauge-value {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1A1A1A;
        margin-top: 0.5rem;
    }

    .plb-gauge-label {
        font-size: 0.85rem;
        color: #4A4A4A;
        margin-top: 0.25rem;
        margin-bottom: 0.75rem;
    }

    .plb-gauge-status {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 50px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 0.5rem;
    }

    .plb-gauge-status.fail {
        background: rgba(198, 40, 40, 0.1);
        color: #C62828;
    }

    .plb-gauge-status.entry {
        background: rgba(245, 124, 0, 0.1);
        color: #F57C00;
    }

    .plb-gauge-status.target {
        background: rgba(13, 71, 161, 0.1);
        color: #0D47A1;
    }

    .plb-gauge-status.exceeded {
        background: rgba(46, 125, 50, 0.1);
        color: #2E7D32;
    }

    .plb-gauge-zones {
        display: flex;
        gap: 0.75rem;
        justify-content: center;
        margin-top: 1rem;
        flex-wrap: wrap;
    }

    .plb-gauge-zone {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.75rem;
        color: #4A4A4A;
    }

    .plb-gauge-zone-color {
        width: 10px;
        height: 10px;
        border-radius: 2px;
    }

    @media (max-width: 768px) {
        .plb-gauge-container {
            gap: 1rem;
        }
        .plb-gauge-card {
            min-width: 100%;
        }
    }
</style>

<div class="plb-dashboard-container" style="overflow: auto; height: 100%;">
    <!-- Dashboard Header -->
    <div class="plb-dashboard-header">
        <h3 class="mb-0" style="font-size: 1.75rem; font-weight: 700; letter-spacing: 0.5px; color: #FFFFFF;">
            PLB Dashboard
        </h3>
        <p class="mb-0 mt-2" style="font-size: 0.95rem; color: #FFFFFF; opacity: 0.9;">Comprehensive business analytics</p>
    </div>

    <!-- Loading state -->
    <t t-if="state.loading">
        <div class="plb-loading">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3" style="color: #6c757d; font-weight: 500;">Loading dashboard data...</p>
        </div>
    </t>

    <t t-else="">
        <!-- Revenue Summary Cards -->
        <div class="row g-3 mb-4">
            <div class="col-12 col-sm-6 col-lg-3">
                <div class="card plb-summary-card card-blue text-center">
                    <div class="card-body">
                        <h6>Total Leads</h6>
                        <h3 style="font-size: 1.25rem;"><t t-esc="state.revenueSummary.lead_count"/></h3>
                    </div>
                </div>
            </div>
            <div class="col-12 col-sm-6 col-lg-3">
                <div class="card plb-summary-card card-blue text-center">
                    <div class="card-body">
                        <h6>Expected Revenue</h6>
                        <h3 style="font-size: 1.25rem;"><t t-esc="formatCurrency(state.revenueSummary.total_expected_revenue)"/></h3>
                    </div>
                </div>
            </div>
            <div class="col-12 col-sm-6 col-lg-3">
                <div class="card plb-summary-card card-red text-center">
                    <div class="card-body">
                        <h6>Realized FY2025</h6>
                        <h3 style="font-size: 1.25rem;"><t t-esc="formatCurrency(state.revenueSummary.total_realized_revenue)"/></h3>
                    </div>
                </div>
            </div>
            <div class="col-12 col-sm-6 col-lg-3">
                <div class="card plb-summary-card card-red text-center">
                    <div class="card-body">
                        <h6>Carry Forward</h6>
                        <h3 style="font-size: 1.25rem;"><t t-esc="formatCurrency(state.totalCarryForward)"/></h3>
                    </div>
                </div>
            </div>
        </div>

        <!-- Filters and Stage Counts -->
        <div class="plb-filters-card">
            <!-- Filters Row -->
            <div class="plb-filters-row">
                <div class="plb-filter-item">
                    <label class="form-label">Salesperson</label>
                    <select class="form-select form-select-sm" t-att-value="state.filters.salesperson" t-on-change="ev => this.setFilter('salesperson', ev.target.value)">
                        <t t-foreach="state.salespersons" t-as="sp" t-key="sp">
                            <option t-att-value="sp"><t t-esc="sp"/></option>
                        </t>
                    </select>
                </div>
                <div class="plb-filter-item">
                    <label class="form-label">Stage</label>
                    <select class="form-select form-select-sm" t-att-value="state.filters.stage" t-on-change="ev => this.setFilter('stage', ev.target.value)">
                        <t t-foreach="state.stages" t-as="st" t-key="st">
                            <option t-att-value="st"><t t-esc="st"/></option>
                        </t>
                    </select>
                </div>
                <div class="plb-filter-item">
                    <label class="form-label">Service</label>
                    <select class="form-select form-select-sm" t-att-value="state.filters.service" t-on-change="ev => this.setFilter('service', ev.target.value)">
                        <t t-foreach="state.services" t-as="sv" t-key="sv">
                            <option t-att-value="sv"><t t-esc="sv"/></option>
                        </t>
                    </select>
                </div>
                <div class="plb-filter-item">
                    <label class="form-label">Year</label>
                    <select class="form-select form-select-sm" t-att-value="state.filters.year" t-on-change="ev => this.setFilter('year', ev.target.value)">
                        <t t-foreach="state.years" t-as="yr" t-key="yr">
                            <option t-att-value="yr"><t t-esc="yr"/></option>
                        </t>
                    </select>
                </div>
            </div>

            <!-- Pipeline Stages as Pills -->
            <div class="plb-stages-header">
                Pipeline Stages
            </div>
            <t t-if="Object.keys(state.stageCounts).length">
                <div class="plb-stages-container">
                    <t t-foreach="Object.entries(state.stageCounts)" t-as="entry" t-key="entry[0]">
                        <span class="plb-stage-pill">
                            <strong><t t-esc="entry[0]"/></strong>
                            <span class="badge"><t t-esc="entry[1]"/></span>
                        </span>
                    </t>
                </div>
            </t>
            <t t-else="">
                <div class="text-muted" style="font-style: italic;">No stage data available.</div>
            </t>
        </div>

        <!-- Gauge Meters -->
        <div class="plb-gauge-container">
            <!-- YTD Revenue Target Gauge -->
            <div class="plb-gauge-card">
                <h5 class="plb-gauge-title">YTD Rev Target (MYR mil)</h5>
                <svg class="plb-gauge-svg" viewBox="0 0 200 130">
                    <!-- Background arc (gray) -->
                    <path class="plb-gauge-background" d="M 20 100 A 80 80 0 0 1 180 100"/>

                    <!-- Progress arc (colored based on percentage) -->
                    <path class="plb-gauge-arc"
                          t-att-d="getGaugeArcPath(state.ytd_percentage)"
                          t-att-stroke="getGaugeColor(state.ytd_percentage)"/>

                    <!-- Percentage text -->
                    <text x="100" y="115" text-anchor="middle" font-size="20" font-weight="bold" fill="#1A1A1A">
                        <t t-esc="formatNumber(state.ytd_percentage)"/>%
                    </text>
                </svg>
                <div class="plb-gauge-value">
                    <t t-esc="formatNumber(state.total_ytd_revenue)"/> M
                </div>
                <div class="plb-gauge-label">Expected Revenue (Millions)</div>
                <span class="plb-gauge-status" t-att-class="getGaugeStatus(state.ytd_percentage).toLowerCase()">
                    <t t-esc="getGaugeStatus(state.ytd_percentage)"/>
                </span>
                <div class="plb-gauge-zones">
                    <div class="plb-gauge-zone">
                        <span class="plb-gauge-zone-color" style="background: #C62828;"></span>
                        <span>Fail</span>
                    </div>
                    <div class="plb-gauge-zone">
                        <span class="plb-gauge-zone-color" style="background: #F57C00;"></span>
                        <span>Entry</span>
                    </div>
                    <div class="plb-gauge-zone">
                        <span class="plb-gauge-zone-color" style="background: #0D47A1;"></span>
                        <span>Target</span>
                    </div>
                    <div class="plb-gauge-zone">
                        <span class="plb-gauge-zone-color" style="background: #2E7D32;"></span>
                        <span>Exceeded</span>
                    </div>
                </div>
            </div>

            <!-- Realized Revenue Target Gauge -->
            <div class="plb-gauge-card">
                <h5 class="plb-gauge-title">Realized Rev Target (MYR mil)</h5>
                <svg class="plb-gauge-svg" viewBox="0 0 200 130">
                    <!-- Background arc (gray) -->
                    <path class="plb-gauge-background" d="M 20 100 A 80 80 0 0 1 180 100"/>

                    <!-- Progress arc (colored based on percentage) -->
                    <path class="plb-gauge-arc"
                          t-att-d="getGaugeArcPath(state.realized_percentage)"
                          t-att-stroke="getGaugeColor(state.realized_percentage)"/>

                    <!-- Percentage text -->
                    <text x="100" y="115" text-anchor="middle" font-size="20" font-weight="bold" fill="#1A1A1A">
                        <t t-esc="formatNumber(state.realized_percentage)"/>%
                    </text>
                </svg>
                <div class="plb-gauge-value">
                    <t t-esc="formatNumber(state.total_realized_revenue)"/> M
                </div>
                <div class="plb-gauge-label">Monthly Subtotal YTD (Millions)</div>
                <span class="plb-gauge-status" t-att-class="getGaugeStatus(state.realized_percentage).toLowerCase()">
                    <t t-esc="getGaugeStatus(state.realized_percentage)"/>
                </span>
                <div class="plb-gauge-zones">
                    <div class="plb-gauge-zone">
                        <span class="plb-gauge-zone-color" style="background: #C62828;"></span>
                        <span>Fail</span>
                    </div>
                    <div class="plb-gauge-zone">
                        <span class="plb-gauge-zone-color" style="background: #F57C00;"></span>
                        <span>Entry</span>
                    </div>
                    <div class="plb-gauge-zone">
                        <span class="plb-gauge-zone-color" style="background: #0D47A1;"></span>
                        <span>Target</span>
                    </div>
                    <div class="plb-gauge-zone">
                        <span class="plb-gauge-zone-color" style="background: #2E7D32;"></span>
                        <span>Exceeded</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Two-column layout: Hit Rate Trend | Hit Rate by Dept/Region -->
        <div class="row mb-4 g-3">
            <div class="col-12 col-lg-6">
                <div class="card plb-chart-card h-100">
                    <div class="card-header">
                        <h5>Hit Rate Trend</h5>
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
                                            <circle t-att-cx="pt.x" t-att-cy="pt.y" r="4" fill="#0D47A1"
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

                        <div class="plb-legend">
                            <div class="plb-legend-item">
                                <span class="plb-legend-color" style="background:#0D47A1;"></span>
                                <small class="plb-legend-label">This Year</small>
                            </div>
                            <div class="plb-legend-item">
                                <span class="plb-legend-color" style="background:#4A4A4A;"></span>
                                <small class="plb-legend-label">Last Year</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-12 col-lg-6">
                <div class="card plb-chart-card h-100">
                    <div class="card-header">
                        <h5>Hit Rate by Dept/Region</h5>
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
                        <div class="plb-legend">
                            <t t-foreach="state.hitRateRegionSeries.regions || []" t-as="reg" t-key="reg.key">
                                <div class="plb-legend-item">
                                    <span class="plb-legend-color" t-att-style="'background:'+reg.color+';'"></span>
                                    <small class="plb-legend-label"><t t-esc="reg.label"/></small>
                                </div>
                            </t>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Second row: 4 columns for all pipeline charts -->
        <div class="row mb-4 g-3">
            <!-- Total pipeline (YTD) chart -->
            <div class="col-12 col-lg-3">
                <div class="card plb-chart-card h-100">
                    <div class="card-header">
                        <h5>Total pipeline (YTD)</h5>
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
                                            <path t-att-d="seg.d" fill="none" stroke="#0D47A1" stroke-width="2"/>
                                        </t>
                                    </g>
                                    <g class="data-points">
                                        <t t-foreach="state.pipelineSeries.points" t-as="pt" t-key="'pt-'+pt.idx">
                                            <circle t-att-cx="pt.x" t-att-cy="pt.y" r="4" fill="#0D47A1" opacity="0.95"
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
                            </svg>
                        </div>

                        <div class="plb-legend">
                            <div class="plb-legend-item">
                                <span class="plb-legend-color" style="background:#0D47A1;"></span>
                                <small class="plb-legend-label">Pipeline (Current year)</small>
                            </div>
                            <div class="plb-legend-item">
                                <span class="plb-legend-color" style="background:#4A4A4A;"></span>
                                <small class="plb-legend-label">Last year Pipeline</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Total pipeline (YTD) by Dept/Region chart -->
            <div class="col-12 col-lg-3">
                <div class="card plb-chart-card h-100">
                    <div class="card-header">
                        <h5>Total pipeline (YTD) by Dept/Region</h5>
                    </div>
                    <div class="card-body">
                        <div class="position-relative" style="height:320px;">
                            <svg width="100%" height="100%" viewBox="0 0 600 320" aria-label="Total pipeline YTD by Dept/Region chart">
                                <!-- Grid lines -->
                                <g class="grid" stroke="#e9ecef" stroke-width="0.6">
                                    <t t-foreach="state.pipelineRegionSeries &amp;&amp; state.pipelineRegionSeries.ticks || []" t-as="tk" t-key="'prtk-'+tk.y">
                                        <line t-att-x1="80" t-att-y1="tk.y" t-att-x2="580" t-att-y2="tk.y"/>
                                    </t>
                                </g>

                                <!-- Y axis -->
                                <g class="axis" fill="none" stroke="#333" stroke-width="0.9">
                                    <line x1="80" y1="20" x2="80" y2="260"/>
                                </g>

                                <!-- Bars for each region -->
                                <t t-if="state.pipelineRegionSeries &amp;&amp; state.pipelineRegionSeries.regions &amp;&amp; state.pipelineRegionSeries.regions.length">
                                    <t t-foreach="state.pipelineRegionSeries.regions" t-as="reg" t-key="'preg-'+reg.key">
                                        <g class="region-bars">
                                            <t t-foreach="reg.bars || []" t-as="bar" t-key="reg.key+'-bar-'+bar.monthIdx">
                                                <rect t-att-x="bar.x" t-att-y="bar.y" t-att-width="bar.width" t-att-height="bar.height"
                                                      t-att-fill="reg.color" opacity="0.85"
                                                      style="cursor:pointer; pointer-events:auto;"
                                                      t-on-mouseenter="ev => this.showPipelineRegionBar(bar, reg, ev)"
                                                      t-on-mousemove="ev => this.movePoint(bar, ev)"
                                                      t-on-mouseleave="this.hidePoint"/>
                                            </t>
                                        </g>
                                    </t>
                                </t>
                                <t t-else="">
                                    <g>
                                        <text x="300" y="160" text-anchor="middle" fill="#888" font-size="14px">No region data to display</text>
                                    </g>
                                </t>

                                <!-- Month labels on X axis -->
                                <t t-foreach="state.pipelineRegionSeries &amp;&amp; state.pipelineRegionSeries.months || []" t-as="mpos" t-key="'prm-'+mpos.label">
                                    <text t-att-x="mpos.x" t-att-y="275" text-anchor="middle" fill="#333" font-size="11px"><t t-esc="mpos.label"/></text>
                                </t>

                                <!-- Y-axis tick labels -->
                                <t t-foreach="state.pipelineRegionSeries &amp;&amp; state.pipelineRegionSeries.ticks || []" t-as="tk" t-key="'prtk2-'+tk.y">
                                    <text t-att-x="68" t-att-y="tk.y + 4" text-anchor="end" fill="#333" font-size="11px"><t t-esc="tk.label"/>M</text>
                                </t>

                                <!-- axis labels -->
                                <text x="330" y="295" text-anchor="middle" fill="#333" font-size="12px">Months</text>
                                <text x="18" y="140" text-anchor="middle" fill="#333" font-size="12px" transform="rotate(-90,18,140)">Revenue (MYR Mil)</text>
                            </svg>
                        </div>

                        <!-- Legend -->
                        <div class="plb-legend">
                            <t t-foreach="state.pipelineRegionSeries.regions || []" t-as="reg" t-key="'prleg-'+reg.key">
                                <div class="plb-legend-item">
                                    <span class="plb-legend-color" t-att-style="'background:'+reg.color+';'"></span>
                                    <small class="plb-legend-label"><t t-esc="reg.label"/></small>
                                </div>
                            </t>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Avg pipeline/person Chart -->
            <div class="col-12 col-lg-3">
                <div class="card plb-chart-card h-100">
                    <div class="card-header">
                        <h5>Avg pipeline/person</h5>
                    </div>
                    <div class="card-body">
                        <div class="position-relative" style="height:320px;">
                            <svg width="100%" height="100%" viewBox="0 0 600 320" aria-label="Avg pipeline per person chart">
                                <!-- Grid lines -->
                                <g class="grid" stroke="#e9ecef" stroke-width="0.6">
                                    <t t-foreach="state.avgPipelinePerPersonSeries &amp;&amp; state.avgPipelinePerPersonSeries.ticks || []" t-as="tk" t-key="'apptk-'+tk.y">
                                        <line t-att-x1="80" t-att-y1="tk.y" t-att-x2="580" t-att-y2="tk.y"/>
                                    </t>
                                </g>

                                <!-- Y axis -->
                                <g class="axis" fill="none" stroke="#333" stroke-width="0.9">
                                    <line x1="80" y1="20" x2="80" y2="260"/>
                                </g>

                                <!-- Line chart -->
                                <t t-if="state.avgPipelinePerPersonSeries &amp;&amp; state.avgPipelinePerPersonSeries.pathSegments &amp;&amp; state.avgPipelinePerPersonSeries.pathSegments.length">
                                    <g class="data-line">
                                        <t t-foreach="state.avgPipelinePerPersonSeries.pathSegments" t-as="seg" t-key="seg.d">
                                            <path t-att-d="seg.d" fill="none" stroke="#0D47A1" stroke-width="2"/>
                                        </t>
                                    </g>
                                    <g class="data-points">
                                        <t t-foreach="state.avgPipelinePerPersonSeries.points" t-as="pt" t-key="'appt-'+pt.idx">
                                            <circle t-att-cx="pt.x" t-att-cy="pt.y" r="4" fill="#0D47A1" opacity="0.95"
                                                    style="cursor:pointer; pointer-events:auto;"
                                                    t-on-mouseenter="ev => this.showAvgPipelinePoint(pt, ev)"
                                                    t-on-mousemove="ev => this.movePoint(pt, ev)"
                                                    t-on-mouseleave="this.hidePoint"/>
                                        </t>
                                    </g>
                                </t>
                                <t t-else="">
                                    <text x="300" y="160" text-anchor="middle" fill="#999" font-size="14px">No data available</text>
                                </t>

                                <!-- month labels on X axis -->
                                <t t-foreach="state.avgPipelinePerPersonSeries &amp;&amp; state.avgPipelinePerPersonSeries.months || []" t-as="mpos" t-key="'appm-'+mpos.label">
                                    <text t-att-x="mpos.x" t-att-y="280" text-anchor="middle" fill="#333" font-size="11px"><t t-esc="mpos.label"/></text>
                                </t>

                                <!-- y ticks labels -->
                                <t t-foreach="state.avgPipelinePerPersonSeries &amp;&amp; state.avgPipelinePerPersonSeries.ticks || []" t-as="tk" t-key="'apptl-'+tk.y">
                                    <text t-att-x="48" t-att-y="tk.y + 4" text-anchor="end" fill="#333" font-size="11px"><t t-esc="tk.label"/>M</text>
                                </t>

                                <!-- axis labels -->
                                <text x="300" y="300" text-anchor="middle" fill="#333" font-size="12px" font-weight="600">Month</text>
                                <text x="20" y="110" text-anchor="middle" fill="#333" font-size="12px" font-weight="600" transform="rotate(-90,20,140)">Avg Pipeline (MYR millions)</text>
                            </svg>
                        </div>

                        <!-- Legend -->
                        <div class="plb-legend">
                            <div class="plb-legend-item">
                                <span class="plb-legend-color" style="background:#0D47A1;"></span>
                                <small class="plb-legend-label">Total</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Avg pipeline/person by Region Chart -->
            <div class="col-12 col-lg-3">
                <div class="card plb-chart-card h-100">
                    <div class="card-header">
                        <h5>Avg pipeline/person by Region</h5>
                    </div>
                    <div class="card-body">
                        <div class="position-relative" style="height:320px;">
                            <svg width="100%" height="100%" viewBox="0 0 600 320" aria-label="Avg pipeline per person by Region chart">
                                <!-- Grid lines -->
                                <g class="grid" stroke="#e9ecef" stroke-width="0.6">
                                    <t t-foreach="state.avgPipelinePerPersonByRegionSeries &amp;&amp; state.avgPipelinePerPersonByRegionSeries.ticks || []" t-as="tk" t-key="'apprtk-'+tk.y">
                                        <line t-att-x1="80" t-att-y1="tk.y" t-att-x2="580" t-att-y2="tk.y"/>
                                    </t>
                                </g>

                                <!-- Y axis -->
                                <g class="axis" fill="none" stroke="#333" stroke-width="0.9">
                                    <line x1="80" y1="20" x2="80" y2="260"/>
                                </g>

                                <!-- Line charts for each region -->
                                <t t-if="state.avgPipelinePerPersonByRegionSeries &amp;&amp; state.avgPipelinePerPersonByRegionSeries.regions &amp;&amp; state.avgPipelinePerPersonByRegionSeries.regions.length">
                                    <t t-foreach="state.avgPipelinePerPersonByRegionSeries.regions" t-as="reg" t-key="'appreg-'+reg.key">
                                        <g class="region-line">
                                            <t t-foreach="reg.segments || []" t-as="seg" t-key="reg.key+'-seg-'+seg.d">
                                                <path t-att-d="seg.d" fill="none" t-att-stroke="reg.color" stroke-width="2"/>
                                            </t>
                                        </g>
                                        <g class="region-points">
                                            <t t-foreach="reg.points || []" t-as="pt" t-key="reg.key+'-pt-'+pt.idx">
                                                <circle t-att-cx="pt.x" t-att-cy="pt.y" r="4" t-att-fill="reg.color" opacity="0.95"
                                                        style="cursor:pointer; pointer-events:auto;"
                                                        t-on-mouseenter="ev => this.showAvgPipelineRegionPoint(pt, reg, ev)"
                                                        t-on-mousemove="ev => this.movePoint(pt, ev)"
                                                        t-on-mouseleave="this.hidePoint"/>
                                            </t>
                                        </g>
                                    </t>
                                </t>
                                <t t-else="">
                                    <text x="300" y="160" text-anchor="middle" fill="#999" font-size="14px">No data available</text>
                                </t>

                                <!-- month labels on X axis -->
                                <t t-foreach="state.avgPipelinePerPersonByRegionSeries &amp;&amp; state.avgPipelinePerPersonByRegionSeries.months || []" t-as="mpos" t-key="'apprm-'+mpos.label">
                                    <text t-att-x="mpos.x" t-att-y="280" text-anchor="middle" fill="#333" font-size="11px"><t t-esc="mpos.label"/></text>
                                </t>

                                <!-- y ticks labels -->
                                <t t-foreach="state.avgPipelinePerPersonByRegionSeries &amp;&amp; state.avgPipelinePerPersonByRegionSeries.ticks || []" t-as="tk" t-key="'apprtl-'+tk.y">
                                    <text t-att-x="48" t-att-y="tk.y + 4" text-anchor="end" fill="#333" font-size="11px"><t t-esc="tk.label"/>M</text>
                                </t>

                                <!-- axis labels -->
                                <text x="300" y="300" text-anchor="middle" fill="#333" font-size="12px" font-weight="600">Month</text>
                                <text x="20" y="110" text-anchor="middle" fill="#333" font-size="12px" font-weight="600" transform="rotate(-90,20,140)">Avg Pipeline (MYR millions)</text>
                            </svg>
                        </div>

                        <!-- Legend -->
                        <div class="plb-legend">
                            <t t-foreach="state.avgPipelinePerPersonByRegionSeries.regions || []" t-as="reg" t-key="'apprleg-'+reg.key">
                                <div class="plb-legend-item">
                                    <span class="plb-legend-color" t-att-style="'background:'+reg.color+';'"></span>
                                    <small class="plb-legend-label"><t t-esc="reg.label"/></small>
                                </div>
                            </t>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Data Table -->
        <div class="card plb-chart-card mb-5">
            <div class="card-header" style="background: #C62828; border: none;">
                <h4 class="mb-0" style="font-weight: 600; letter-spacing: 0.5px; color: #FFFFFF;">
                    Current Year YTD Gain
                </h4>
            </div>
            <div class="card-body p-0">
                <style>
                    /* Ensure table-bordered shows regular borders (Bootstrap may set these elsewhere) */
                    table.table-bordered th, table.table-bordered td { border: 1px solid #D0D5DD !important; }
                    /* Double border only on monthly subtotal cells (Jan..Dec) */
                    .plb-footer .plb-month-border { border-top: 3px double #1A1A1A !important; border-bottom: 3px double #1A1A1A !important; }
                    /* Remove the bottom border of subtotal's non-month cells so the double line doesn't continue across */
                    .plb-footer .plb-subtotal-no-bottom { border-bottom: none !important; }
                    /* Remove the top border of the cumulative row cells to avoid a full-width line between subtotal &amp; cumulative */
                    .plb-footer .plb-cumulative-no-top { border-top: none !important; }
                    /* Enhanced table styling */
                    .plb-data-table {
                        margin-bottom: 0;
                        border-radius: 0 0 8px 8px;
                    }
                    .plb-data-table thead th {
                        background: #F2F4F7;
                        font-weight: 700;
                        color: #1A1A1A;
                        text-transform: uppercase;
                        font-size: 11px;
                        letter-spacing: 0.5px;
                        padding: 12px 8px;
                        border-color: #D0D5DD;
                        position: sticky;
                        top: 0;
                        z-index: 10;
                        text-align: center;
                        vertical-align: middle;
                    }
                    .plb-data-table tbody tr {
                        transition: all 0.2s ease;
                    }
                    .plb-data-table tbody tr:hover {
                        background-color: rgba(13, 71, 161, 0.05);
                        box-shadow: 0 2px 4px rgba(13, 71, 161, 0.1);
                    }
                    .plb-data-table tbody td {
                        padding: 10px 8px;
                        vertical-align: middle;
                        font-size: 13px;
                        color: #1A1A1A;
                    }
                    .plb-footer tr {
                        background: #F2F4F7;
                    }
                    .plb-footer td {
                        font-weight: 600;
                        font-size: 13px;
                        color: #1A1A1A;
                    }
                    /* Alternating row colors for better readability */
                    .plb-data-table tbody tr:nth-child(even) {
                        background-color: #FFFFFF;
                    }
                    .plb-data-table tbody tr:nth-child(odd) {
                        background-color: #F2F4F7;
                    }
                </style>
                <div class="plb-table-container">
                    <table class="table table-bordered table-hover table-sm sticky-head plb-data-table mb-3" style="border-collapse:collapse; border-spacing:0;">
                        <thead class="table-light">
                            <tr>
                                <th rowspan="2">No.</th>
                                <th rowspan="2">Quarter</th>
                                <th rowspan="2">Sales</th>
                                <th rowspan="2">Stage</th>
                                <th rowspan="2">Services</th>
                                <th rowspan="2">Customer</th>
                                <th rowspan="2">Annualized Revenue</th>
                                <th colspan="12" class="text-center">Realized Revenue (Months)</th>
                                <th rowspan="2">Month</th>
                                <th rowspan="2">Week</th>
                                <th rowspan="2">Realized Revenue 2025</th>
                                <th rowspan="2">Carry Forward 2026</th>
                             </tr>
                            <tr>
                                <th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th>
                                <th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th>
                            </tr>
                        </thead>
                <tbody>
                    <t t-if="getFilteredTableRows() &amp;&amp; getFilteredTableRows().length">
                        <t t-set="contractRows" t-value="getFilteredTableRows().filter(r => r.stage &amp;&amp; r.stage.toLowerCase().includes('contract'))"/>
                        <t t-if="contractRows &amp;&amp; contractRows.length">
                            <tr t-foreach="contractRows" t-as="row" t-key="row.id">
                                <td class="text-center"><t t-esc="row_index + 1"/></td>
                                <td class="text-center"><t t-esc="row.quarter || '-'"/></td>
                                <td><t t-esc="formatText(row.salesperson)"/></td>
                                <td><t t-esc="row.stage || 'NULL'"/></td>
                                <td><t t-esc="formatText(row.services)"/></td>
                                <td><t t-esc="row.customer || 'NULL'"/></td>
                                <td class="text-end"><t t-esc="formatCurrency(row.sales)"/></td>

                                <!-- Loop for monthly revenue -->
                                <t t-foreach="row.monthlyRevenue || []" t-as="month" t-key="month">
                                    <td class="text-end"><t t-esc="formatCurrency(month)"/></td>
                                </t>

                                <td class="text-center"><t t-esc="row.month || '-'"/></td>
                                <td class="text-center"><t t-esc="row.week || '-'"/></td>
                                <td class="text-end"><t t-esc="formatCurrency(row.realizedRevenue)"/></td>
                                <td class="text-end"><t t-esc="formatCurrency(row.carryForward)"/></td>
                            </tr>
                        </t>
                        <t t-else="">
                            <tr>
                                <td colspan="21" class="text-center text-muted">No contract stage data available</td>
                            </tr>
                        </t>
                     </t>
                     <t t-else="">
                         <tr>
                            <td colspan="21" class="text-center text-muted">No data available</td>
                         </tr>
                     </t>
                 </tbody>
                 <tfoot class="plb-footer">
                     <!-- Emphasized subtotal row: double top/bottom border only on monthly columns -->
                     <tr style="font-weight:700; background:#f8f9fa;">
                         <!-- remove bottom border on the leading label cell so the double line won't continue across -->
                         <td colspan="7" class="text-end plb-subtotal-no-bottom"><strong>Monthly Subtotal</strong></td>
                         <!-- Double top and bottom border only on monthly columns (Jan..Dec) -->
                         <t t-foreach="state.monthlySubtotals" t-as="m" t-key="m">
                             <td class="text-end plb-month-border" style="font-weight:700;"><t t-esc="formatCurrency(m)"/></td>
                         </t>
                         <td colspan="4"></td>
                     </tr>

                     <!-- Cumulative row: slightly lighter styling, no full-width top border so the double line appears only under monthly columns -->
                     <tr style="font-weight:600; background:#ffffff;">
                         <td colspan="7" class="text-end plb-cumulative-no-top"><strong>Cumulative</strong></td>
                         <t t-foreach="state.monthlyCumulative" t-as="c" t-key="c">
                             <td class="text-end plb-cumulative-no-top" style="font-weight:600;"><t t-esc="formatCurrency(c)"/></td>
                         </t>
                         <td colspan="4"></td>
                     </tr>
                 </tfoot>
             </table>
                </div>
            </div>
        </div>
     </t>
 </div>
 `;

 registry.category("actions").add("PLB_dashboard_tag", PLBDashboard);

