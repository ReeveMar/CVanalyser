import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import PDFViewer from '../components/PDFViewer';
import { apiFetch, checkAuthStatus } from '../api/client';

function Dashboard() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('upload'); // upload, analyze, coverLetter
  const [cvUploaded, setCvUploaded] = useState(false);
  const [jobDescription, setJobDescription] = useState('');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [authChecking, setAuthChecking] = useState(true);
  const [cvMetadata, setCvMetadata] = useState({ fileName: '', isPdf: false, fileType: '' });
  
  // PDF Viewer states
  const [cvPdfUrl, setCvPdfUrl] = useState(null);
  const [loadingCvPdf, setLoadingCvPdf] = useState(false);
  
  const [improvedCvPdfUrl, setImprovedCvPdfUrl] = useState(null);
  const [generatingImproved, setGeneratingImproved] = useState(false);
  
  const [coverLetterPdfUrl, setCoverLetterPdfUrl] = useState(null);
  const [generatingCoverLetter, setGeneratingCoverLetter] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const fetchCvPdf = async () => {
    setLoadingCvPdf(true);
    try {
      const res = await apiFetch(`/api/cv/pdf?t=${Date.now()}`, {
        cache: 'no-store'
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        setCvPdfUrl((prevUrl) => {
          if (prevUrl) URL.revokeObjectURL(prevUrl);
          return url;
        });
      }
    } catch (err) {
      console.error("Error fetching CV PDF:", err);
    }
    setLoadingCvPdf(false);
  };

  const fetchCvContent = async () => {
    try {
      const res = await apiFetch(`/api/cv/content?t=${Date.now()}`, {
        cache: 'no-store'
      });
      if (res.ok) {
        const data = await res.json();
        setCvUploaded(true);
        setCvMetadata({
          fileName: data.file_name,
          isPdf: data.is_pdf,
          fileType: data.file_type
        });
        await fetchCvPdf();
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

  const uploadFile = async (file) => {
    if (!file) return;

    const validExtensions = ['.pdf', '.txt', '.md'];
    const fileName = file.name.toLowerCase();
    const isValid = validExtensions.some(ext => fileName.endsWith(ext));
    if (!isValid) {
      alert("Only .pdf, .txt, and .md files are allowed.");
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    setLoading(true);
    try {
      const res = await apiFetch('/api/cv/upload', {
        method: 'POST',
        body: formData,
      });
      if (res.ok) {
        // Reset downstream results so they don't reflect previous CV version
        setAnalysisResult(null);
        setImprovedCvPdfUrl(null);
        setCoverLetterPdfUrl(null);

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

  const handleUpload = async (e) => {
    const file = e.target.files && e.target.files[0];
    // Reset input value immediately so selecting the exact same file name again triggers onChange
    e.target.value = '';
    if (file) {
      await uploadFile(file);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) {
      await uploadFile(file);
    }
  };

  const handleAnalyze = async () => {
    if (!jobDescription) {
      alert("Please provide a job description.");
      return;
    }
    setLoading(true);
    setImprovedCvPdfUrl(null);
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
        const url = URL.createObjectURL(blob);
        setImprovedCvPdfUrl((prevUrl) => {
          if (prevUrl) URL.revokeObjectURL(prevUrl);
          return url;
        });
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(errData.detail || 'Failed to generate improved CV PDF.');
      }
    } catch (err) {
      console.error(err);
      alert('Network error while generating improved CV.');
    }
    setGeneratingImproved(false);
  };

  const handleGenerateLetter = async () => {
    if (!jobDescription) {
      alert("Please provide a job description.");
      return;
    }
    setGeneratingCoverLetter(true);
    try {
      const res = await apiFetch('/api/cv/download-cover-letter', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ job_description: jobDescription }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        setCoverLetterPdfUrl((prevUrl) => {
          if (prevUrl) URL.revokeObjectURL(prevUrl);
          return url;
        });
      } else {
        alert('Failed to generate cover letter PDF.');
      }
    } catch (err) {
      console.error(err);
      alert('Network error');
    }
    setGeneratingCoverLetter(false);
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
            <div 
              className={`upload-area ${isDragging ? 'drag-over' : ''}`} 
              onClick={() => document.getElementById('cv-upload').click()}
              onDragOver={handleDragOver}
              onDragEnter={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <div className="upload-icon-wrapper">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="17 8 12 3 7 8"></polyline>
                  <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
              </div>
              <p>{isDragging ? 'Drop your CV file here...' : 'Drag & Drop or Click to Upload (.pdf, .txt, .md)'}</p>
              <span>Supported formats: PDF, TXT, MD</span>
              <input 
                id="cv-upload" 
                type="file" 
                accept=".pdf,.txt,.md" 
                style={{ display: 'none' }} 
                onClick={(e) => { e.target.value = null; }}
                onChange={handleUpload} 
              />
            </div>
            {loading && <p style={{ textAlign: 'center', marginTop: '1.5rem', color: 'var(--accent-primary)', fontWeight: '600' }}>Uploading...</p>}
            {cvUploaded && (
              <div style={{ marginTop: '2.5rem' }}>
                <p style={{ color: 'var(--accent-success)', textAlign: 'center', marginBottom: '1.25rem', fontWeight: '600' }}>
                  ✓ CV is uploaded and ready!
                </p>
                <PDFViewer
                  key={cvPdfUrl || 'empty-cv'}
                  pdfUrl={cvPdfUrl}
                  title="Your Stored CV"
                  fileName={cvMetadata.fileName || "Stored_CV.pdf"}
                  loading={loadingCvPdf}
                />
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
                    Generate an optimized, 1-page PDF version of your CV with improvements applied. Your uploaded CV in storage remains untouched.
                  </p>
                  <div className="apply-buttons">
                    <button className="btn" onClick={handleGenerateImproved} disabled={generatingImproved}>
                      {generatingImproved ? 'Generating 1-Page PDF CV...' : 'Generate 1-Page PDF CV Preview'}
                    </button>
                  </div>
                </div>

                {(improvedCvPdfUrl || generatingImproved) && (
                  <div style={{ marginTop: '2rem' }}>
                    <PDFViewer
                      key={improvedCvPdfUrl || 'empty-improved'}
                      pdfUrl={improvedCvPdfUrl}
                      title="Tailored 1-Page CV"
                      fileName="Improved_CV.pdf"
                      loading={generatingImproved}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'coverLetter' && (
          <div>
            <button className="btn" onClick={handleGenerateLetter} disabled={generatingCoverLetter}>
              {generatingCoverLetter ? 'Generating Cover Letter PDF...' : 'Generate Cover Letter PDF'}
            </button>

            {(coverLetterPdfUrl || generatingCoverLetter) && (
              <div style={{ marginTop: '2rem' }}>
                <PDFViewer
                  key={coverLetterPdfUrl || 'empty-cover-letter'}
                  pdfUrl={coverLetterPdfUrl}
                  title="Tailored Cover Letter"
                  fileName="Cover_Letter.pdf"
                  loading={generatingCoverLetter}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
