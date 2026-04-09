import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI, reportAPI } from '../api';

const formatDate = (s) => {
  if (!s) return '—';
  const d = new Date(s.endsWith('Z') ? s : s + 'Z');
  return isNaN(d) ? s : d.toLocaleDateString();
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('');

  const CATEGORIES = ['AWS', 'Microsoft', 'Google', 'Salesforce', 'Pega', 'SAP'];

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('payment') === 'success') {
      window.history.replaceState({}, '', '/dashboard');
    }

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
    if (!selectedCategory) {
      alert('Please select a category before uploading.');
      e.target.value = '';
      return;
    }

    setUploading(true);
    try {
      const response = await reportAPI.upload(Array.from(fileList), selectedCategory);
      setReports([response.data, ...reports]);
      e.target.value = '';
      setSelectedCategory('');
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
          <div>
            <h1 className="text-2xl font-bold text-primary-600">SaaSCostCompare</h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm text-slate-600">{user?.full_name}</p>
              <p className="text-xs text-slate-500">{user?.email}</p>
            </div>
            <button
              onClick={handleLogout}
              className="btn-secondary text-sm"
            >
              Logout
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Upload Section */}
        <div className="mb-8">
          <div className="card p-8">
            <div className="flex items-start justify-between mb-6">
              <h2 className="text-2xl font-bold text-slate-900">Upload SaaS Spend Data</h2>
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
              <p><strong>CSV:</strong> Use the standard template with columns: <span className="font-mono text-xs">vendor, product_name, sku, quantity, unit_price, total_cost, billing_frequency, currency</span>.</p>
              <p className="mt-1"><strong>PDF:</strong> Upload contract documents, invoices, or pricing schedules. You can select multiple PDFs at once.</p>
              <p className="mt-1"><strong>ZIP:</strong> Bundle multiple CSV and PDF files into a single ZIP archive.</p>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Select Vendor Category
              </label>
              <div className="flex flex-wrap gap-2">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-4 py-2 rounded-lg border text-sm font-medium transition ${
                      selectedCategory === cat
                        ? 'bg-primary-600 text-white border-primary-600'
                        : 'bg-white text-slate-700 border-slate-300 hover:border-primary-400'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            <div className={`border-2 border-dashed rounded-lg p-8 transition ${
              selectedCategory
                ? 'border-primary-300 bg-primary-50 hover:bg-primary-100 cursor-pointer'
                : 'border-slate-200 bg-slate-50 opacity-60 cursor-not-allowed'
            }`}>
              <label className={selectedCategory ? 'cursor-pointer block' : 'cursor-not-allowed block'}>
                <div className="text-center">
                  <svg
                    className="mx-auto h-12 w-12 text-primary-600 mb-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 4v16m8-8H4"
                    />
                  </svg>
                  <p className="text-lg font-medium text-slate-900">
                    {uploading
                      ? 'Uploading...'
                      : selectedCategory
                      ? `Click to upload your ${selectedCategory} spend data`
                      : 'Select a category above to upload'}
                  </p>
                  <p className="text-sm text-slate-600 mt-2">
                    CSV, PDF, or ZIP · Select one or multiple files · Max 50MB total
                  </p>
                </div>
                <input
                  type="file"
                  accept=".csv,.pdf,.zip"
                  multiple
                  onChange={handleFileUpload}
                  disabled={uploading || !selectedCategory}
                  className="hidden"
                />
              </label>
            </div>
          </div>
        </div>

        {/* Reports Section */}
        <div className="mb-10">
          <h2 className="text-2xl font-bold mb-6 text-slate-900">Your Reports</h2>

          {reports.length === 0 ? (
            <div className="card p-12 text-center">
              <p className="text-slate-500 text-lg">No reports yet. Upload one to get started!</p>
            </div>
          ) : (
            <div className="grid gap-6">
              {reports.map((report) => (
                <ReportCard key={report.id} report={report} />
              ))}
            </div>
          )}
        </div>

        {/* Downloaded Reports Section */}
        <DownloadedReports reports={reports} />
      </div>
    </div>
  );
}

