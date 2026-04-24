import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI, reportAPI, licenseAPI } from '../api';

const formatDate = (s) => {
  if (!s) return '—';
  const d = new Date(s.endsWith('Z') ? s : s + 'Z');
  return isNaN(d) ? s : d.toLocaleDateString();
};

const formatCurrency = (n) =>
  n != null ? `$${Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '—';

export default function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [vendorName, setVendorName] = useState('');

  const VENDORS = [
    'Microsoft (M365/Azure)',
    'Salesforce',
    'SAP',
    'Oracle',
    'Google Cloud',
    'AWS',
  ];

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const [userRes, reportsRes] = await Promise.all([
          authAPI.getCurrentUser(),
          reportAPI.listReports(),
        ]);
        setUser(userRes.data);
        setReports(reportsRes.data);
      } catch (err) {
        localStorage.removeItem('token');
        navigate('/login');
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const handleFileUpload = async (e) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;
    if (!vendorName) {
      alert('Please select a vendor before uploading.');
      e.target.value = '';
      return;
    }

    setUploading(true);
    try {
      const response = await reportAPI.upload(Array.from(fileList), vendorName.trim());
      setReports([response.data, ...reports]);
      e.target.value = '';
      setVendorName('');
    } catch (err) {
      alert('Upload failed: ' + (err.response?.data?.detail || 'Unknown error'));
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Navigation */}
      <nav className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-primary-600">SaaSCostCompare</h1>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm text-slate-600">{user?.full_name}</p>
              <p className="text-xs text-slate-500">{user?.email}</p>
            </div>
            <button onClick={handleLogout} className="btn-secondary text-sm">
              Logout
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Upload Section */}
        <div className="mb-8">
          <div className="card p-8">
            <div className="flex items-start justify-between mb-6">
              <h2 className="text-2xl font-bold text-slate-900">Upload SaaS Contract Data</h2>
              <a
                href="/saas_spend_template.csv"
                download="saas_spend_template.csv"
                className="flex items-center gap-2 text-sm font-medium text-primary-600 border border-primary-300 bg-primary-50 hover:bg-primary-100 px-4 py-2 rounded-lg transition"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download Template
              </a>
            </div>

            <div className="mb-5 p-4 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
              <p className="font-semibold mb-1">Supported formats</p>
              <p><strong>CSV:</strong> Use the template with columns: <span className="font-mono text-xs">vendor, product_name, sku, quantity, unit_price, total_cost, billing_frequency, currency</span>.</p>
              <p className="mt-1"><strong>PDF / Word:</strong> Upload contract documents, invoices, or pricing schedules (.pdf, .doc, .docx).</p>
              <p className="mt-1"><strong>ZIP:</strong> Bundle multiple CSV, PDF, and Word files into a single archive.</p>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Select Vendor
              </label>
              <div className="flex flex-wrap gap-2">
                {VENDORS.map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => setVendorName(v)}
                    className={`px-4 py-2 rounded-lg border text-sm font-medium transition ${
                      vendorName === v
                        ? 'bg-primary-600 text-white border-primary-600'
                        : 'bg-white text-slate-700 border-slate-300 hover:border-primary-400'
                    }`}
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>

            <div className={`border-2 border-dashed rounded-lg p-8 transition ${
              vendorName
                ? 'border-primary-300 bg-primary-50 hover:bg-primary-100 cursor-pointer'
                : 'border-slate-200 bg-slate-50 opacity-60 cursor-not-allowed'
            }`}>
              <label className={vendorName ? 'cursor-pointer block' : 'cursor-not-allowed block'}>
                <div className="text-center">
                  <svg className="mx-auto h-12 w-12 text-primary-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  <p className="text-lg font-medium text-slate-900">
                    {uploading
                      ? 'Uploading...'
                      : vendorName.trim()
                      ? `Click to upload your ${vendorName} contract data`
                      : 'Select a vendor above to upload'}
                  </p>
                  <p className="text-sm text-slate-600 mt-2">
                    CSV, PDF, Word, or ZIP &middot; Select one or multiple files &middot; Max 50MB total
                  </p>
                </div>
                <input
                  type="file"
                  accept=".csv,.pdf,.zip,.doc,.docx"
                  multiple
                  onChange={handleFileUpload}
                  disabled={uploading || !vendorName}
                  className="hidden"
                />
              </label>
            </div>
          </div>
        </div>

        {/* Current Licence Analysis Section */}
        <div className="mb-8">
          <LicenseAnalysisSection vendors={VENDORS} />
        </div>

        {/* Reports Section */}
        <div>
          <h2 className="text-2xl font-bold mb-6 text-slate-900">Your Uploads</h2>
          {reports.length === 0 ? (
            <div className="card p-12 text-center">
              <p className="text-slate-500 text-lg">No uploads yet. Upload a contract to get started!</p>
            </div>
          ) : (
            <div className="grid gap-6">
              {reports.map((report) => (
                <ReportCard key={report.id} report={report} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


function ReportCard({ report }) {
  const [status, setStatus] = useState(report);
  const [lineItems, setLineItems] = useState(null);
  const [showLineItems, setShowLineItems] = useState(false);
  const [comparison, setComparison] = useState(null);
  const [showComparison, setShowComparison] = useState(false);
  const [benchmark, setBenchmark] = useState(null);
  const [showBenchmark, setShowBenchmark] = useState(false);
  const [actionLoading, setActionLoading] = useState('');

  // Poll for status updates
  useEffect(() => {
    const FINAL = ['extracted', 'completed', 'failed', 'error'];
    if (FINAL.includes(status.status)) return;

    const check = async () => {
      try {
        const res = await reportAPI.getReportStatus(report.id);
        setStatus(res.data);
      } catch {}
    };

    const interval = setInterval(check, 3000);
    return () => clearInterval(interval);
  }, [report.id, status.status]);

  // Load existing benchmark on mount
  useEffect(() => {
    (async () => {
      try {
        const res = await reportAPI.getBenchmark(report.id);
        setBenchmark(res.data);
      } catch {}
    })();
  }, [report.id]);

  // Load comparison if status is completed
  useEffect(() => {
    if (status.status === 'completed') {
      (async () => {
        try {
          const res = await reportAPI.getComparison(report.id);
          setComparison(res.data);
        } catch {}
      })();
    }
  }, [report.id, status.status]);

  const handleViewLineItems = async () => {
    if (lineItems) {
      setShowLineItems(!showLineItems);
      return;
    }
    setActionLoading('lineItems');
    try {
      const res = await reportAPI.getLineItems(report.id);
      setLineItems(res.data);
      setShowLineItems(true);
    } catch (err) {
      alert('Failed to load line items: ' + (err.response?.data?.detail || 'Unknown error'));
    } finally {
      setActionLoading('');
    }
  };

  const handleRunComparison = async () => {
    setActionLoading('compare');
    try {
      const res = await reportAPI.runComparison(report.id);
      setComparison(res.data);
      setShowComparison(true);
      setStatus((prev) => ({ ...prev, status: 'completed' }));
    } catch (err) {
      alert('Comparison failed: ' + (err.response?.data?.detail || 'Unknown error'));
    } finally {
      setActionLoading('');
    }
  };

  const handleGenerateNarrative = async () => {
    setActionLoading('narrative');
    try {
      const res = await reportAPI.generateBenchmark(report.id);
      setBenchmark(res.data);
      setShowBenchmark(true);
    } catch (err) {
      alert('Report generation failed: ' + (err.response?.data?.detail || 'Unknown error'));
    } finally {
      setActionLoading('');
    }
  };

  const handleDownloadPDF = async () => {
    setActionLoading('download');
    try {
      const res = await reportAPI.downloadFullReport(report.id);
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `SaaSCostCompare_Report_${report.id}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Download failed: ' + (err.response?.data?.detail || 'Unknown error'));
    } finally {
      setActionLoading('');
    }
  };

  const statusBadge = () => {
    const map = {
      uploaded: { label: 'Uploaded', cls: 'bg-slate-100 text-slate-700' },
      extracting: { label: 'Extracting...', cls: 'bg-blue-100 text-blue-700' },
      extracted: { label: 'Extracted', cls: 'bg-green-100 text-green-800' },
      completed: { label: 'Compared', cls: 'bg-emerald-100 text-emerald-800' },
      failed: { label: 'Failed', cls: 'bg-red-100 text-red-800' },
    };
    const s = map[status.status] || { label: status.status, cls: 'bg-slate-100 text-slate-700' };
    return <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${s.cls}`}>{s.label}</span>;
  };

  const isExtracting = status.status === 'uploaded' || status.status === 'extracting';
  const isExtracted = status.status === 'extracted' || status.status === 'completed';
  const isCompared = status.status === 'completed';

  return (
    <div className="card p-6">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-bold text-slate-900">{report.filename}</h3>
          <div className="flex items-center gap-2 mt-1">
            {report.category && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                {report.category}
              </span>
            )}
            <span className="text-sm text-slate-500">{formatDate(report.created_at)}</span>
          </div>
        </div>
        {statusBadge()}
      </div>

      {/* Warnings */}
      {status.warnings && status.warnings.length > 0 && (
        <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="flex items-start gap-2">
            <svg className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <div>
              {status.warnings.map((w, i) => (
                <p key={i} className="text-sm text-amber-800">{w}</p>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Extraction in progress */}
      {isExtracting && (
        <div className="flex items-center gap-2 text-slate-600 p-4 bg-blue-50 rounded-lg">
          <div className="animate-spin w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full"></div>
          <span>Extracting contract data from your files...</span>
        </div>
      )}

      {/* Extraction summary */}
      {isExtracted && status.extraction_summary && (
        <div className="mb-4 p-3 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700">
          <span className="font-medium">{status.line_item_count || 0} line items extracted</span>
          {status.extraction_summary.file_summary && (
            <span className="text-slate-500 ml-2">({status.extraction_summary.file_summary})</span>
          )}
        </div>
      )}

      {/* Action Buttons */}
      {isExtracted && (
        <div className="flex flex-wrap gap-2 mb-2">
          {/* Step 1: Review Line Items */}
          <button
            onClick={handleViewLineItems}
            disabled={!!actionLoading}
            className="btn-secondary text-sm disabled:opacity-50"
          >
            {actionLoading === 'lineItems' ? 'Loading...' : showLineItems ? 'Hide Line Items' : 'Review Line Items'}
          </button>

          {/* Step 2: Run Comparison */}
          {!isCompared && (
            <button
              onClick={handleRunComparison}
              disabled={!!actionLoading}
              className="btn-primary text-sm disabled:opacity-50 flex items-center gap-2"
            >
              {actionLoading === 'compare' ? (
                <>
                  <div className="animate-spin w-3 h-3 border-2 border-white border-t-transparent rounded-full"></div>
                  Running Comparison...
                </>
              ) : 'Run Peer Comparison'}
            </button>
          )}

          {/* Step 3: Generate Narrative */}
          {isCompared && !benchmark && (
            <button
              onClick={handleGenerateNarrative}
              disabled={!!actionLoading}
              className="btn-primary text-sm disabled:opacity-50 flex items-center gap-2"
            >
              {actionLoading === 'narrative' ? (
                <>
                  <div className="animate-spin w-3 h-3 border-2 border-white border-t-transparent rounded-full"></div>
                  Generating Report...
                </>
              ) : 'Generate Benchmark Report'}
            </button>
          )}

          {/* View Comparison */}
          {isCompared && comparison && (
            <button
              onClick={() => setShowComparison(!showComparison)}
              disabled={!!actionLoading}
              className="btn-secondary text-sm disabled:opacity-50"
            >
              {showComparison ? 'Hide Comparison' : 'View Comparison'}
            </button>
          )}

          {/* View/Hide Benchmark */}
          {benchmark && (
            <button
              onClick={() => setShowBenchmark(!showBenchmark)}
              className="btn-secondary text-sm"
            >
              {showBenchmark ? 'Hide Report' : 'View Report'}
            </button>
          )}

          {/* Download PDF */}
          {benchmark && (
            <button
              onClick={handleDownloadPDF}
              disabled={!!actionLoading}
              className="btn-primary text-sm disabled:opacity-50"
            >
              {actionLoading === 'download' ? 'Downloading...' : 'Download PDF'}
            </button>
          )}
        </div>
      )}

      {/* Line Items Panel */}
      {showLineItems && lineItems && (
        <LineItemsPanel items={lineItems} />
      )}

      {/* Comparison Panel */}
      {showComparison && comparison && (
        <ComparisonPanel data={comparison} />
      )}

      {/* Benchmark Panel */}
      {showBenchmark && benchmark && (
        <BenchmarkPanel benchmark={benchmark} />
      )}
    </div>
  );
}


function LineItemsPanel({ items }) {
  if (!items || items.length === 0) {
    return (
      <div className="mt-4 p-4 bg-slate-50 rounded-lg text-sm text-slate-500">
        No line items extracted.
      </div>
    );
  }

  return (
    <div className="mt-4 border-t border-slate-200 pt-4">
      <h4 className="text-sm font-bold text-slate-900 mb-3">Extracted Line Items ({items.length})</h4>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 text-left">
              <th className="px-3 py-2 font-medium text-slate-600">Vendor</th>
              <th className="px-3 py-2 font-medium text-slate-600">Product</th>
              <th className="px-3 py-2 font-medium text-slate-600 text-right">Qty</th>
              <th className="px-3 py-2 font-medium text-slate-600 text-right">Unit Price</th>
              <th className="px-3 py-2 font-medium text-slate-600 text-right">Annual Cost</th>
              <th className="px-3 py-2 font-medium text-slate-600">Billing</th>
              <th className="px-3 py-2 font-medium text-slate-600">Source</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="px-3 py-2 font-medium text-slate-900">{item.vendor_name}</td>
                <td className="px-3 py-2 text-slate-700">{item.product_name}</td>
                <td className="px-3 py-2 text-right text-slate-700">{item.quantity}</td>
                <td className="px-3 py-2 text-right text-slate-700">{formatCurrency(item.unit_price)}</td>
                <td className="px-3 py-2 text-right font-medium text-slate-900">{formatCurrency(item.total_cost_annual)}</td>
                <td className="px-3 py-2 text-slate-500">{item.billing_frequency}</td>
                <td className="px-3 py-2">
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    item.extraction_source === 'csv' ? 'bg-green-50 text-green-700' :
                    item.extraction_source === 'pdf_ai' ? 'bg-purple-50 text-purple-700' :
                    item.extraction_source === 'pdf_vision' ? 'bg-indigo-50 text-indigo-700' :
                    'bg-slate-100 text-slate-600'
                  }`}>
                    {item.extraction_source === 'csv' ? 'CSV' :
                     item.extraction_source === 'pdf_ai' ? 'PDF' :
                     item.extraction_source === 'pdf_vision' ? 'PDF (Vision)' : item.extraction_source}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}


