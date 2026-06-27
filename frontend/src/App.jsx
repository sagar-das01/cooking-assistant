import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || (window.location.origin + '/api');

// A simple and robust Markdown-to-HTML parser function to render cooking guides beautifully
const parseMarkdown = (text) => {
  if (!text) return '';
  
  const lines = text.split('\n');
  let html = [];
  let inList = false;
  let inTable = false;
  let tableRows = [];
  
  for (let i = 0; i < lines.length; i++) {
    let line = lines[i].trim();
    
    // Handle Table
    if (line.startsWith('|')) {
      inTable = true;
      const cells = line.split('|').map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
      
      // Check if it's separator row
      if (line.includes('---')) {
        continue;
      }
      
      tableRows.push(cells);
      continue;
    } else if (inTable) {
      // Table ended, compile it
      if (tableRows.length > 0) {
        let tableHtml = '<table><thead><tr>';
        // Header
        tableRows[0].forEach(cell => {
          tableHtml += `<th>${cell}</th>`;
        });
        tableHtml += '</tr></thead><tbody>';
        // Rows
        for (let r = 1; r < tableRows.length; r++) {
          tableHtml += '<tr>';
          tableRows[r].forEach(cell => {
            let cellContent = cell.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            tableHtml += `<td>${cellContent}</td>`;
          });
          tableHtml += '</tr>';
        }
        tableHtml += '</tbody></table>';
        html.push(tableHtml);
      }
      inTable = false;
      tableRows = [];
    }
    
    // Handle Headings
    if (line.startsWith('###')) {
      if (inList) { html.push('</ul>'); inList = false; }
      let content = line.substring(3).trim();
      content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      html.push(`<h3>${content}</h3>`);
      continue;
    }
    
    // Handle Horizontal Rule
    if (line === '---' || line === '***') {
      if (inList) { html.push('</ul>'); inList = false; }
      html.push('<hr />');
      continue;
    }
    
    // Handle Lists
    if (line.startsWith('*') || line.startsWith('-')) {
      if (!inList) {
        html.push('<ul>');
        inList = true;
      }
      let content = line.substring(1).trim();
      content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      html.push(`<li>${content}</li>`);
      continue;
    } else {
      if (inList) {
        html.push('</ul>');
        inList = false;
      }
    }
    
    // Skip empty lines
    if (line === '') {
      continue;
    }
    
    // Handle Regular Paragraphs
    let content = line;
    content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html.push(`<p>${content}</p>`);
  }
  
  // Close any open tags
  if (inList) html.push('</ul>');
  if (inTable && tableRows.length > 0) {
    let tableHtml = '<table><thead><tr>';
    tableRows[0].forEach(cell => {
      tableHtml += `<th>${cell}</th>`;
    });
    tableHtml += '</tr></thead><tbody>';
    for (let r = 1; r < tableRows.length; r++) {
      tableHtml += '<tr>';
      tableRows[r].forEach(cell => {
        let cellContent = cell.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        tableHtml += `<td>${cellContent}</td>`;
      });
      tableHtml += '</tr>';
    }
    tableHtml += '</tbody></table>';
    html.push(tableHtml);
  }
  
  return html.join('');
};