function DownloadedReports({ reports }) {
  const downloaded = reports.filter((r) => r.payment_status === 'completed');
  const [downloading, setDownloading] = useState({});
  const [benchmarks, setBenchmarks] = useState({});
  const [expanded, setExpanded] = useState({});

  useEffect(() => {
    downloaded.forEach(async (report) => {
      try {
        const res = await reportAPI.getBenchmark(report.id);
        setBenchmarks((prev) => ({ ...prev, [report.id]: res.data }));
      } catch {
        // no benchmark yet
      }
    });
  }, [reports]);

  const handleDownload = async (report) => {
    setDownloading((prev) => ({ ...prev, [report.id]: true }));
    try {
      const res = await reportAPI.download(report.id);
      const url = window.URL.createObjectURL(res.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = report.filename || `report-${report.id}.csv`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Download failed: ' + (err.response?.data?.detail || 'Unknown error'));
    } finally {
      setDownloading((prev) => ({ ...prev, [report.id]: false }));
    }
  };

  const toggleExpand = (id) => setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));

  if (downloaded.length === 0) return null;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6 text-slate-900">Downloaded Reports</h2>
      <div className="grid gap-4">
        {downloaded.map((report) => {
          const bm = benchmarks[report.id];
          const isExpanded = expanded[report.id];
          return (
            <div key={report.id} className="card p-6">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-base font-bold text-slate-900">{report.filename}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    {report.category && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                        {report.category}
                      </span>
                    )}
                    <span className="text-xs text-slate-500">
                      {formatDate(report.created_at)}
                    </span>
                    <span className="badge badge-success">Paid</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleDownload(report)}
                    disabled={downloading[report.id]}
                    className="btn-primary text-sm disabled:opacity-50"
                  >
                    {downloading[report.id] ? 'Downloading...' : 'Re-download'}
                  </button>
                  {bm && (
                    <button
                      onClick={() => toggleExpand(report.id)}
                      className="btn-secondary text-sm"
                    >
                      {isExpanded ? 'Hide Analysis' : 'View Analysis'}
                    </button>
                  )}
                </div>
              </div>

              {isExpanded && bm && (
                <div className="mt-5 border-t border-slate-200 pt-5">
                  <div className="grid grid-cols-3 gap-3 mb-4">
                    <div className="bg-blue-50 rounded-lg p-3 text-center">
                      <p className="text-xs text-slate-500 mb-1">Total SaaS Spend</p>
                      <p className="text-lg font-bold text-blue-700">
                        {bm.total_spend != null ? `$${Number(bm.total_spend).toLocaleString()}` : '—'}
                      </p>
                    </div>
                    <div className="bg-purple-50 rounded-lg p-3 text-center">
                      <p className="text-xs text-slate-500 mb-1">Per Employee</p>
                      <p className="text-lg font-bold text-purple-700">
                        {bm.spend_per_employee != null ? `$${Number(bm.spend_per_employee).toLocaleString()}` : '—'}
                      </p>
                    </div>
                    <div className="bg-green-50 rounded-lg p-3 text-center">
                      <p className="text-xs text-slate-500 mb-1">% of Revenue</p>
                      <p className="text-lg font-bold text-green-700">
                        {bm.spend_pct_revenue != null ? `${Number(bm.spend_pct_revenue).toFixed(1)}%` : '—'}
                      </p>
                    </div>
                  </div>
                  {bm.report && (
                    <div className="bg-slate-50 rounded-lg border border-slate-200 p-4 max-h-96 overflow-y-auto">
                      <pre className="text-sm text-slate-700 whitespace-pre-wrap font-sans">{bm.report}</pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ReportCard({ report }) {
  const [status, setStatus] = useState(report);
  const [loading, setLoading] = useState(false);
  const [benchmarking, setBenchmarking] = useState(false);
  const [benchmark, setBenchmark] = useState(null);
  const [showBenchmark, setShowBenchmark] = useState(false);

  useEffect(() => {
    const FINAL_STATUSES = ['completed', 'failed', 'error'];
    if (FINAL_STATUSES.includes(status.status)) return;

    const checkStatus = async () => {
      try {
        const response = await reportAPI.getReportStatus(report.id);
        setStatus(response.data);
      } catch (err) {
        console.error('Failed to fetch status');
      }
    };

    const interval = setInterval(checkStatus, 3000);
    return () => clearInterval(interval);
  }, [report.id, status.status]);

  // Load existing benchmark on mount
  useEffect(() => {
    const fetchBenchmark = async () => {
      try {
        const response = await reportAPI.getBenchmark(report.id);
        setBenchmark(response.data);
      } catch {
        // No benchmark yet — that's fine
      }
    };
    fetchBenchmark();
  }, [report.id]);

  const handlePay = async () => {
    setLoading(true);
    try {
      const res = await reportAPI.createPaymentSession(report.id, 9999);
      window.location.href = res.data.url;
    } catch (err) {
      alert('Payment failed: ' + (err.response?.data?.detail || 'Unknown error'));
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    setLoading(true);
    try {
      const res = await reportAPI.downloadFullReport(report.id);
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `SaaSCostCompare_Report_${report.filename?.replace(/\.[^.]+$/, '') || report.id}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Download failed: ' + (err.response?.data?.detail || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateBenchmark = async () => {
    setBenchmarking(true);
    try {
      const response = await reportAPI.generateBenchmark(report.id);
      setBenchmark(response.data);
      setShowBenchmark(true);
    } catch (err) {
      alert('Benchmark generation failed: ' + (err.response?.data?.detail || 'Unknown error'));
    } finally {
      setBenchmarking(false);
    }
  };

  return (
    <div className="card p-6">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-bold text-slate-900">{report.filename}</h3>
          <div className="flex items-center gap-2 mt-1">
            {report.category && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                {report.category}
              </span>
            )}
            <p className="text-sm text-slate-500">
              {formatDate(report.created_at)}
            </p>
          </div>
        </div>
        {status.status === 'processing' && (
          <span className="badge badge-pending">Processing</span>
        )}
        {status.status === 'failed' && (
          <span className="badge badge-error">Failed</span>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {status.status === 'processing' && (
          <div className="flex-1 flex items-center justify-center gap-2 text-slate-600">
            <div className="animate-spin w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full"></div>
            <span>Analyzing with AI...</span>
          </div>
        )}
        {status.status === 'completed' && !benchmark && (
          <button
            onClick={handleGenerateBenchmark}
            disabled={benchmarking}
            className="btn-primary flex-1 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {benchmarking ? (
              <>
                <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                Generating Benchmark...
              </>
            ) : (
              'Generate Benchmark Report'
            )}
          </button>
        )}
        {status.status === 'completed' && benchmark && (
          <>
            <button
              onClick={handleDownload}
              disabled={loading}
              className="btn-primary flex-1 disabled:opacity-50"
            >
              {loading ? 'Downloading...' : 'Download PDF Report'}
            </button>
            <button
              onClick={() => setShowBenchmark(!showBenchmark)}
              className="btn-secondary disabled:opacity-50 flex items-center gap-2"
            >
              {showBenchmark ? 'Hide Benchmark' : 'View Benchmark'}
            </button>
          </>
        )}
      </div>

      {showBenchmark && benchmark && (
        <BenchmarkPanel benchmark={benchmark} />
      )}
    </div>
  );
}

function BenchmarkPanel({ benchmark }) {
  const formatCurrency = (n) =>
    n != null ? `$${Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '—';
  const formatPct = (n) => (n != null ? `${Number(n).toFixed(1)}%` : '—');

  // Render markdown-like text: headings, bold, tables as readable HTML
  const renderMarkdown = (text) => {
    if (!text) return null;
    return text.split('\n').map((line, i) => {
      if (line.startsWith('## ')) {
        return (
          <h3 key={i} className="text-base font-bold text-slate-900 mt-5 mb-2 border-b border-slate-200 pb-1">
            {line.slice(3)}
          </h3>
        );
      }
      if (line.startsWith('# ')) {
        return (
          <h2 key={i} className="text-lg font-bold text-slate-900 mt-4 mb-2">
            {line.slice(2)}
          </h2>
        );
      }
      if (line.includes('|')) {
        // Skip separator lines like |---|---|---|
        if (/^[\s|:-]+$/.test(line)) return null;
        // Table row — render as a styled div
        const cells = line.split('|').filter((c) => c.trim() !== '');
        if (cells.length === 0) return null;
        const isSeparator = cells.every((c) => /^[-: ]+$/.test(c));
        if (isSeparator) return null;
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
        return (
          <li key={i} className="text-sm text-slate-700 ml-4 list-disc">
            {line.slice(2).replace(/\*\*(.*?)\*\*/g, '$1')}
          </li>
        );
      }
      if (/^\d+\. /.test(line)) {
        return (
          <li key={i} className="text-sm text-slate-700 ml-4 list-decimal">
            {line.replace(/^\d+\. /, '').replace(/\*\*(.*?)\*\*/g, '$1')}
          </li>
        );
      }
      if (line.trim() === '') return <div key={i} className="h-1" />;
      return (
        <p key={i} className="text-sm text-slate-700">
          {line.replace(/\*\*(.*?)\*\*/g, '$1')}
        </p>
      );
    });
  };

  return (
    <div className="mt-6 border-t border-slate-200 pt-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-base font-bold text-slate-900">Benchmarking Report</h4>
          <p className="text-xs text-slate-500 mt-0.5">
            Based on {benchmark.peer_count > 0 ? `${benchmark.peer_count} peer organization(s) + ` : ''}AI industry knowledge
            {benchmark.generated_at && ` · Generated ${new Date(benchmark.generated_at).toLocaleString()}`}
          </p>
        </div>
      </div>

      {/* Key metrics strip */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">Total SaaS Spend</p>
          <p className="text-lg font-bold text-blue-700">{formatCurrency(benchmark.total_spend)}</p>
        </div>
        <div className="bg-purple-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">Per Employee</p>
          <p className="text-lg font-bold text-purple-700">{formatCurrency(benchmark.spend_per_employee)}</p>
        </div>
        <div className="bg-green-50 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">% of Revenue</p>
          <p className="text-lg font-bold text-green-700">{formatPct(benchmark.spend_pct_revenue)}</p>
        </div>
      </div>

      {/* Full report */}
      <div className="bg-slate-50 rounded-lg border border-slate-200 p-5 space-y-1 max-h-[600px] overflow-y-auto">
        {renderMarkdown(benchmark.report)}
      </div>
    </div>
  );
}