function ComparisonPanel({ data }) {
  const { items, summary } = data;
  if (!summary) return null;

  const assessmentColors = {
    well_below_market: 'bg-green-100 text-green-800',
    below_market: 'bg-emerald-100 text-emerald-800',
    at_market: 'bg-blue-100 text-blue-800',
    above_market: 'bg-red-100 text-red-800',
  };

  const assessmentLabels = {
    well_below_market: 'Well Below Market',
    below_market: 'Below Market',
    at_market: 'At Market',
    above_market: 'Above Market',
  };

  return (
    <div className="mt-4 border-t border-slate-200 pt-4">
      <h4 className="text-sm font-bold text-slate-900 mb-3">Peer Comparison Results</h4>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">Total Annual Spend</p>
          <p className="text-lg font-bold text-blue-700">{formatCurrency(summary.total_annual_spend)}</p>
        </div>
        <div className="bg-green-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">Potential Savings</p>
          <p className="text-lg font-bold text-green-700">{formatCurrency(summary.total_potential_savings)}</p>
        </div>
        <div className="bg-purple-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">Benchmarkable</p>
          <p className="text-lg font-bold text-purple-700">{summary.benchmarkable_items} / {summary.total_items}</p>
        </div>
        <div className="bg-amber-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">Data Coverage</p>
          <p className="text-lg font-bold text-amber-700">{summary.coverage_pct}%</p>
        </div>
      </div>

      {/* Assessment Breakdown */}
      {summary.assessment_breakdown && (
        <div className="flex flex-wrap gap-2 mb-4">
          {Object.entries(summary.assessment_breakdown).map(([key, count]) => (
            count > 0 && (
              <span key={key} className={`text-xs font-medium px-2.5 py-1 rounded-full ${assessmentColors[key]}`}>
                {assessmentLabels[key]}: {count}
              </span>
            )
          ))}
        </div>
      )}

      {/* Per-Item Results */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 text-left">
              <th className="px-3 py-2 font-medium text-slate-600">Vendor / Product</th>
              <th className="px-3 py-2 font-medium text-slate-600 text-right">Your Cost</th>
              <th className="px-3 py-2 font-medium text-slate-600 text-right">Peer Median</th>
              <th className="px-3 py-2 font-medium text-slate-600 text-right">Percentile</th>
              <th className="px-3 py-2 font-medium text-slate-600">Assessment</th>
              <th className="px-3 py-2 font-medium text-slate-600 text-right">Savings</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.line_item_id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="px-3 py-2">
                  <span className="font-medium text-slate-900">{item.vendor_name}</span>
                  <span className="text-slate-500 ml-1">{item.product_name}</span>
                </td>
                <td className="px-3 py-2 text-right text-slate-900">{formatCurrency(item.user_unit_cost_annual)}</td>
                <td className="px-3 py-2 text-right text-slate-700">
                  {item.has_sufficient_peers ? formatCurrency(item.peer_median) : '—'}
                </td>
                <td className="px-3 py-2 text-right text-slate-700">
                  {item.has_sufficient_peers ? `${item.user_percentile}%` : '—'}
                </td>
                <td className="px-3 py-2">
                  {item.has_sufficient_peers ? (
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${assessmentColors[item.assessment]}`}>
                      {assessmentLabels[item.assessment]}
                    </span>
                  ) : (
                    <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">
                      Insufficient Data ({item.peer_count} peers)
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-right font-medium">
                  {item.potential_annual_savings ? (
                    <span className="text-green-700">{formatCurrency(item.potential_annual_savings)}</span>
                  ) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}


function BenchmarkPanel({ benchmark }) {
  const renderMarkdown = (text) => {
    if (!text) return null;
    return text.split('\n').map((line, i) => {
      if (line.startsWith('## ')) {
        return <h3 key={i} className="text-base font-bold text-slate-900 mt-5 mb-2 border-b border-slate-200 pb-1">{line.slice(3)}</h3>;
      }
      if (line.startsWith('# ')) {
        return <h2 key={i} className="text-lg font-bold text-slate-900 mt-4 mb-2">{line.slice(2)}</h2>;
      }
      if (line.includes('|')) {
        if (/^[\s|:-]+$/.test(line)) return null;
        const cells = line.split('|').filter((c) => c.trim() !== '');
        if (cells.length === 0 || cells.every((c) => /^[-: ]+$/.test(c))) return null;
        return (
          <div key={i} className="flex gap-2 text-sm border-b border-slate-100 py-1">
            {cells.map((cell, j) => (
              <span key={j} className={`flex-1 ${j === 0 ? 'font-medium text-slate-700' : 'text-slate-600'}`}>
                {cell.trim()}
              </span>
            ))}
          </div>
        );
      }
      if (line.startsWith('- ') || line.startsWith('* ')) {
        return <li key={i} className="text-sm text-slate-700 ml-4 list-disc">{line.slice(2).replace(/\*\*(.*?)\*\*/g, '$1')}</li>;
      }
      if (/^\d+\. /.test(line)) {
        return <li key={i} className="text-sm text-slate-700 ml-4 list-decimal">{line.replace(/^\d+\. /, '').replace(/\*\*(.*?)\*\*/g, '$1')}</li>;
      }
      if (line.trim() === '') return <div key={i} className="h-1" />;
      return <p key={i} className="text-sm text-slate-700">{line.replace(/\*\*(.*?)\*\*/g, '$1')}</p>;
    });
  };

  return (
    <div className="mt-4 border-t border-slate-200 pt-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-bold text-slate-900">Benchmark Report</h4>
        {benchmark.generated_at && (
          <span className="text-xs text-slate-500">
            Generated {new Date(benchmark.generated_at).toLocaleString()}
          </span>
        )}
      </div>
      <div className="bg-slate-50 rounded-lg border border-slate-200 p-5 space-y-1 max-h-[600px] overflow-y-auto">
        {renderMarkdown(benchmark.narrative || benchmark.report)}
      </div>
    </div>
  );
}


// ── Current Licence Analysis ────────────────────────────────────────────────

const VENDOR_CREDENTIAL_FIELDS = {
  'Salesforce_jwt': [
    { key: 'login_url', label: 'Salesforce Instance URL', placeholder: 'https://yourorg.my.salesforce.com', type: 'text' },
    { key: 'client_id', label: 'Connected App Consumer Key', placeholder: 'From Setup → App Manager → Your App → View', type: 'text' },
    { key: 'username', label: 'Salesforce Username', placeholder: 'admin@yourcompany.com', type: 'text' },
    { key: 'private_key', label: 'Private Key (PEM)', placeholder: 'Paste your private key including BEGIN/END lines', type: 'textarea' },
  ],
  'Salesforce_password': [
    { key: 'login_url', label: 'Salesforce Instance URL', placeholder: 'https://yourorg.my.salesforce.com', type: 'text' },
    { key: 'client_id', label: 'Connected App Consumer Key', placeholder: 'From Setup → App Manager → Your App → View', type: 'text' },
    { key: 'client_secret', label: 'Consumer Secret', placeholder: 'Consumer secret from your Connected App', type: 'password' },
    { key: 'username', label: 'Salesforce Username', placeholder: 'admin@yourcompany.com', type: 'text' },
    { key: 'password', label: 'Password + Security Token', placeholder: 'Your password concatenated with security token', type: 'password' },
  ],
  'Microsoft (M365/Azure)': [
    { key: 'tenant_id', label: 'Tenant ID', placeholder: 'Azure AD Tenant ID', type: 'text' },
    { key: 'client_id', label: 'Application (Client) ID', placeholder: 'From Azure App Registration', type: 'text' },
    { key: 'client_secret', label: 'Client Secret', placeholder: 'Secret value', type: 'password' },
  ],
  'SAP_oauth': [
    { key: 'base_url', label: 'SAP S/4HANA System URL', placeholder: 'https://my-s4hana.s4hana.cloud.sap', type: 'text' },
    { key: 'token_url', label: 'OAuth Token URL', placeholder: 'https://my-s4hana.authentication.eu10.hana.ondemand.com/oauth/token', type: 'text' },
    { key: 'client_id', label: 'Client ID', placeholder: 'From Communication Arrangement', type: 'text' },
    { key: 'client_secret', label: 'Client Secret', placeholder: 'Client secret', type: 'password' },
  ],
  'SAP_basic': [
    { key: 'base_url', label: 'SAP S/4HANA System URL', placeholder: 'https://my-s4hana.s4hana.cloud.sap', type: 'text' },
    { key: 'username', label: 'Username', placeholder: 'SAP admin username', type: 'text' },
    { key: 'password', label: 'Password', placeholder: 'SAP password', type: 'password' },
  ],
  'Oracle': [
    { key: 'tenancy_ocid', label: 'Tenancy OCID', placeholder: 'ocid1.tenancy.oc1..aaaa...', type: 'text' },
    { key: 'user_ocid', label: 'User OCID', placeholder: 'ocid1.user.oc1..aaaa...', type: 'text' },
    { key: 'fingerprint', label: 'API Key Fingerprint', placeholder: 'aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99', type: 'text' },
    { key: 'private_key', label: 'Private Key (PEM)', placeholder: 'Paste your API signing key including BEGIN/END lines', type: 'textarea' },
    { key: 'region', label: 'Region', placeholder: 'us-ashburn-1', type: 'text' },
  ],
  'Google Cloud': [
    { key: 'service_account_key', label: 'Service Account Key (JSON)', placeholder: '{"type": "service_account", "project_id": "...", ...}', type: 'textarea' },
  ],
  'AWS': [
    { key: 'access_key_id', label: 'Access Key ID', placeholder: 'AKIA...', type: 'text' },
    { key: 'secret_access_key', label: 'Secret Access Key', placeholder: 'Your secret key', type: 'password' },
    { key: 'region', label: 'Region', placeholder: 'us-east-1', type: 'text' },
  ],
};

function JwtSetupGuide({ onKeyGenerated }) {
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);
  const [certPem, setCertPem] = useState('');

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await licenseAPI.generateCertificate();
      const { private_key, certificate } = res.data;
      onKeyGenerated(private_key);
      setCertPem(certificate);
      setGenerated(true);
    } catch (err) {
      alert('Failed to generate certificate: ' + (err.response?.data?.detail || 'Unknown error'));
    } finally {
      setGenerating(false);
    }
  };

  const downloadCert = () => {
    const blob = new Blob([certPem], { type: 'application/x-pem-file' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'SaaSCostCompare_certificate.crt';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mt-3 p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-sm">
      <p className="font-semibold text-emerald-900 mb-2">JWT Setup (one-time per Connected App)</p>

      {!generated ? (
        <>
          <ol className="list-decimal ml-4 space-y-1 text-emerald-800 mb-3">
            <li>Click <strong>Generate Certificate</strong> below</li>
            <li>Download the certificate file</li>
            <li>In Salesforce: <strong>Setup</strong> → <strong>App Manager</strong> → your Connected App → <strong>Edit</strong></li>
            <li>Check <strong>"Use Digital Signatures"</strong> and upload the certificate</li>
            <li>Fill in the remaining fields below and run the analysis</li>
          </ol>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-2"
          >
            {generating ? (
              <>
                <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                Generating...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                Generate Certificate
              </>
            )}
          </button>
        </>
      ) : (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-emerald-800">
            <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span className="font-medium">Certificate generated! Private key auto-filled below.</span>
          </div>
          <button
            onClick={downloadCert}
            className="bg-white text-emerald-700 border border-emerald-300 px-4 py-2 rounded-lg text-sm font-medium hover:bg-emerald-50 flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download Certificate (.crt) — upload this to Salesforce Connected App
          </button>
        </div>
      )}
    </div>
  );
}


function LicenseAnalysisSection({ vendors }) {
  const [expanded, setExpanded] = useState(false);
  const [selectedVendor, setSelectedVendor] = useState('');
  const [authMethod, setAuthMethod] = useState('jwt');
  const [credentials, setCredentials] = useState({});
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    if (expanded && history.length === 0) {
      licenseAPI.list().then(res => setHistory(res.data)).catch(() => {});
    }
  }, [expanded]);

  const handleAnalyze = async () => {
    if (!selectedVendor) return;
    setAnalyzing(true);
    setError('');
    setResult(null);

    try {
      const res = await licenseAPI.analyze(selectedVendor, credentials);
      setResult(res.data);
      setCredentials({});
      licenseAPI.list().then(r => setHistory(r.data)).catch(() => {});
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to connect. Please check your credentials.');
    } finally {
      setAnalyzing(false);
    }
  };

  const credKey = selectedVendor === 'Salesforce' ? `Salesforce_${authMethod}`
    : selectedVendor === 'SAP' ? `SAP_${authMethod}` : selectedVendor;
  const credFields = VENDOR_CREDENTIAL_FIELDS[credKey] || [];
  return (
    <div className="card">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-6 flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-3">
          <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Current Licence Analysis</h2>
            <p className="text-sm text-slate-500 mt-0.5">Connect to your vendor admin console to analyse licence utilisation</p>
          </div>
        </div>
        <svg className={`w-5 h-5 text-slate-400 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="px-6 pb-6 border-t border-slate-100 pt-4">
          {/* Vendor Selection */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-slate-700 mb-2">Select Vendor</label>
            <div className="flex flex-wrap gap-2">
              {vendors.map((v) => (
                <button
                  key={v}
                  onClick={() => { setSelectedVendor(v); setAuthMethod(v === 'SAP' ? 'oauth' : v === 'AWS' ? 'keys' : v === 'Google Cloud' ? 'sa' : v === 'Oracle' ? 'apikey' : 'jwt'); setCredentials({}); setResult(null); setError(''); }}
                  className={`px-4 py-2 rounded-lg border text-sm font-medium transition ${
                    selectedVendor === v
                      ? 'bg-primary-600 text-white border-primary-600'
                      : 'bg-white text-slate-700 border-slate-300 hover:border-primary-400'
                  }`}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>

          {/* Credential Fields */}
          {selectedVendor && (
            <div className="mt-4">
              <>
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800 mb-4">
                  <p className="font-semibold">How it works</p>
                    <p className="mt-1">
                      We connect to your {selectedVendor} admin API using the credentials below to pull licence counts, assignments, and usage data.
                      Credentials are used once for the API call and are <strong>never stored</strong>.
                    </p>
                  </div>

                  {/* Auth Method Toggle for Salesforce */}
                  {selectedVendor === 'Salesforce' && (
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-slate-700 mb-2">Authentication Method</label>
                      <div className="flex gap-2">
                        <button
                          onClick={() => { setAuthMethod('jwt'); setCredentials({}); }}
                          className={`px-4 py-2 rounded-lg border text-sm font-medium transition ${
                            authMethod === 'jwt'
                              ? 'bg-emerald-600 text-white border-emerald-600'
                              : 'bg-white text-slate-700 border-slate-300 hover:border-emerald-400'
                          }`}
                        >
                          JWT Bearer (Recommended)
                        </button>
                        <button
                          onClick={() => { setAuthMethod('password'); setCredentials({}); }}
                          className={`px-4 py-2 rounded-lg border text-sm font-medium transition ${
                            authMethod === 'password'
                              ? 'bg-emerald-600 text-white border-emerald-600'
                              : 'bg-white text-slate-700 border-slate-300 hover:border-emerald-400'
                          }`}
                        >
                          Username / Password
                        </button>
                      </div>

                      {/* JWT Setup Guide */}
                      {authMethod === 'jwt' && (
                        <JwtSetupGuide
                          onKeyGenerated={(privateKey) => setCredentials({ ...credentials, private_key: privateKey })}
                        />
                      )}
                    </div>
                  )}

                  {/* Auth Method Toggle for SAP */}
                  {selectedVendor === 'SAP' && (
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-slate-700 mb-2">Authentication Method</label>
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => { setAuthMethod('oauth'); setCredentials({}); }}
                          className={`px-4 py-2 rounded-lg border text-sm font-medium transition ${
                            authMethod === 'oauth'
                              ? 'bg-emerald-600 text-white border-emerald-600'
                              : 'bg-white text-slate-700 border-slate-300 hover:border-emerald-400'
                          }`}
                        >
                          OAuth 2.0 (Communication Arrangement)
                        </button>
                        <button
                          onClick={() => { setAuthMethod('basic'); setCredentials({}); }}
                          className={`px-4 py-2 rounded-lg border text-sm font-medium transition ${
                            authMethod === 'basic'
                              ? 'bg-emerald-600 text-white border-emerald-600'
                              : 'bg-white text-slate-700 border-slate-300 hover:border-emerald-400'
                          }`}
                        >
                          Basic Auth (Username / Password)
                        </button>
                        <button
                          onClick={() => { setAuthMethod('oauth'); setCredentials({ demo_mode: true }); }}
                          className="px-4 py-2 rounded-lg border text-sm font-medium transition bg-amber-50 text-amber-700 border-amber-300 hover:bg-amber-100"
                        >
                          Demo Mode (Sample Data)
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Auth Method Toggle for AWS */}
                  {selectedVendor === 'AWS' && (
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-slate-700 mb-2">Authentication Method</label>
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => { setAuthMethod('keys'); setCredentials({}); }}
                          className={`px-4 py-2 rounded-lg border text-sm font-medium transition ${
                            authMethod === 'keys' && !credentials.demo_mode
                              ? 'bg-emerald-600 text-white border-emerald-600'
                              : 'bg-white text-slate-700 border-slate-300 hover:border-emerald-400'
                          }`}
                        >
                          IAM Access Keys
                        </button>
                        <button
                          onClick={() => { setAuthMethod('keys'); setCredentials({ demo_mode: true }); }}
                          className="px-4 py-2 rounded-lg border text-sm font-medium transition bg-amber-50 text-amber-700 border-amber-300 hover:bg-amber-100"
                        >
                          Demo Mode (Sample Data)
                        </button>
                      </div>
                      {!credentials.demo_mode && (
                        <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800">
                          <p className="font-semibold mb-1">Required IAM Permissions</p>
                          <p>The access key needs: <span className="font-mono">ce:GetCostAndUsage</span>, <span className="font-mono">ce:GetReservationUtilization</span>, <span className="font-mono">ec2:DescribeInstances</span>, <span className="font-mono">ec2:DescribeVolumes</span>, <span className="font-mono">ec2:DescribeAddresses</span>, <span className="font-mono">iam:ListUsers</span>, <span className="font-mono">iam:ListAccessKeys</span>, <span className="font-mono">sts:GetCallerIdentity</span></p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Auth Method Toggle for Google Cloud */}
                  {selectedVendor === 'Google Cloud' && (
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-slate-700 mb-2">Authentication Method</label>
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => { setAuthMethod('sa'); setCredentials({}); }}
                          className={`px-4 py-2 rounded-lg border text-sm font-medium transition ${
                            authMethod === 'sa' && !credentials.demo_mode
                              ? 'bg-emerald-600 text-white border-emerald-600'
                              : 'bg-white text-slate-700 border-slate-300 hover:border-emerald-400'
                          }`}
                        >
                          Service Account Key
                        </button>
                        <button
                          onClick={() => { setAuthMethod('sa'); setCredentials({ demo_mode: true }); }}
                          className="px-4 py-2 rounded-lg border text-sm font-medium transition bg-amber-50 text-amber-700 border-amber-300 hover:bg-amber-100"
                        >
                          Demo Mode (Sample Data)
                        </button>
                      </div>
                      {!credentials.demo_mode && (
                        <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800">
                          <p className="font-semibold mb-1">Required Roles</p>
                          <p>The service account needs: <span className="font-mono">roles/compute.viewer</span>, <span className="font-mono">roles/iam.serviceAccountViewer</span>, <span className="font-mono">roles/billing.viewer</span></p>
                          <p className="mt-1">Create a key in <strong>IAM &amp; Admin</strong> → <strong>Service Accounts</strong> → your account → <strong>Keys</strong> → <strong>Add Key</strong> → <strong>JSON</strong></p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Auth Method Toggle for Oracle */}
                  {selectedVendor === 'Oracle' && (
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-slate-700 mb-2">Authentication Method</label>
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => { setAuthMethod('apikey'); setCredentials({}); }}
                          className={`px-4 py-2 rounded-lg border text-sm font-medium transition ${
                            authMethod === 'apikey' && !credentials.demo_mode
                              ? 'bg-emerald-600 text-white border-emerald-600'
                              : 'bg-white text-slate-700 border-slate-300 hover:border-emerald-400'
                          }`}
                        >
                          OCI API Key
                        </button>
                        <button
                          onClick={() => { setAuthMethod('apikey'); setCredentials({ demo_mode: true }); }}
                          className="px-4 py-2 rounded-lg border text-sm font-medium transition bg-amber-50 text-amber-700 border-amber-300 hover:bg-amber-100"
                        >
                          Demo Mode (Sample Data)
                        </button>
                      </div>
                      {!credentials.demo_mode && (
                        <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800">
                          <p className="font-semibold mb-1">Required OCI Policies</p>
                          <p>The user needs: <span className="font-mono">inspect instances</span>, <span className="font-mono">inspect volumes</span>, <span className="font-mono">inspect users</span>, <span className="font-mono">read usage-reports</span></p>
                          <p className="mt-1">Generate an API key in <strong>OCI Console</strong> → <strong>Profile</strong> → <strong>API Keys</strong> → <strong>Add API Key</strong></p>
                        </div>
                      )}
                    </div>
                  )}

                  {!credentials.demo_mode && (
                    <div className="space-y-3">
                      {credFields.map((field) => (
                        <div key={field.key}>
                          <label className="block text-sm font-medium text-slate-700 mb-1">{field.label}</label>
                          {field.type === 'textarea' ? (
                            <textarea
                              placeholder={field.placeholder}
                              value={credentials[field.key] || ''}
                              onChange={(e) => setCredentials({ ...credentials, [field.key]: e.target.value })}
                              rows={6}
                              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                            />
                          ) : (
                            <input
                              type={field.type}
                              placeholder={field.placeholder}
                              value={credentials[field.key] || ''}
                              onChange={(e) => setCredentials({ ...credentials, [field.key]: e.target.value })}
                              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                            />
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  <button
                    onClick={handleAnalyze}
                    disabled={analyzing || (!credentials.demo_mode && credFields.filter(f => !f.optional).some(f => !credentials[f.key]))}
                    className="mt-4 btn-primary text-sm disabled:opacity-50 flex items-center gap-2"
                  >
                    {analyzing ? (
                      <>
                        <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                        Connecting to {selectedVendor}...
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        Run Licence Analysis
                      </>
                    )}
                  </button>
              </>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
              {error}
            </div>
          )}

          {/* Results */}
          {result && (
            <LicenseResultPanel result={result} />
          )}

          {/* History */}
          {history.length > 0 && (
            <div className="mt-6 border-t border-slate-200 pt-4">
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="text-sm font-medium text-primary-600 hover:text-primary-700"
              >
                {showHistory ? 'Hide' : 'Show'} Previous Analyses ({history.length})
              </button>
              {showHistory && (
                <div className="mt-3 space-y-2">
                  {history.map((h) => (
                    <div key={h.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg text-sm">
                      <div>
                        <span className="font-medium text-slate-900">{h.vendor_name}</span>
                        <span className="text-slate-500 ml-2">{formatDate(h.created_at)}</span>
                      </div>
                      <button
                        onClick={() => setResult(h.result)}
                        className="text-primary-600 hover:text-primary-700 text-xs font-medium"
                      >
                        View Results
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


function LicenseResultPanel({ result }) {
  if (!result) return null;

  if (result.report_type === 'cloud_cost' && result.vendor === 'AWS') {
    return <AWSResultPanel result={result} />;
  }
  if (result.report_type === 'cloud_cost' && result.vendor === 'Google Cloud') {
    return <GCPResultPanel result={result} />;
  }
  if (result.report_type === 'cloud_cost' && result.vendor === 'Oracle') {
    return <OracleResultPanel result={result} />;
  }

  if (!result.licenses) return null;

  const licenses = result.licenses || [];
  const activity = result.login_activity || {};
  const totalLicenses = licenses.reduce((s, l) => s + (l.total_licenses || 0), 0);
  const totalUsed = licenses.reduce((s, l) => s + (l.assigned_licenses || 0), 0);
  const totalUnused = licenses.reduce((s, l) => s + (l.unused_licenses || 0), 0);
  const overallUtil = totalLicenses > 0 ? Math.round(totalUsed / totalLicenses * 100) : 0;

  return (
    <div className="mt-4 border-t border-slate-200 pt-4">
      <div className="flex items-center gap-2 mb-3">
        <h4 className="text-sm font-bold text-slate-900">
          {result.vendor} — Licence Utilisation Summary
        </h4>
        {result.demo_mode && (
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">Demo Data</span>
        )}
      </div>

      {result.note && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800 mb-4">
          {result.note}
        </div>
      )}

      {/* Summary Cards */}
      {licenses.length > 0 && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <div className="bg-blue-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Total Licences</p>
              <p className="text-lg font-bold text-blue-700">{totalLicenses.toLocaleString()}</p>
            </div>
            <div className="bg-green-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Assigned</p>
              <p className="text-lg font-bold text-green-700">{totalUsed.toLocaleString()}</p>
            </div>
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Unused</p>
              <p className="text-lg font-bold text-red-700">{totalUnused.toLocaleString()}</p>
            </div>
            <div className="bg-purple-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Utilisation</p>
              <p className={`text-lg font-bold ${overallUtil >= 80 ? 'text-green-700' : overallUtil >= 50 ? 'text-amber-700' : 'text-red-700'}`}>
                {overallUtil}%
              </p>
            </div>
          </div>

          {/* Login Activity */}
          {(activity.daily_avg_logins > 0 || activity.total_users > 0) && (
            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="bg-slate-50 rounded-lg p-3 text-center">
                <p className="text-xs text-slate-500 mb-1">Avg Daily Logins</p>
                <p className="text-lg font-bold text-slate-700">{(activity.daily_avg_logins || 0).toLocaleString()}</p>
              </div>
              <div className="bg-slate-50 rounded-lg p-3 text-center">
                <p className="text-xs text-slate-500 mb-1">Active Users (30d)</p>
                <p className="text-lg font-bold text-slate-700">{(activity.unique_users_30d || 0).toLocaleString()}</p>
              </div>
              <div className="bg-slate-50 rounded-lg p-3 text-center">
                <p className="text-xs text-slate-500 mb-1">Total Active Users</p>
                <p className="text-lg font-bold text-slate-700">{(activity.total_users || 0).toLocaleString()}</p>
              </div>
            </div>
          )}

          {/* Licence Breakdown Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 text-left">
                  <th className="px-3 py-2 font-medium text-slate-600">Product / Licence Type</th>
                  <th className="px-3 py-2 font-medium text-slate-600 text-right">Total</th>
                  <th className="px-3 py-2 font-medium text-slate-600 text-right">Assigned</th>
                  <th className="px-3 py-2 font-medium text-slate-600 text-right">Unused</th>
                  <th className="px-3 py-2 font-medium text-slate-600 text-right">Utilisation</th>
                </tr>
              </thead>
              <tbody>
                {licenses.map((lic, i) => (
                  <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-3 py-2 font-medium text-slate-900">{lic.product_name}</td>
                    <td className="px-3 py-2 text-right text-slate-700">{(lic.total_licenses || 0).toLocaleString()}</td>
                    <td className="px-3 py-2 text-right text-slate-700">{(lic.assigned_licenses || 0).toLocaleString()}</td>
                    <td className="px-3 py-2 text-right text-slate-700">{(lic.unused_licenses || 0).toLocaleString()}</td>
                    <td className="px-3 py-2 text-right">
                      <span className={`font-medium ${
                        lic.utilization_pct >= 80 ? 'text-green-700' :
                        lic.utilization_pct >= 50 ? 'text-amber-700' : 'text-red-700'
                      }`}>
                        {lic.utilization_pct}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {result.retrieved_at && (
        <p className="text-xs text-slate-400 mt-3 text-right">
          Data retrieved: {new Date(result.retrieved_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}


function AWSResultPanel({ result }) {
  const cost = result.cost_summary || {};
  const ri = result.reservations || {};
  const idle = result.idle_resources || {};
  const iam = result.iam_summary || {};
  const services = cost.top_services || [];

  return (
    <div className="mt-4 border-t border-slate-200 pt-4">
      <div className="flex items-center gap-2 mb-3">
        <h4 className="text-sm font-bold text-slate-900">AWS — Cloud Cost & Usage Analysis</h4>
        {result.demo_mode && (
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">Demo Data</span>
        )}
      </div>

      {/* Top-Level Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">Monthly Spend</p>
          <p className="text-lg font-bold text-blue-700">{formatCurrency(cost.total_monthly || 0)}</p>
        </div>
        <div className="bg-green-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">RI Utilisation</p>
          <p className={`text-lg font-bold ${ri.utilization_pct >= 80 ? 'text-green-700' : ri.utilization_pct >= 50 ? 'text-amber-700' : 'text-red-700'}`}>
            {ri.has_reservations ? `${ri.utilization_pct}%` : 'No RIs'}
          </p>
        </div>
        <div className="bg-red-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">Idle Resource Waste</p>
          <p className="text-lg font-bold text-red-700">{formatCurrency(idle.estimated_waste || 0)}/mo</p>
        </div>
        <div className="bg-purple-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">IAM Users</p>
          <p className="text-lg font-bold text-purple-700">{(iam.total_users || 0).toLocaleString()}</p>
        </div>
      </div>

      {/* Cost Breakdown by Service */}
      {services.length > 0 && (
        <div className="mb-4">
          <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">Cost Breakdown by Service</h5>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 text-left">
                  <th className="px-3 py-2 font-medium text-slate-600">Service</th>
                  <th className="px-3 py-2 font-medium text-slate-600 text-right">Monthly Avg</th>
                  <th className="px-3 py-2 font-medium text-slate-600 text-right">6-Month Total</th>
                  <th className="px-3 py-2 font-medium text-slate-600">6-Month Trend</th>
                </tr>
              </thead>
              <tbody>
                {services.map((svc, i) => (
                  <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-3 py-2 font-medium text-slate-900">{svc.service}</td>
                    <td className="px-3 py-2 text-right text-slate-700">{formatCurrency(svc.monthly_cost)}</td>
                    <td className="px-3 py-2 text-right text-slate-700">{formatCurrency(svc.total_6m)}</td>
                    <td className="px-3 py-2">
                      {svc.trend_6m && svc.trend_6m.length > 0 && <MiniTrend values={svc.trend_6m} />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Reserved Instances */}
      {ri.has_reservations && (
        <div className="mb-4">
          <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">Reserved Instance Utilisation</h5>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Utilisation</p>
              <p className={`text-lg font-bold ${ri.utilization_pct >= 80 ? 'text-green-700' : ri.utilization_pct >= 50 ? 'text-amber-700' : 'text-red-700'}`}>
                {ri.utilization_pct}%
              </p>
            </div>
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Purchased Hours</p>
              <p className="text-lg font-bold text-slate-700">{(ri.purchased_hours || 0).toLocaleString()}</p>
            </div>
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Used Hours</p>
              <p className="text-lg font-bold text-green-700">{(ri.used_hours || 0).toLocaleString()}</p>
            </div>
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Unused Hours</p>
              <p className="text-lg font-bold text-red-700">{(ri.unused_hours || 0).toLocaleString()}</p>
            </div>
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Net RI Savings</p>
              <p className="text-lg font-bold text-green-700">{formatCurrency(ri.net_savings || 0)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Idle Resources */}
      {(idle.ec2_stopped > 0 || idle.ebs_unattached > 0 || idle.eip_unassociated > 0) && (
        <div className="mb-4">
          <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">Idle Resources</h5>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Stopped EC2</p>
              <p className="text-lg font-bold text-red-700">{idle.ec2_stopped}</p>
            </div>
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Unattached EBS</p>
              <p className="text-lg font-bold text-red-700">{idle.ebs_unattached}</p>
            </div>
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Unused Elastic IPs</p>
              <p className="text-lg font-bold text-red-700">{idle.eip_unassociated}</p>
            </div>
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Est. Monthly Waste</p>
              <p className="text-lg font-bold text-red-700">{formatCurrency(idle.estimated_waste || 0)}</p>
            </div>
          </div>
        </div>
      )}

      {/* IAM Summary */}
      {iam.total_users > 0 && (
        <div className="mb-4">
          <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">IAM User Analysis</h5>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Total Users</p>
              <p className="text-lg font-bold text-slate-700">{iam.total_users}</p>
            </div>
            <div className="bg-green-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Active (90d)</p>
              <p className="text-lg font-bold text-green-700">{iam.active_users_90d || 0}</p>
            </div>
            <div className="bg-amber-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Inactive (90d)</p>
              <p className="text-lg font-bold text-amber-700">{iam.inactive_users_90d || 0}</p>
            </div>
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Never Logged In</p>
              <p className="text-lg font-bold text-red-700">{iam.never_logged_in || 0}</p>
            </div>
            <div className="bg-amber-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Old Access Keys</p>
              <p className="text-lg font-bold text-amber-700">{iam.old_access_keys || 0}</p>
            </div>
          </div>
        </div>
      )}

      {result.retrieved_at && (
        <p className="text-xs text-slate-400 mt-3 text-right">
          Data retrieved: {new Date(result.retrieved_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}


function GCPResultPanel({ result }) {
  const cost = result.cost_summary || {};
  const compute = result.compute || {};
  const diskWaste = result.disk_waste || {};
  const iam = result.iam_summary || {};
  const services = cost.top_services || [];

  return (
    <div className="mt-4 border-t border-slate-200 pt-4">
      <div className="flex items-center gap-2 mb-3">
        <h4 className="text-sm font-bold text-slate-900">Google Cloud — Infrastructure & Cost Analysis</h4>
        {result.demo_mode && (
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">Demo Data</span>
        )}
      </div>

      {/* Top-Level Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">Monthly Spend</p>
          <p className="text-lg font-bold text-blue-700">{formatCurrency(cost.total_monthly || 0)}</p>
        </div>
        <div className="bg-green-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">Compute Instances</p>
          <p className="text-lg font-bold text-green-700">{compute.running || 0} running</p>
        </div>
        <div className="bg-red-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">Disk Waste</p>
          <p className="text-lg font-bold text-red-700">{formatCurrency(diskWaste.estimated_waste || 0)}/mo</p>
        </div>
        <div className="bg-purple-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">Service Accounts</p>
          <p className="text-lg font-bold text-purple-700">{(iam.total_service_accounts || 0).toLocaleString()}</p>
        </div>
      </div>

      {/* Cost Breakdown by Service */}
      {services.length > 0 && (
        <div className="mb-4">
          <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">Cost Breakdown by Service</h5>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 text-left">
                  <th className="px-3 py-2 font-medium text-slate-600">Service</th>
                  <th className="px-3 py-2 font-medium text-slate-600 text-right">Monthly Avg</th>
                  <th className="px-3 py-2 font-medium text-slate-600 text-right">6-Month Total</th>
                  <th className="px-3 py-2 font-medium text-slate-600">6-Month Trend</th>
                </tr>
              </thead>
              <tbody>
                {services.map((svc, i) => (
                  <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-3 py-2 font-medium text-slate-900">{svc.service}</td>
                    <td className="px-3 py-2 text-right text-slate-700">{formatCurrency(svc.monthly_cost)}</td>
                    <td className="px-3 py-2 text-right text-slate-700">{formatCurrency(svc.total_6m)}</td>
                    <td className="px-3 py-2">
                      {svc.trend_6m && svc.trend_6m.length > 0 && <MiniTrend values={svc.trend_6m} />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Compute Engine Instances */}
      {compute.total_instances > 0 && (
        <div className="mb-4">
          <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">Compute Engine Instances</h5>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-3">
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Total Instances</p>
              <p className="text-lg font-bold text-slate-700">{compute.total_instances}</p>
            </div>
            <div className="bg-green-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Running</p>
              <p className="text-lg font-bold text-green-700">{compute.running}</p>
            </div>
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Stopped / Terminated</p>
              <p className="text-lg font-bold text-red-700">{compute.stopped}</p>
            </div>
          </div>
          {compute.machine_types && Object.keys(compute.machine_types).length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 text-left">
                    <th className="px-3 py-2 font-medium text-slate-600">Machine Type</th>
                    <th className="px-3 py-2 font-medium text-slate-600 text-right">Count</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(compute.machine_types).map(([mt, count]) => (
                    <tr key={mt} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-3 py-2 font-medium text-slate-900 font-mono text-xs">{mt}</td>
                      <td className="px-3 py-2 text-right text-slate-700">{count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Persistent Disk Analysis */}
      {(diskWaste.unattached_disks > 0 || diskWaste.total_disks > 0) && (
        <div className="mb-4">
          <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">Persistent Disk Analysis</h5>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Total Disks</p>
              <p className="text-lg font-bold text-slate-700">{diskWaste.total_disks}</p>
            </div>
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Unattached Disks</p>
              <p className="text-lg font-bold text-red-700">{diskWaste.unattached_disks}</p>
            </div>
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Unattached Size</p>
              <p className="text-lg font-bold text-red-700">{(diskWaste.unattached_size_gb || 0).toLocaleString()} GB</p>
            </div>
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Est. Monthly Waste</p>
              <p className="text-lg font-bold text-red-700">{formatCurrency(diskWaste.estimated_waste || 0)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Service Account Analysis */}
      {iam.total_service_accounts > 0 && (
        <div className="mb-4">
          <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">Service Account Analysis</h5>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Total SAs</p>
              <p className="text-lg font-bold text-slate-700">{iam.total_service_accounts}</p>
            </div>
            <div className="bg-green-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Active</p>
              <p className="text-lg font-bold text-green-700">{iam.active_service_accounts || 0}</p>
            </div>
            <div className="bg-amber-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Disabled</p>
              <p className="text-lg font-bold text-amber-700">{iam.disabled_service_accounts || 0}</p>
            </div>
            <div className="bg-amber-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Old SA Keys (&gt;90d)</p>
              <p className="text-lg font-bold text-amber-700">{iam.old_sa_keys || 0}</p>
            </div>
          </div>
        </div>
      )}

      {result.retrieved_at && (
        <p className="text-xs text-slate-400 mt-3 text-right">
          Data retrieved: {new Date(result.retrieved_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}


function OracleResultPanel({ result }) {
  const cost = result.cost_summary || {};
  const compute = result.compute || {};
  const storage = result.storage_waste || {};
  const iam = result.iam_summary || {};
  const services = cost.top_services || [];

  return (
    <div className="mt-4 border-t border-slate-200 pt-4">
      <div className="flex items-center gap-2 mb-3">
        <h4 className="text-sm font-bold text-slate-900">Oracle Cloud — Infrastructure & Cost Analysis</h4>
        {result.demo_mode && (
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">Demo Data</span>
        )}
      </div>

      {/* Top-Level Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">Monthly Spend</p>
          <p className="text-lg font-bold text-blue-700">{formatCurrency(cost.total_monthly || 0)}</p>
        </div>
        <div className="bg-green-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">Compute Instances</p>
          <p className="text-lg font-bold text-green-700">{compute.running || 0} running</p>
        </div>
        <div className="bg-red-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">Storage Waste</p>
          <p className="text-lg font-bold text-red-700">{formatCurrency(storage.estimated_waste || 0)}/mo</p>
        </div>
        <div className="bg-purple-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">IAM Users</p>
          <p className="text-lg font-bold text-purple-700">{(iam.total_users || 0).toLocaleString()}</p>
        </div>
      </div>

      {/* Cost Breakdown by Service */}
      {services.length > 0 && (
        <div className="mb-4">
          <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">Cost Breakdown by Service</h5>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 text-left">
                  <th className="px-3 py-2 font-medium text-slate-600">Service</th>
                  <th className="px-3 py-2 font-medium text-slate-600 text-right">Monthly Avg</th>
                  <th className="px-3 py-2 font-medium text-slate-600 text-right">6-Month Total</th>
                  <th className="px-3 py-2 font-medium text-slate-600">6-Month Trend</th>
                </tr>
              </thead>
              <tbody>
                {services.map((svc, i) => (
                  <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-3 py-2 font-medium text-slate-900">{svc.service}</td>
                    <td className="px-3 py-2 text-right text-slate-700">{formatCurrency(svc.monthly_cost)}</td>
                    <td className="px-3 py-2 text-right text-slate-700">{formatCurrency(svc.total_6m)}</td>
                    <td className="px-3 py-2">
                      {svc.trend_6m && svc.trend_6m.length > 0 && <MiniTrend values={svc.trend_6m} />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Compute Instances */}
      {compute.total_instances > 0 && (
        <div className="mb-4">
          <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">OCI Compute Instances</h5>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-3">
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Total Instances</p>
              <p className="text-lg font-bold text-slate-700">{compute.total_instances}</p>
            </div>
            <div className="bg-green-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Running</p>
              <p className="text-lg font-bold text-green-700">{compute.running}</p>
            </div>
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Stopped</p>
              <p className="text-lg font-bold text-red-700">{compute.stopped}</p>
            </div>
          </div>
          {compute.shapes && Object.keys(compute.shapes).length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 text-left">
                    <th className="px-3 py-2 font-medium text-slate-600">Shape</th>
                    <th className="px-3 py-2 font-medium text-slate-600 text-right">Count</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(compute.shapes).map(([shape, count]) => (
                    <tr key={shape} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-3 py-2 font-medium text-slate-900 font-mono text-xs">{shape}</td>
                      <td className="px-3 py-2 text-right text-slate-700">{count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Block Volume Analysis */}
      {(storage.unattached_volumes > 0 || storage.total_volumes > 0) && (
        <div className="mb-4">
          <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">Block Volume Analysis</h5>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Total Volumes</p>
              <p className="text-lg font-bold text-slate-700">{storage.total_volumes}</p>
            </div>
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Unattached</p>
              <p className="text-lg font-bold text-red-700">{storage.unattached_volumes}</p>
            </div>
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Unattached Size</p>
              <p className="text-lg font-bold text-red-700">{(storage.unattached_size_gb || 0).toLocaleString()} GB</p>
            </div>
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Est. Monthly Waste</p>
              <p className="text-lg font-bold text-red-700">{formatCurrency(storage.estimated_waste || 0)}</p>
            </div>
          </div>
        </div>
      )}

      {/* IAM User Analysis */}
      {iam.total_users > 0 && (
        <div className="mb-4">
          <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-2">IAM User Analysis</h5>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Total Users</p>
              <p className="text-lg font-bold text-slate-700">{iam.total_users}</p>
            </div>
            <div className="bg-green-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Active</p>
              <p className="text-lg font-bold text-green-700">{iam.active_users || 0}</p>
            </div>
            <div className="bg-amber-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Inactive</p>
              <p className="text-lg font-bold text-amber-700">{iam.inactive_users || 0}</p>
            </div>
            <div className="bg-amber-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">Old API Keys (&gt;90d)</p>
              <p className="text-lg font-bold text-amber-700">{iam.old_api_keys || 0}</p>
            </div>
            <div className="bg-slate-50 rounded-lg p-3 text-center">
              <p className="text-xs text-slate-500 mb-1">IAM Groups</p>
              <p className="text-lg font-bold text-slate-700">{iam.total_groups || 0}</p>
            </div>
          </div>
        </div>
      )}

      {result.retrieved_at && (
        <p className="text-xs text-slate-400 mt-3 text-right">
          Data retrieved: {new Date(result.retrieved_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}


function MiniTrend({ values }) {
  if (!values || values.length === 0) return null;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  const h = 24;
  const w = 80;
  const step = w / (values.length - 1 || 1);

  const points = values.map((v, i) => `${i * step},${h - ((v - min) / range) * (h - 4) - 2}`).join(' ');
  const trending = values[values.length - 1] > values[0];

  return (
    <svg width={w} height={h} className="inline-block">
      <polyline
        points={points}
        fill="none"
        stroke={trending ? '#ef4444' : '#22c55e'}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