function App() {
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [inputMsg, setInputMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('chef_assist_gemini_key') || '');
  const [showMobileSidebar, setShowMobileSidebar] = useState(false);
  const [backendHealthy, setBackendHealthy] = useState(true);
  const [toastMessage, setToastMessage] = useState('');
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  const messagesEndRef = useRef(null);

  // Check health and load sessions
  useEffect(() => {
    checkHealth();
    fetchSessions();
  }, []);

  // Scroll to bottom when currentSession changes or loading changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentSession, loading]);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(''), 3000);
  };

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        setBackendHealthy(true);
      } else {
        setBackendHealthy(false);
      }
    } catch {
      setBackendHealthy(false);
    }
  };

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/sessions`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (e) {
      console.error('Failed to fetch sessions:', e);
      setBackendHealthy(false);
    }
  };

  const selectSession = async (sessionId) => {
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        setCurrentSession(data);
        setShowMobileSidebar(false);
      }
    } catch (e) {
      console.error('Failed to load session details:', e);
      showToast('Error loading chat session');
    }
  };

  const handleCreateSession = async () => {
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New Cooking Session' }),
      });
      if (res.ok) {
        const newSess = await res.json();
        setSessions((prev) => [newSess, ...prev]);
        setCurrentSession(newSess);
        showToast('Created new session');
        setShowMobileSidebar(false);
      }
    } catch (e) {
      console.error('Failed to create session:', e);
      showToast('Failed to create session');
    }
  };

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this session?')) return;

    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
        if (currentSession && currentSession.id === sessionId) {
          setCurrentSession(null);
        }
        showToast('Session deleted');
      }
    } catch (e) {
      console.error('Failed to delete session:', e);
      showToast('Failed to delete session');
    }
  };

  const handleStartRename = (e, session) => {
    e.stopPropagation();
    setEditingSessionId(session.id);
    setEditTitle(session.title);
  };

  const handleSaveRename = async (e, sessionId) => {
    e.stopPropagation();
    if (!editTitle.trim()) return;

    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}/title`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: editTitle }),
      });
      if (res.ok) {
        setSessions((prev) =>
          prev.map((s) => (s.id === sessionId ? { ...s, title: editTitle } : s))
        );
        if (currentSession && currentSession.id === sessionId) {
          setCurrentSession((prev) => ({ ...prev, title: editTitle }));
        }
        setEditingSessionId(null);
        showToast('Renamed session');
      }
    } catch (e) {
      console.error('Failed to rename session:', e);
      showToast('Failed to rename session');
    }
  };

  const handleSendMessage = async (textToSend) => {
    const messageText = textToSend || inputMsg;
    if (!messageText.trim()) return;

    let sessionId = currentSession?.id;

    setLoading(true);
    if (!textToSend) {
      setInputMsg('');
    }

    try {
      // 1. Create a session if none is active
      if (!sessionId) {
        const sessionRes = await fetch(`${API_BASE}/sessions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: 'New Cooking Session' }),
        });
        if (sessionRes.ok) {
          const newSess = await sessionRes.json();
          sessionId = newSess.id;
          // Set sessions and currentSession locally first
          setSessions((prev) => [newSess, ...prev]);
          setCurrentSession(newSess);
        } else {
          showToast('Failed to create session');
          setLoading(false);
          return;
        }
      }

      // 2. Send message
      const headers = { 'Content-Type': 'application/json' };
      if (apiKey) {
        headers['X-Gemini-API-Key'] = apiKey;
      }

      const res = await fetch(`${API_BASE}/sessions/${sessionId}/message`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ content: messageText }),
      });

      if (res.ok) {
        const data = await res.json();
        setCurrentSession(data.session);
        // Refresh session list to update titles if changed
        fetchSessions();
      } else {
        showToast('Failed to send message');
      }
    } catch (e) {
      console.error('Error sending message:', e);
      showToast('Error connecting to backend server');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveApiKey = () => {
    localStorage.setItem('chef_assist_gemini_key', apiKey);
    setShowSettings(false);
    showToast('API Key saved successfully!');
  };

  const handleClearApiKey = () => {
    setApiKey('');
    localStorage.removeItem('chef_assist_gemini_key');
    setShowSettings(false);
    showToast('API Key cleared');
  };

  const starterPrompts = [
    { text: 'Plan a quick 15-minute dinner on a budget', icon: '⏱️' },
    { text: 'Help me plan low-carb meals for a busy workday', icon: '🥗' },
    { text: 'Vegetarian substitutions for common chicken recipes', icon: '🔄' },
    { text: 'Budget grocery list with oats, eggs, and veggies', icon: '🛒' },
  ];

  return (
    <div className="app-container">
      {/* Toast Notification */}
      {toastMessage && <div className="toast">{toastMessage}</div>}

      {/* Sidebar */}
      <div className={`sidebar ${showMobileSidebar ? 'show' : ''}`}>
        <div className="sidebar-header">
          <span className="brand-icon">🍳</span>
          <span className="brand-title">Chef Assist</span>
        </div>

        <button className="new-chat-btn" onClick={handleCreateSession}>
          <span>+</span> New Session
        </button>

        <div className="sessions-list">
          {sessions.map((sess) => (
            <div
              key={sess.id}
              className={`session-item ${currentSession?.id === sess.id ? 'active' : ''}`}
              onClick={() => selectSession(sess.id)}
            >
              <div className="session-title-wrapper">
                <span className="session-icon">💬</span>
                {editingSessionId === sess.id ? (
                  <input
                    type="text"
                    className="form-input"
                    style={{ padding: '4px 8px', fontSize: '0.85rem', width: '80%' }}
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveRename(e, sess.id);
                      if (e.key === 'Escape') setEditingSessionId(null);
                    }}
                    autoFocus
                  />
                ) : (
                  <span className="session-text">{sess.title}</span>
                )}
              </div>
              <div className="session-actions">
                {editingSessionId === sess.id ? (
                  <button
                    className="action-btn"
                    title="Save"
                    onClick={(e) => handleSaveRename(e, sess.id)}
                  >
                    💾
                  </button>
                ) : (
                  <button
                    className="action-btn"
                    title="Rename"
                    onClick={(e) => handleStartRename(e, sess)}
                  >
                    ✏️
                  </button>
                )}
                <button
                  className="action-btn"
                  title="Delete"
                  onClick={(e) => handleDeleteSession(e, sess.id)}
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <button className="settings-trigger" onClick={() => setShowSettings(true)}>
            ⚙️ Settings
          </button>
          {!backendHealthy && (
            <span style={{ color: '#ef4444', fontSize: '0.75rem', fontWeight: 600 }}>
              ⚠️ Server Offline
            </span>
          )}
        </div>
      </div>

      {/* Main Chat Panel */}
      <div className="chat-area">
        <div className="chat-header">
          <div className="header-title-container">
            <button
              className="menu-toggle"
              onClick={() => setShowMobileSidebar(!showMobileSidebar)}
            >
              ☰
            </button>
            <h1 className="header-title">
              {currentSession ? currentSession.title : 'AI Cooking Assistant'}
            </h1>
          </div>

          <div className="api-indicator">
            <span className={`indicator-dot ${apiKey ? 'active' : 'inactive'}`}></span>
            <span>{apiKey ? 'API Key Enabled' : 'Using Fallback Mock Mode'}</span>
          </div>
        </div>

        {/* Chat Area Body */}
        <div className="messages-container">
          {!currentSession || currentSession.messages.length === 0 ? (
            <div className="hero-container animate-fade">
              <div className="hero-logo">🍳</div>
              <div className="hero-headline">
                <h2>Plan Your Perfect Kitchen Day</h2>
                <p>Describe your day, schedule, or budget and Chef Assist will craft a custom meal plan and grocery list.</p>
              </div>

              <div className="feature-cards-grid">
                <div className="feature-card">
                  <div className="feature-card-icon">🍳</div>
                  <h4>Dynamic Meal Planning</h4>
                  <p>Breakfast, lunch, and dinner plans calibrated to your prep time.</p>
                </div>
                <div className="feature-card">
                  <div className="feature-card-icon">🛒</div>
                  <h4>Smart Grocery Lists</h4>
                  <p>Quantities organized by category to save shopping time.</p>
                </div>
                <div className="feature-card">
                  <div className="feature-card-icon">🔄</div>
                  <h4>Quick Substitutions</h4>
                  <p>Flexible recommendations for dietary restrictions or missing items.</p>
                </div>
                <div className="feature-card">
                  <div className="feature-card-icon">💰</div>
                  <h4>Budget Optimization</h4>
                  <p>Interactive value check and money-saving grocery strategies.</p>
                </div>
              </div>

              <div className="prompts-container">
                <h3 className="prompts-title">Try asking...</h3>
                <div className="prompts-grid">
                  {starterPrompts.map((prompt, idx) => (
                    <button
                      key={idx}
                      className="prompt-suggestion-btn"
                      onClick={() => handleSendMessage(prompt.text)}
                    >
                      <span>{prompt.icon} {prompt.text}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            currentSession.messages.map((msg) => (
              <div key={msg.id} className={`message-row ${msg.role}`}>
                <div className="message-bubble">
                  <div className="message-header">
                    {msg.role === 'user' ? 'You' : 'Chef Assist AI'}
                  </div>
                  {msg.role === 'user' ? (
                    <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                  ) : (
                    <div
                      className="markdown-content"
                      dangerouslySetInnerHTML={{ __html: parseMarkdown(msg.content) }}
                    />
                  )}
                </div>
              </div>
            ))
          )}

          {loading && (
            <div className="message-row model">
              <div className="message-loading">
                <div className="dot-loading"></div>
                <div className="dot-loading"></div>
                <div className="dot-loading"></div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="chat-footer">
          <div className="input-wrapper">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="input-container"
            >
              <input
                id="prompt-input"
                type="text"
                className="chat-input"
                placeholder="Message Chef Assist... (e.g., 'Plan meals for a busy Monday on a $15 budget')"
                value={inputMsg}
                onChange={(e) => setInputMsg(e.target.value)}
                disabled={loading}
              />
              <button
                type="submit"
                className="send-btn"
                disabled={loading || !inputMsg.trim()}
              >
                🍳
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="modal-backdrop">
          <div className="modal-content animate-fade">
            <div className="modal-header">
              <h3 className="modal-title">⚙️ Settings</h3>
              <button className="close-btn" onClick={() => setShowSettings(false)}>
                &times;
              </button>
            </div>

            <div className="form-group">
              <label className="form-label">Gemini API Key</label>
              <input
                type="password"
                className="form-input"
                placeholder="Enter your GEMINI_API_KEY"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
              <span className="form-help">
                Your key is stored locally in your browser and used only to query the Gemini models. Leave empty to use the server's default configuration or the built-in Chef Mock mode.
              </span>
            </div>

            <div className="modal-footer">
              <button className="btn-secondary" onClick={handleClearApiKey}>
                Clear Key
              </button>
              <button className="btn-primary" onClick={handleSaveApiKey}>
                Save & Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
