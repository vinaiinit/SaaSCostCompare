import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI, reportAPI } from '../api';

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
    if (!vendorName.trim()) {
      alert('Please enter a vendor name before uploading.');
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
              <p className="mt-1"><strong>PDF:</strong> Upload contract documents, invoices, or pricing schedules.</p>
              <p className="mt-1"><strong>ZIP:</strong> Bundle multiple CSV and PDF files into a single archive.</p>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Vendor Name
              </label>
              <input
                type="text"
                value={vendorName}
                onChange={(e) => setVendorName(e.target.value)}
                placeholder="e.g. Salesforce, AWS, Microsoft, Datadog..."
                className="input-field max-w-md"
              />
            </div>

            <div className={`border-2 border-dashed rounded-lg p-8 transition ${
              vendorName.trim()
                ? 'border-primary-300 bg-primary-50 hover:bg-primary-100 cursor-pointer'
                : 'border-slate-200 bg-slate-50 opacity-60 cursor-not-allowed'
            }`}>
              <label className={vendorName.trim() ? 'cursor-pointer block' : 'cursor-not-allowed block'}>
                <div className="text-center">
                  <svg className="mx-auto h-12 w-12 text-primary-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  <p className="text-lg font-medium text-slate-900">
                    {uploading
                      ? 'Uploading...'
                      : vendorName.trim()
                      ? `Click to upload your ${vendorName.trim()} contract data`
                      : 'Enter a vendor name above to upload'}
                  </p>
                  <p className="text-sm text-slate-600 mt-2">
                    CSV, PDF, or ZIP &middot; Select one or multiple files &middot; Max 50MB total
                  </p>
                </div>
                <input
                  type="file"
                  accept=".csv,.pdf,.zip"
                  multiple
                  onChange={handleFileUpload}
                  disabled={uploading || !vendorName.trim()}
                  className="hidden"
                />
              </label>
            </div>
          </div>
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
                    'bg-slate-100 text-slate-600'
                  }`}>
                    {item.extraction_source === 'csv' ? 'CSV' :
                     item.extraction_source === 'pdf_ai' ? 'PDF' : item.extraction_source}
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
