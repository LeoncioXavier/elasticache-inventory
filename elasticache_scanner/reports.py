"""Report generation utilities."""

import json
import logging
from typing import List

import pandas as pd

logger = logging.getLogger(__name__)


def generate_html_report(df: pd.DataFrame, profiles: List[str], html_path: str, config) -> None:
    """Generate interactive HTML report with DataTables, charts and filters."""
    # Use DataTables + Bootstrap for sorting and per-column filters
    # Remove unwanted columns from the table view
    # Hide some columns in the HTML view (still kept in CSV/XLSX)
    # Keep CreationTime and CC in the HTML table — still drop Profile, ARN and Email for the UI view
    drop_cols = [c for c in ("Profile", "ARN", "Email") if c in df.columns]
    df_for_table = df.drop(columns=drop_cols) if drop_cols else df.copy()
    table_html = df_for_table.to_html(index=False, classes="table table-striped table-bordered", border=0)
    # Ensure the generated table has id="elasticache" so the client-side JS can find it reliably.
    # Pandas' to_html output can vary (sometimes includes a border attribute), so insert the id
    # into the first <table ...> tag if it's not already present.
    if 'id="elasticache"' not in table_html:
        table_html = table_html.replace("<table", '<table id="elasticache"', 1)
        # Add nicer table utility classes
        table_html = table_html.replace('class="dataframe table', 'class="dataframe table table-hover table-sm')

    # Precompute data for charts and filters
    engine_counts = df.groupby("EngineVersion").size().to_dict() if "EngineVersion" in df.columns else {}
    region_list = sorted(df["Region"].unique().tolist()) if "Region" in df.columns else []
    account_list = sorted(df["AccountId"].unique().astype(str).tolist()) if "AccountId" in df.columns else []
    resource_type_list = sorted(df["ResourceType"].unique().tolist()) if "ResourceType" in df.columns else []

    # Build team list from configured tags
    team_list = []
    for tag in config.tags:
        if tag in df.columns:
            # Convert all values to strings to handle mixed data types (ints, strings)
            tag_values = [str(val) for val in df[tag].unique().tolist() if pd.notna(val)]
            team_list.extend(tag_values)
    team_list = sorted(list(set(team_list)))

    # Engine groups (major version grouping)
    engine_groups = []
    if "EngineVersion" in df.columns:
        versions = df["EngineVersion"].dropna().unique()
        major_versions = set()
        for v in versions:
            try:
                major = str(v).split(".")[0]
                if major.isdigit():
                    major_versions.add(f"{major}.x")
            except (ValueError, IndexError, AttributeError):
                pass
        engine_groups = sorted(list(major_versions))

    # Summary metrics
    total_count = len(df)
    atrest_count = (
        len(df[df.get("AtRestEncryptionEnabled", pd.Series(dtype=bool))])
        if "AtRestEncryptionEnabled" in df.columns
        else 0
    )
    transit_count = (
        len(df[df.get("TransitEncryptionEnabled", pd.Series(dtype=bool))])
        if "TransitEncryptionEnabled" in df.columns
        else 0
    )
    region_count = len(region_list)
    profiles_count = len(profiles)

    chart_data = {
        "engine_counts": engine_counts,
        "region_list": region_list,
        "team_list": team_list,
        "engine_groups": engine_groups,
        "resource_type_list": resource_type_list,
        "account_list": account_list,
    }

    html_template = _get_html_template()

    # Replace placeholders
    html_content = html_template.replace("__TABLE_HTML__", table_html)
    html_content = html_content.replace("__CHART_DATA_PLACEHOLDER__", json.dumps(chart_data))
    html_content = html_content.replace("__TOTAL_COUNT__", str(total_count))
    html_content = html_content.replace("__ATREST_COUNT__", str(atrest_count))
    html_content = html_content.replace("__TRANSIT_COUNT__", str(transit_count))
    html_content = html_content.replace("__REGION_COUNT__", str(region_count))
    html_content = html_content.replace("__PROFILES_COUNT__", str(profiles_count))

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"Wrote HTML to {html_path}")


