import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import CVViewer from '../components/CVViewer';
import { apiFetch, checkAuthStatus } from '../api/client';

function Dashboard() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('upload'); // upload, analyze, coverLetter
  const [cvUploaded, setCvUploaded] = useState(false);
  const [jobDescription, setJobDescription] = useState('');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [coverLetter, setCoverLetter] = useState('');
  const [loading, setLoading] = useState(false);
  const [authChecking, setAuthChecking] = useState(true);
  const [cvContent, setCvContent] = useState('');
  const [cvMetadata, setCvMetadata] = useState({ fileName: '', isPdf: false, fileType: '' });
  
  // Improved CV state
  const [improvedCvText, setImprovedCvText] = useState('');
  const [generatingImproved, setGeneratingImproved] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const fetchCvContent = async () => {
    try {
      const res = await apiFetch('/api/cv/content');
      if (res.ok) {
        const data = await res.json();
        setCvUploaded(true);
        setCvContent(data.content);
        setCvMetadata({
          fileName: data.file_name,
          isPdf: data.is_pdf,
          fileType: data.file_type
        });
      }
    } catch (err) {
      console.log("No existing CV found or error fetching.");
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const status = await checkAuthStatus();
      if (status.authenticated) {
        await fetchCvContent();
      } else {
        navigate('/login');
      }
      setAuthChecking(false);
    };

    initAuth();

    const handleUnauthorized = () => {
      navigate('/login');
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, [navigate]);

  if (authChecking) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh', color: 'var(--text-muted)' }}>
        <p>Loading session...</p>
      </div>
    );
  }

  const handleLogout = async () => {
    try {
      await apiFetch('/api/users/logout', { method: 'POST' });
    } catch (err) {
      console.error(err);
    }
    navigate('/login');
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setLoading(true);
    try {
      const res = await apiFetch('/api/cv/upload', {
        method: 'POST',
        body: formData,
      });
      if (res.ok) {
        await fetchCvContent();
        alert('CV Uploaded Successfully!');
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(errData.detail || 'Failed to upload CV.');
      }
    } catch (err) {
      console.error(err);
      alert('Network error');
    }
    setLoading(false);
  };

  const handleAnalyze = async () => {
    if (!jobDescription) {
      alert("Please provide a job description.");
      return;
    }
    setLoading(true);
    setImprovedCvText('');
    try {
      const res = await apiFetch('/api/cv/analyze', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ job_description: jobDescription }),
      });
      if (res.ok) {
        const data = await res.json();
        setAnalysisResult(data);
      } else {
        alert('Failed to analyze CV.');
      }
    } catch (err) {
      console.error(err);
      alert('Network error');
    }
    setLoading(false);
  };

  const handleGenerateImproved = async () => {
    if (!jobDescription) {
      alert("Please provide a job description.");
      return;
    }
    setGeneratingImproved(true);
    try {
      const res = await apiFetch('/api/cv/generate-improved', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          job_description: jobDescription,
          improvements: analysisResult ? analysisResult.improvements : ''
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setImprovedCvText(data.improved_text);
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(errData.detail || 'Failed to generate improved CV.');
      }
    } catch (err) {
      console.error(err);
      alert('Network error while generating improved CV.');
    }
    setGeneratingImproved(false);
  };

  const handleDownloadPdf = async () => {
    if (!jobDescription) {
      alert("Please provide a job description.");
      return;
    }
    setDownloadingPdf(true);
    try {
      const res = await apiFetch('/api/cv/download-improved', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          job_description: jobDescription,
          improvements: analysisResult ? analysisResult.improvements : ''
        }),
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'Improved_CV.pdf';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } else {
        alert('Failed to download PDF.');
      }
    } catch (err) {
      console.error(err);
      alert('Network error while downloading PDF.');
    }
    setDownloadingPdf(false);
  };

  const handleGenerateLetter = async () => {
    if (!jobDescription) {
      alert("Please provide a job description.");
      return;
    }
    setLoading(true);
    try {
      const res = await apiFetch('/api/cv/cover-letter', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ job_description: jobDescription }),
      });
      if (res.ok) {
        const data = await res.json();
        setCoverLetter(data.cover_letter);
      } else {
        alert('Failed to generate cover letter.');
      }
    } catch (err) {
      console.error(err);
      alert('Network error');
    }
    setLoading(false);
  };

  return (
    <div>
      <nav className="nav-bar">
        <div className="brand-header">
          <div className="brand-icon">✓</div>
          <h2 className="brand-title">CV Analyser</h2>
        </div>
        <div className="nav-links">
          <a href="#" className={activeTab === 'upload' ? 'active' : ''} onClick={(e) => { e.preventDefault(); setActiveTab('upload'); }}>Upload CV</a>
          <a href="#" className={activeTab === 'analyze' ? 'active' : ''} onClick={(e) => { e.preventDefault(); cvUploaded ? setActiveTab('analyze') : alert('Please upload a CV first.'); }}>Analyze CV</a>
          <a href="#" className={activeTab === 'coverLetter' ? 'active' : ''} onClick={(e) => { e.preventDefault(); cvUploaded ? setActiveTab('coverLetter') : alert('Please upload a CV first.'); }}>Cover Letter</a>
          <a href="#" className="nav-logout-btn" onClick={(e) => { e.preventDefault(); handleLogout(); }}>Logout</a>
        </div>
      </nav>

      <div className="glass-panel" style={{ minHeight: '60vh' }}>
        {activeTab === 'upload' && (
          <div>
            <h3 style={{ marginBottom: '1.25rem' }}>Upload your CV (.pdf, .txt, or .md)</h3>
            <div className="upload-area" onClick={() => document.getElementById('cv-upload').click()}>
              <div className="upload-icon-wrapper">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="17 8 12 3 7 8"></polyline>
                  <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
              </div>
              <p>Drag & Drop or Click to Upload (.pdf, .txt, .md)</p>
              <span>Supported formats: PDF, TXT, MD</span>
              <input 
                id="cv-upload" 
                type="file" 
                accept=".pdf,.txt,.md" 
                style={{ display: 'none' }} 
                onChange={handleUpload} 
              />
            </div>
            {loading && <p style={{ textAlign: 'center', marginTop: '1.5rem', color: 'var(--accent-primary)', fontWeight: '600' }}>Uploading...</p>}
            {cvUploaded && (
              <div style={{ marginTop: '2.5rem' }}>
                <p style={{ color: 'var(--accent-success)', textAlign: 'center', marginBottom: '1.25rem', fontWeight: '600' }}>
                  ✓ CV is uploaded and ready!
                </p>
                <div className="cv-display-card">
                  <div className="cv-display-header">
                    <h4 style={{ margin: 0 }}>Your Stored CV</h4>
                    {cvMetadata.fileName && (
                      <span className="cv-file-badge">{cvMetadata.fileName}</span>
                    )}
                  </div>
                  <CVViewer content={cvContent} />
                </div>
              </div>
            )}
          </div>
        )}

        {(activeTab === 'analyze' || activeTab === 'coverLetter') && (
          <div className="form-group">
            <label>Job Description</label>
            <textarea 
              rows="6" 
              value={jobDescription} 
              onChange={(e) => setJobDescription(e.target.value)} 
              placeholder="Paste the target job description here..."
            />
          </div>
        )}

        {activeTab === 'analyze' && (
          <div>
            <button className="btn" onClick={handleAnalyze} disabled={loading}>
              {loading ? 'Analyzing...' : 'Analyze CV'}
            </button>
            
            {analysisResult && (
              <div className="cv-display-card">
                <div className="score-display">
                  <div className="score-circle" style={{ '--score-deg': `${(analysisResult.score / 100) * 360}deg` }}>
                    <span className="score-value">{analysisResult.score}</span>
                  </div>
                  <div className="score-text-container">
                    <h3>Analysis Score</h3>
                    <p>Based on the provided job description</p>
                  </div>
                </div>
                <h4>Areas for Improvement</h4>
                <div className="content-box">
                  {analysisResult.improvements}
                </div>

                <div className="apply-prompt-card">
                  <h4 style={{ margin: 0, color: 'var(--text-main)' }}>Generate 1-Page Tailored CV</h4>
                  <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                    Generate an optimized, 1-page version of your CV with improvements applied. You can preview it below as HTML or download it as a PDF. Your uploaded CV in storage remains untouched.
                  </p>
                  <div className="apply-buttons">
                    <button className="btn" onClick={handleGenerateImproved} disabled={generatingImproved}>
                      {generatingImproved ? 'Generating 1-Page CV...' : 'Generate 1-Page CV Preview'}
                    </button>
                  </div>
                </div>

                {improvedCvText && (
                  <div style={{ marginTop: '2rem' }}>
                    <div className="cv-display-header">
                      <h4 style={{ margin: 0 }}>Generated 1-Page CV Preview (HTML)</h4>
                      <span className="cv-file-badge">1-Page HTML Preview</span>
                    </div>
                    <CVViewer content={improvedCvText} />
                    
                    <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginTop: '1.5rem' }}>
                      <button className="btn" onClick={handleDownloadPdf} disabled={downloadingPdf}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '0.4rem' }}>
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                          <polyline points="7 10 12 15 17 10"></polyline>
                          <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        {downloadingPdf ? 'Downloading PDF...' : 'Download Generated CV (PDF)'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'coverLetter' && (
          <div>
            <button className="btn" onClick={handleGenerateLetter} disabled={loading}>
              {loading ? 'Generating...' : 'Generate Cover Letter'}
            </button>

            {coverLetter && (
              <div className="result-card">
                <h4>Your Tailored Cover Letter</h4>
                <div className="content-box">
                  {coverLetter}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
