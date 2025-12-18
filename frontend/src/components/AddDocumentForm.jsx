import React, { useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

const AddDocumentForm = ({ onDocAdded }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    type: 'pdf', // pdf, html, or json
    file: null, // For PDF/JSON file uploads
    url: '', // For HTML URL or optional metadata for PDF/JSON
    jsonBody: '' // For JSON body input
  });

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFormData({ ...formData, file: file });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    setIsSubmitting(true);

    try {
      let response;
      let result;

      if (formData.type === 'pdf') {
        // PDF Upload
        if (!formData.file) {
          alert('Please select a PDF file');
          setIsSubmitting(false);
          return;
        }

        const formDataToSend = new FormData();
        formDataToSend.append('file', formData.file);
        if (formData.url) {
          formDataToSend.append('url', formData.url); // Optional, metadata only
        }

        response = await fetch(`${API_BASE_URL}/index/rps`, {
          method: 'POST',
          body: formDataToSend, // multipart/form-data
        });

      } else if (formData.type === 'html') {
        // HTML URL
        if (!formData.url || !formData.url.trim()) {
          alert('Please enter a URL');
          setIsSubmitting(false);
          return;
        }

        response = await fetch(`${API_BASE_URL}/index/html`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            url: formData.url
          }),
        });

      } else if (formData.type === 'json') {
        // JSON Upload
        if (formData.file) {
          // JSON file upload
          const formDataToSend = new FormData();
          formDataToSend.append('file', formData.file);
          if (formData.url) {
            formDataToSend.append('url', formData.url); // Optional, metadata only
          }

          response = await fetch(`${API_BASE_URL}/index/json`, {
            method: 'POST',
            body: formDataToSend, // multipart/form-data
          });

        } else if (formData.jsonBody && formData.jsonBody.trim()) {
          // JSON body upload
          try {
            const jsonDoc = JSON.parse(formData.jsonBody);
            const requestBody = { ...jsonDoc };
            if (formData.url) {
              requestBody.url = formData.url; // Optional, metadata only
            }

            response = await fetch(`${API_BASE_URL}/index/json`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify(requestBody),
            });
          } catch (parseError) {
            alert('Invalid JSON format. Please check your JSON syntax.');
            setIsSubmitting(false);
            return;
          }
        } else {
          alert('Please select a JSON file or paste JSON content');
          setIsSubmitting(false);
          return;
        }
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Upload failed: ${response.statusText}`);
      }

      result = await response.json();

      if (result.success === false) {
        throw new Error(result.error || 'Upload request failed');
      }

      // Show success message
      const title = result.title || (formData.file ? formData.file.name.replace(/\.(pdf|json)$/i, '') : 'Document');
      const docId = result.doc_id || 'unknown';
      alert(`Document "${title}" indexed as ${docId}!`);

      // Call callback with result
      if (onDocAdded) {
        onDocAdded(result);
      }

      // Reset form
      setFormData({ type: 'pdf', file: null, url: '', jsonBody: '' });
      setIsOpen(false);
    } catch (error) {
      console.error('Upload error:', error);
      alert(`Error: ${error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) {
    return (
      <div className="add-doc-card" style={{ textAlign: 'center', cursor: 'pointer', padding: '1rem' }} onClick={() => setIsOpen(true)}>
        <span style={{ color: 'var(--primary)', fontWeight: 'bold' }}>+ Add New Document</span>
      </div>
    );
  }

  return (
    <div className="add-doc-card">
      <div className="form-title">
        <span>Add Data Source</span>
        <button 
          onClick={(e) => { e.stopPropagation(); setIsOpen(false); }}
          style={{ marginLeft: 'auto', background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}
        >
          Close
        </button>
      </div>
      
      <form onSubmit={handleSubmit} className="form-grid">
        <select
          className="form-select"
          value={formData.type}
          onChange={e => setFormData({...formData, type: e.target.value, file: null, jsonBody: ''})}
        >
          <option value="pdf">PDF (Research Paper)</option>
          <option value="html">HTML (Web Page URL)</option>
          <option value="json">JSON (Research Paper)</option>
        </select>

        {/* PDF Upload Option */}
        {formData.type === 'pdf' && (
          <>
            <input
              className="form-input"
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              required
            />
            {formData.file && (
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Selected: {formData.file.name}
              </span>
            )}
            <input
              className="form-input"
              type="url"
              placeholder="URL (optional, metadata only)"
              value={formData.url}
              onChange={e => setFormData({...formData, url: e.target.value})}
            />
          </>
        )}

        {/* HTML URL Option */}
        {formData.type === 'html' && (
          <input
            className="form-input"
            type="url"
            placeholder="URL (https://...)"
            value={formData.url}
            onChange={e => setFormData({...formData, url: e.target.value})}
            required
          />
        )}

        {/* JSON Upload Option */}
        {formData.type === 'json' && (
          <>
            <input
              className="form-input"
              type="file"
              accept=".json"
              onChange={handleFileChange}
            />
            {formData.file && (
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Selected: {formData.file.name}
              </span>
            )}
            {!formData.file && (
              <textarea
                className="form-input"
                placeholder="Paste JSON document here (CORD-19 format)..."
                rows="8"
                value={formData.jsonBody}
                onChange={e => setFormData({...formData, jsonBody: e.target.value})}
                required
                style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
              />
            )}
            <input
              className="form-input"
              type="url"
              placeholder="URL (optional, metadata only)"
              value={formData.url}
              onChange={e => setFormData({...formData, url: e.target.value})}
            />
          </>
        )}

        <button type="submit" className="btn-add" disabled={isSubmitting}>
          {isSubmitting ? 'Indexing...' : 'Add to Index'}
        </button>
      </form>
    </div>
  );
};

export default AddDocumentForm;