def _get_html_template() -> str:
    """Get the HTML template for the report."""
    return """<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>ElastiCache Report</title>
        <!-- Bootstrap CSS -->
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Prefer Amazon Ember if available, fall back to Noto Sans for similar metrics -->
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@300;400;700&display=swap" rel="stylesheet">
        <!-- DataTables CSS -->
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css">
        <style>
            /* CloudWatch-like theme and typography */
            :root{
                --aws-bg:#f6f7f8; --aws-surface:#ffffff; --aws-header:#232f3e;
                --aws-accent:#ff9900; --aws-muted:#6b7280; --card-radius:6px
            }
            /* typography: prefer Amazon Ember if installed, otherwise Noto Sans */
            body {
                background: var(--aws-bg);
                font-family: 'Amazon Ember', 'Noto Sans', 'Segoe UI', Roboto, Arial, system-ui;
                color:#0f1115; margin:0; -webkit-font-smoothing:antialiased;
            }
            .page-header {
                background: var(--aws-header); color: #ffffff; padding: 12px 18px;
                border-radius: 0; margin-bottom: 14px; display:flex;
                align-items:center; justify-content:space-between; height:64px;
            }
            .page-header h3 { font-weight:600; margin:0; font-size:1rem; letter-spacing: -0.2px; }
            .page-header .profiles { text-align:right; font-size:0.9rem; color:rgba(255,255,255,0.9); }
            .muted { color: var(--aws-muted); }
            .card {
                background: var(--aws-surface); border: 1px solid rgba(15,23,42,0.04);
                border-radius: var(--card-radius); box-shadow: 0 1px 2px rgba(15,23,42,0.04);
            }
            .metric-card { padding: 12px; display:flex; align-items:center; justify-content:space-between; }
            .metric-card .value { font-size:1.1rem; font-weight:700; color:#0f1115; }
            .metric-card .label { font-size:0.8rem; color:var(--aws-muted); }
            .dataTables_wrapper .dataTables_filter { float: right; text-align: right; }
            .table-wrapper { max-height: calc(100vh - 420px); overflow: auto; border-radius:6px; }
            .table-wrapper .table { width: 100% !important; table-layout: fixed; border-collapse: separate; }
            .table-wrapper th, .table-wrapper td { word-break: break-word; white-space: normal; padding: 10px; }
            .table thead th { background: #f0f2f4; color: #111827; border-bottom: 1px solid rgba(15,23,42,0.06); }
            .table tbody tr { background: #fff; }
            .table tbody tr:hover { background: #f7f8f9; }
            .btn-primary { background-color: var(--aws-accent); border-color: var(--aws-accent); color: #1b1b1b; }
            .btn-outline-secondary { border-color: rgba(15,23,42,0.08); color:#111827; background:transparent; }
            .select2-container--default .select2-selection--multiple { min-height: 38px; border-radius:4px; }
            .small-muted { font-size:0.85rem; color:var(--aws-muted); }
            /* Responsive spacing tweaks */
            @media (max-width: 768px){ .page-header { flex-direction:column; align-items:flex-start; gap:8px; } }
            /* Top nav bar (AWS console style) */
            .top-nav { background: var(--aws-header); color: #fff; height:48px; display:flex; align-items:center; padding: 6px 18px; }
            .top-nav .logo { display:flex; align-items:center; gap:12px; }
            .top-nav .logo svg { height:32px; }
            .top-nav .region { margin-left:12px; color:rgba(255,255,255,0.85); font-size:0.9rem; }
        </style>
    </head>
    <body>
        <!-- Top AWS-like nav -->
        <div class="top-nav">
            <div class="logo">
                <!-- logo removed to avoid remote asset loading -->
            </div>
            <div style="margin-left:18px; color:#fff; font-weight:600; font-size:1rem;">ElastiCache Inventory</div>
            <div class="ms-auto text-end" style="color:rgba(255,255,255,0.95);">
                <div class="small-muted">Profiles scanned</div>
                <div style="font-weight:700; font-size:1rem">__PROFILES_COUNT__</div>
            </div>
        </div>
        <div class="container-fluid p-4">

            <!-- Summary metrics -->
            <div class="row g-3 mb-3">
                <div class="col-sm-6 col-md-3">
                    <div class="card metric-card">
                        <div>
                            <div class="label">Total instances</div>
                            <div class="value">__TOTAL_COUNT__</div>
                        </div>
                        <div class="text-end muted">📊</div>
                    </div>
                </div>
                <div class="col-sm-6 col-md-3">
                    <div class="card metric-card">
                        <div>
                            <div class="label">At-rest encrypted</div>
                            <div class="value">__ATREST_COUNT__</div>
                        </div>
                        <div class="text-end muted">🔒</div>
                    </div>
                </div>
                <div class="col-sm-6 col-md-3">
                    <div class="card metric-card">
                        <div>
                            <div class="label">In-transit encrypted</div>
                            <div class="value">__TRANSIT_COUNT__</div>
                        </div>
                        <div class="text-end muted">🔐</div>
                    </div>
                </div>
                <div class="col-sm-6 col-md-3">
                    <div class="card metric-card">
                        <div>
                            <div class="label">Regions</div>
                            <div class="value">__REGION_COUNT__</div>
                        </div>
                        <div class="text-end muted">🌍</div>
                    </div>
                </div>
            </div>

            <!-- Filters -->
            <div class="card mb-3 p-3">
                <div class="row g-2 align-items-end">
                    <div class="col-md-2">
                        <label class="form-label">Region</label>
                        <select id="filter-region" class="form-select" multiple><option value="">All</option></select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Account</label>
                        <select id="filter-account" class="form-select" multiple><option value="">All</option></select>
                    </div>
                    <!-- Engine Version select removed; use Engine Groups for major-version filtering -->
                    <div class="col-md-2">
                        <label class="form-label">AtRest</label>
                        <select id="filter-atrest" class="form-select"><option value="">All</option><option value="True">True</option><option value="False">False</option></select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">InTransit</label>
                        <select id="filter-transit" class="form-select"><option value="">All</option><option value="True">True</option><option value="False">False</option></select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Resource Type</label>
                        <select id="filter-resource-type" class="form-select" multiple><option value="">All</option></select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Team</label>
                        <select id="filter-team" class="form-select" multiple><option value="">All</option></select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Resource Id</label>
                        <input id="filter-resource-id" class="form-control" placeholder="partial match (e.g., my-cache-)" />
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Engine Groups</label>
                        <select id="filter-engine-groups" class="form-select"><option value="">All</option></select>
                    </div>
                    <div class="col-md-1 text-end">
                        <button id="clear-filters" class="btn btn-sm btn-secondary">Clear</button>
                    </div>
                </div>
            </div>
            <!-- Columns toggle (show/hide) -->
            <div class="mb-3">
                <div class="btn-group">
                    <button class="btn btn-sm btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false">Columns</button>
                    <ul class="dropdown-menu p-3" id="columns-dropdown" style="max-height:300px; overflow:auto;">
                        <!-- populated by JS -->
                        <li class="mb-2"><button class="btn btn-sm btn-link" id="show-all-cols">Show all</button> <button class="btn btn-sm btn-link" id="hide-all-cols">Hide all</button></li>
                    </ul>
                </div>
                <button class="btn btn-sm btn-primary ms-2" id="export-filtered-csv">Export filtered CSV</button>
            </div>

            <!-- Tabs -->
            <ul class="nav nav-tabs mb-3" id="reportTabs" role="tablist">
                <li class="nav-item" role="presentation"><button class="nav-link active" id="list-tab" data-bs-toggle="tab" data-bs-target="#list" type="button" role="tab">List</button></li>
                <li class="nav-item" role="presentation"><button class="nav-link" id="charts-tab" data-bs-toggle="tab" data-bs-target="#charts" type="button" role="tab">Charts</button></li>
            </ul>

            <div class="tab-content">
                <div class="tab-pane fade show active" id="list" role="tabpanel">
                    <div class="card p-3"><div class="table-wrapper">__TABLE_HTML__</div></div>
                </div>
                <div class="tab-pane fade" id="charts" role="tabpanel">
                    <div class="row g-3">
                        <div class="col-12 col-lg-6">
                            <div class="card p-3 mb-3"><h6>Engine versions</h6><canvas id="engineChart" width="400" height="200"></canvas></div>
                        </div>
                        <div class="col-12 col-lg-6">
                            <div class="card p-3 mb-3"><h6>Encryption (At-rest / In-transit)</h6><canvas id="encChart" width="400" height="200"></canvas></div>
                        </div>
                        <div class="col-12 col-lg-6">
                            <div class="card p-3 mb-3"><h6>Regions</h6><canvas id="regionChart" width="400" height="200"></canvas></div>
                        </div>
                        <div class="col-12 col-lg-6">
                            <div class="card p-3 mb-3"><h6>Team</h6><canvas id="teamChart" width="400" height="200"></canvas></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
    <!-- Select2 for nice multi-selects -->
    <link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css" rel="stylesheet" />
    <script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <script>
            var __CHART_DATA__ = __CHART_DATA_PLACEHOLDER__;
            $(document).ready(function() {
                var table = $('#elasticache').DataTable({
                    orderCellsTop: true,
                    responsive: true,
                    autoWidth: false,
                    pageLength: 30,
                    lengthMenu: [ [30, 50, 100, -1], [30, 50, 100, "All"] ]
                });

                // Populate filter selects from table data (use toArray for compatibility)
                var headerMap = {};
                $('#elasticache thead tr').first().find('th').each(function(i){ headerMap[$(this).text().trim()] = i; });
                var regionIdx = headerMap['Region'];
                var accountIdx = headerMap['AccountId'];
                var engIdx = headerMap['EngineVersion'];
                var atrestIdx = headerMap['AtRestEncryptionEnabled'];
                var transitIdx = headerMap['TransitEncryptionEnabled'];
                var teamIdx = headerMap['Team'];
                var resTypeIdx = headerMap['ResourceType'];
                var resIdIdx = headerMap['ResourceId'];

                function populateFilters(){
                    // Prefer precomputed lists injected in __CHART_DATA__
                    try{
                        var cd = __CHART_DATA__;
                        if(cd.region_list && cd.region_list.length){ cd.region_list.forEach(function(v){ $('#filter-region').append($('<option>').val(v).text(v)); }); }
                        if(cd.account_list && cd.account_list.length){ cd.account_list.forEach(function(v){ $('#filter-account').append($('<option>').val(v).text(v)); }); }
                        // engine_list still available in injected data but Engine Version select removed
                        if(cd.team_list && cd.team_list.length){ cd.team_list.forEach(function(v){ $('#filter-team').append($('<option>').val(v).text(v)); }); }
                        if(cd.engine_groups && cd.engine_groups.length){ cd.engine_groups.forEach(function(v){ $('#filter-engine-groups').append($('<option>').val(v).text(v)); }); }
                        if(cd.resource_type_list && cd.resource_type_list.length){ cd.resource_type_list.forEach(function(v){ $('#filter-resource-type').append($('<option>').val(v).text(v)); }); }
                        return;
                    } catch(e){ /* fallback to table-derived lists below */ }

                    // guard empty mappings
                    if(regionIdx === undefined || engIdx === undefined || teamIdx === undefined) return;
                    var regionVals = table.column(regionIdx).data().unique().toArray().sort();
                    regionVals.forEach(function(v){ if(v!==null && v!==undefined && v!=='') { $('#filter-region').append($('<option>').val(v).text(v)); } });
                    var engVals = table.column(engIdx).data().unique().toArray().sort();
                    engVals.forEach(function(v){ if(v!==null && v!==undefined && v!=='') { $('#filter-engine').append($('<option>').val(v).text(v)); } });
                    var teamVals = table.column(teamIdx).data().unique().toArray().sort();
                    teamVals.forEach(function(v){ if(v!==null && v!==undefined && v!=='') { $('#filter-team').append($('<option>').val(v).text(v)); } });
                    if(resTypeIdx !== undefined){ var rtVals = table.column(resTypeIdx).data().unique().toArray().sort(); rtVals.forEach(function(v){ if(v!==null && v!==undefined && v!=='') { $('#filter-resource-type').append($('<option>').val(v).text(v)); } }); }
                    if(accountIdx !== undefined){ var acctVals = table.column(accountIdx).data().unique().toArray().sort(); acctVals.forEach(function(v){ if(v!==null && v!==undefined && v!=='') { $('#filter-account').append($('<option>').val(v).text(v)); } }); }
                }
                populateFilters();

                // Initialize Select2 on our multi-selects for a nicer UX
                $('#filter-region,#filter-team,#filter-resource-type,#filter-account').select2({width:'100%', placeholder: 'All', allowClear:true});
                // Engine groups is a single-select helper (not Select2)
                // If you want multi for groups you could change it similarly

                function applyFilters(){
                    // For multi-selects, build an OR regex like "^(a|b|c)$" to match any selected value
                    function buildRegex(vals){
                        if(!vals || vals.length===0) return '';
                        // If user selected the empty 'All' option (value==""), treat as no-filter
                        var cleaned = vals.filter(function(v){ return v !== null && v !== undefined && v !== ''; });
                        if(cleaned.length===0) return '';
                        var esc = cleaned.map(function(s){ return s.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&'); });
                        return '^(' + esc.join('|') + ')$';
                    }

                    var r = buildRegex($('#filter-region').val());
                    var eg = $('#filter-engine-groups').val() || '';
                    var e = '';
                    if(eg){
                        var m = eg.match(/^(\\d+)\\.x$/);
                        if(m){ e = '^(' + m[1] + '\\\\..*)$'; }
                    }

                    // Debug info for engine-group filtering
                    try{
                        console.debug('applyFilters: region=', r, 'engine_group=', eg, 'engine_regex=', e, 'atrest=', ar, 'transit=', tr, 'team=', t);
                    } catch(ex){}
                    var ar = $('#filter-atrest').val() || '';
                    var tr = $('#filter-transit').val() || '';
                    var t = buildRegex($('#filter-team').val());
                    var rt = buildRegex($('#filter-resource-type').val());
                    var aid = buildRegex($('#filter-account').val());
                    var rid = ($('#filter-resource-id').val() || '').trim();

                    table.column(regionIdx).search(r, true, false);
                    // Validate regex before applying to avoid silent failures
                    if(e){
                        try{
                            new RegExp(e);
                            table.column(engIdx).search(e, true, false);
                        } catch(rx){
                            console.warn('Invalid engine version regex', e, rx);
                            table.column(engIdx).search('', false, false);
                        }
                    } else {
                        table.column(engIdx).search('', false, false);
                    }
                    table.column(atrestIdx).search(ar);
                    table.column(transitIdx).search(tr);
                    table.column(teamIdx).search(t, true, false);
                    // Resource Type (multi-select)
                    if(resTypeIdx !== undefined){ table.column(resTypeIdx).search(rt, true, false); }
                    if(accountIdx !== undefined){ table.column(accountIdx).search(aid, true, false); }
                    // Resource Id (partial, case-insensitive). Use regex and caseInsensitive flag (4th arg)
                    if(resIdIdx !== undefined){
                        if(rid){
                            try{
                                // escape special regex chars and match substring
                                var esc = rid.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
                                var regex = esc; // we'll do substring match
                                table.column(resIdIdx).search(regex, true, false, true);
                            } catch(err){ console.warn('Invalid resource id regex', rid, err); table.column(resIdIdx).search('', false, false); }
                        } else {
                            table.column(resIdIdx).search('', false, false);
                        }
                    }
                    table.draw();
                    updateChartsFromFiltered();
                }

                // Wire change events, include engine groups so selecting a group applies filters
                $('#filter-region, #filter-engine-groups, #filter-atrest, #filter-transit, #filter-team, #filter-resource-type, #filter-account').on('change', applyFilters);
                $('#filter-resource-id').on('input', function(){ applyFilters(); });
                $('#clear-filters').on('click', function(){
                    $('#filter-region,#filter-engine-groups,#filter-atrest,#filter-transit,#filter-team,#filter-resource-type,#filter-account').val(null).trigger('change');
                    $('#filter-resource-id').val('');
                    applyFilters();
                });

                // Now create charts using injected JSON data
                try {
                    const chartData = __CHART_DATA__;
                    const engineCtx = document.getElementById('engineChart').getContext('2d');
                    const encCtx = document.getElementById('encChart').getContext('2d');
                    const regionCtx = document.getElementById('regionChart').getContext('2d');
                    const teamCtx = document.getElementById('teamChart').getContext('2d');
                    // nodeFamilyChart removed

                    var engineChart = new Chart(engineCtx, {type:'bar', data:{labels:[], datasets:[{label:'Instances', data:[], backgroundColor:'rgba(54,162,235,0.6)'}]}, options:{responsive:true, plugins:{legend:{display:false}}}});
                    var encChart = new Chart(encCtx, {type:'bar', data:{labels:['AtRest','InTransit'], datasets:[{label:'True', data:[0,0], backgroundColor:'rgba(75,192,192,0.6)'},{label:'False', data:[0,0], backgroundColor:'rgba(255,99,132,0.6)'}]}, options:{responsive:true}});
                    var regionChart = new Chart(regionCtx, {type:'pie', data:{labels:[], datasets:[{data:[], backgroundColor:[]}],}, options:{responsive:true}});
                    var teamChart = new Chart(teamCtx, {type:'bar', data:{labels:[], datasets:[{label:'Instances', data:[], backgroundColor:'rgba(153,102,255,0.6)'}]}, options:{indexAxis:'y', responsive:true}});
                    // nodeFamilyChart removed

                    function updateChartsFromFiltered(){
                        var visibleData = [];
                        table.rows({filter:'applied'}).every(function(){ visibleData.push(this.data()); });
                        var cols = [];
                        $('#elasticache thead tr').first().find('th').each(function(i){ cols.push($(this).text().trim()); });
                        var idxOf = (name)=>cols.indexOf(name);
                        var ev = idxOf('EngineVersion');
                        var r = idxOf('Region');
                        var ar = idxOf('AtRestEncryptionEnabled');
                        var trn = idxOf('TransitEncryptionEnabled');
                        var tm = idxOf('Team');

                        var engineMap = {};
                        var regionMap = {};
                        // nodeFamilyMap removed
                        var teamMap = {};
                        var atRestTrue=0, atRestFalse=0, transitTrue=0, transitFalse=0;

                        visibleData.forEach(function(row){
                            var engine = ev>=0 ? String(row[ev]) : 'unknown'; engineMap[engine] = (engineMap[engine]||0)+1;
                            var region = r>=0 ? String(row[r]) : 'unknown'; regionMap[region] = (regionMap[region]||0)+1;
                            var team = tm>=0 ? String(row[tm]) : 'not found'; teamMap[team] = (teamMap[team]||0)+1;
                            // NodeTypes handled elsewhere; node family chart removed
                            var a = ar>=0 ? String(row[ar]) : 'False'; if(a==='True' || a==='true' || a==='1') atRestTrue++; else atRestFalse++;
                            var t = trn>=0 ? String(row[trn]) : 'False'; if(t==='True' || t==='true' || t==='1') transitTrue++; else transitFalse++;
                        });

                        var engineLabels = Object.keys(engineMap).sort();
                        engineChart.data.labels = engineLabels;
                        engineChart.data.datasets[0].data = engineLabels.map(l=>engineMap[l]);
                        engineChart.update();

                        encChart.data.datasets[0].data = [atRestTrue, transitTrue];
                        encChart.data.datasets[1].data = [atRestFalse, transitFalse];
                        encChart.update();

                        var regionLabels = Object.keys(regionMap).sort();
                        regionChart.data.labels = regionLabels;
                        regionChart.data.datasets[0].data = regionLabels.map(l=>regionMap[l]);
                        regionChart.data.datasets[0].backgroundColor = regionLabels.map((_,i)=>`hsl(${(i*40)%360} 70% 50%)`);
                        regionChart.update();

                        var teamEntries = Object.entries(teamMap).sort((a,b)=>b[1]-a[1]).slice(0,10);
                        var teamLabels = teamEntries.map(e=>e[0]);
                        var teamValues = teamEntries.map(e=>e[1]);
                        teamChart.data.labels = teamLabels;
                        teamChart.data.datasets[0].data = teamValues;
                        teamChart.update();
                        // nodeFamilyChart update removed
                    }

                    // Update when switching to charts tab
                    var chartsTab = document.getElementById('charts-tab');
                    if(chartsTab){ chartsTab.addEventListener('shown.bs.tab', function(){ updateChartsFromFiltered(); }); }

                    // initialize charts from full dataset
                    updateChartsFromFiltered();
                } catch (err) {
                    console.warn('Failed to render charts', err);
                }

                // --- Columns toggle population ---
                (function(){
                    var cols = [];
                    $('#elasticache thead th').each(function(i){ cols.push({idx:i, name:$(this).text().trim()}); });
                    var dropdown = $('#columns-dropdown');
                    cols.forEach(function(c){
                        var id = 'colchk_' + c.idx;
                        var li = $('<li class="mb-1"></li>');
                        var html = `<div class="form-check"><input class="form-check-input col-toggle" type="checkbox" value="${c.idx}" id="${id}" checked> <label class="form-check-label" for="${id}">${c.name}</label></div>`;
                        li.html(html);
                        dropdown.append(li);
                    });

                    // toggle handlers
                    $('.col-toggle').on('change', function(){
                        var idx = parseInt($(this).val(),10);
                        var vis = $(this).is(':checked');
                        table.column(idx).visible(vis);
                    });

                    $('#show-all-cols').on('click', function(e){ e.preventDefault(); $('.col-toggle').prop('checked', true).trigger('change'); });
                    $('#hide-all-cols').on('click', function(e){ e.preventDefault(); $('.col-toggle').prop('checked', false).trigger('change'); });
                })();

                // Export filtered rows as CSV (only visible columns)
                $('#export-filtered-csv').on('click', function(){
                    try{
                        var visibleCols = [];
                        $('#elasticache thead th').each(function(i){ if(table.column(i).visible()){ visibleCols.push({idx:i, name:$(this).text().trim()}); } });
                        if(visibleCols.length===0){ alert('No visible columns to export'); return; }

                        var rows = [];
                        // Get filtered rows (apply: 'applied')
                        table.rows({filter:'applied'}).every(function(){ rows.push(this.data()); });

                        // Build CSV header
                        var header = visibleCols.map(function(c){ return '"' + c.name.replace(/"/g,'""') + '"'; }).join(',');
                        var csvLines = [header];

                        rows.forEach(function(r){
                            var vals = visibleCols.map(function(c){
                                var v = r[c.idx];
                                if(v===null || v===undefined) v='';
                                var s = String(v).replace(/"/g,'""');
                                return '"' + s + '"';
                            });
                            csvLines.push(vals.join(','));
                        });

                        var csvContent = csvLines.join('\\n');
                        var blob = new Blob([csvContent], {type: 'text/csv;charset=utf-8;'});
                        var url = URL.createObjectURL(blob);
                        var a = document.createElement('a');
                        a.href = url;
                        var filename = 'elasticache_filtered.csv';
                        a.download = filename;
                        document.body.appendChild(a);
                        a.click();
                        setTimeout(function(){ document.body.removeChild(a); URL.revokeObjectURL(url); }, 1000);
                    } catch(e){ console.error('Failed to export CSV', e); alert('Export failed: '+e); }
                });
            } );
        </script>
    </body>
</html>"""
