import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import DocumentViewer from './components/DocumentViewer';
import ChatPanel from './components/ChatPanel';
import DocumentUpload from './components/DocumentUpload';
import AIConfigModal from './components/AIConfigModal';
import LoginModal from './components/LoginModal';
import { useAuth } from './context/AuthContext';
import {
  fetchDocuments,
  fetchChatSessions,
  createChatSession,
  deleteChatSession,
  fetchSessionMessages,
  sendChatMessage,
  deleteDocument,
  reanalyzeDocument,
  fetchAIConfig
} from './services/api';
import { X, Loader2 } from 'lucide-react';

function App() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [activeDocument, setActiveDocument] = useState(null);
  const [chatSessions, setChatSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [aiConfig, setAiConfig] = useState(null);
  const [sending, setSending] = useState(false);
  const [initialPrompt, setInitialPrompt] = useState('');

  // Initial Data Fetching upon User Authentication
  useEffect(() => {
    if (isAuthenticated) {
      loadInitialData();
      loadAIConfig();
    } else {
      setDocuments([]);
      setChatSessions([]);
      setActiveDocument(null);
      setActiveSession(null);
      setMessages([]);
    }
  }, [isAuthenticated]);

  const loadInitialData = async () => {
    try {
      const docsData = await fetchDocuments();
      const docs = Array.isArray(docsData) ? docsData : (docsData.results || []);
      setDocuments(docs);

      const sessionsData = await fetchChatSessions();
      const sessions = Array.isArray(sessionsData) ? sessionsData : (sessionsData.results || []);
      setChatSessions(sessions);

      // Session Persistence: Restore last selected session or document from localStorage
      const savedSessionId = localStorage.getItem('activeSessionId');
      const savedDocId = localStorage.getItem('activeDocumentId');

      let restoredSession = null;
      let restoredDoc = null;

      if (savedSessionId) {
        restoredSession = sessions.find((s) => String(s.id) === String(savedSessionId));
      }

      if (savedDocId) {
        restoredDoc = docs.find((d) => String(d.id) === String(savedDocId));
      }

      if (restoredSession) {
        handleSelectSession(restoredSession, docs);
      } else if (restoredDoc) {
        handleSelectDocument(restoredDoc, sessions);
      } else if (docs.length > 0) {
        handleSelectDocument(docs[0], sessions);
      }
    } catch (err) {
      console.error('Failed to load initial data:', err);
    }
  };

  const loadAIConfig = async () => {
    try {
      const config = await fetchAIConfig();
      setAiConfig(config);
    } catch (err) {
      console.error('Failed to load AI config:', err);
    }
  };

  const handleSelectDocument = async (doc, existingSessions = chatSessions) => {
    setActiveDocument(doc);
    localStorage.setItem('activeDocumentId', doc.id);

    // Find existing session for this document
    let session = existingSessions.find((s) => s.document === doc.id);

    if (!session) {
      try {
        session = await createChatSession(doc.id, `Chat: ${doc.title}`);
        const updatedSessions = [session, ...existingSessions];
        setChatSessions(updatedSessions);
      } catch (err) {
        console.error('Failed to create chat session:', err);
        return;
      }
    }

    setActiveSession(session);
    localStorage.setItem('activeSessionId', session.id);
    loadSessionMessages(session.id);
  };

  const handleSelectSession = (session, existingDocs = documents) => {
    setActiveSession(session);
    localStorage.setItem('activeSessionId', session.id);
    if (session.document) {
      const matchedDoc = existingDocs.find((d) => String(d.id) === String(session.document));
      if (matchedDoc) {
        setActiveDocument(matchedDoc);
        localStorage.setItem('activeDocumentId', matchedDoc.id);
      }
    }
    loadSessionMessages(session.id);
  };

  const loadSessionMessages = async (sessionId) => {
    try {
      const msgs = await fetchSessionMessages(sessionId);
      setMessages(Array.isArray(msgs) ? msgs : (msgs.results || []));
    } catch (err) {
      console.error('Failed to load messages:', err);
      setMessages([]);
    }
  };

  const handleUploadSuccess = async (newDoc) => {
    setShowUploadModal(false);
    const updatedDocs = [newDoc, ...documents];
    setDocuments(updatedDocs);
    await handleSelectDocument(newDoc, chatSessions);
  };

  const handleDeleteDocument = async (docId) => {
    try {
      await deleteDocument(docId);
      const updatedDocs = documents.filter((d) => d.id !== docId);
      setDocuments(updatedDocs);

      // Clean up chat sessions associated with deleted document
      const updatedSessions = chatSessions.filter((s) => s.document !== docId);
      setChatSessions(updatedSessions);

      if (activeDocument && activeDocument.id === docId) {
        if (updatedDocs.length > 0) {
          handleSelectDocument(updatedDocs[0], updatedSessions);
        } else {
          setActiveDocument(null);
          setActiveSession(null);
          localStorage.removeItem('activeDocumentId');
          localStorage.removeItem('activeSessionId');
          setMessages([]);
        }
      }
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    try {
      await deleteChatSession(sessionId);
      const updatedSessions = chatSessions.filter((s) => s.id !== sessionId);
      setChatSessions(updatedSessions);

      if (activeSession && activeSession.id === sessionId) {
        if (updatedSessions.length > 0) {
          handleSelectSession(updatedSessions[0]);
        } else {
          setActiveSession(null);
          localStorage.removeItem('activeSessionId');
          setMessages([]);
        }
      }
    } catch (err) {
      console.error('Failed to delete chat session:', err);
    }
  };

  const handleReanalyzeDocument = async (docId, focus) => {
    try {
      const updatedDoc = await reanalyzeDocument(docId, focus);
      setActiveDocument(updatedDoc);
      setDocuments((prev) => prev.map((d) => (d.id === docId ? updatedDoc : d)));
    } catch (err) {
      console.error('Failed to reanalyze document:', err);
    }
  };

  const handleSendMessage = async (content) => {
    setSending(true);
    setInitialPrompt('');

    // Optimistically add user message
    const tempUserMsg = { sender: 'user', content, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      let currentSession = activeSession;
      if (!currentSession) {
        // Auto-create session on first message
        const docId = activeDocument ? activeDocument.id : null;
        const title = activeDocument ? `Chat: ${activeDocument.title}` : 'General AI Chat';
        currentSession = await createChatSession(docId, title);
        setChatSessions((prev) => [currentSession, ...prev]);
        setActiveSession(currentSession);
        localStorage.setItem('activeSessionId', currentSession.id);
      }

      const response = await sendChatMessage(currentSession.id, content);
      if (response.user_message && response.assistant_message) {
        setMessages((prev) => [
          ...prev.slice(0, prev.length - 1),
          response.user_message,
          response.assistant_message
        ]);
      }
    } catch (err) {
      console.error('Failed to send message:', err);
      const detail = err.response?.data?.error || err.response?.data?.detail;
      const errorMsg = {
        sender: 'assistant',
        content: detail ? `⚠️ ${detail}` : '⚠️ Server is currently spinning up or unreachable. Please try your question again in a moment.',
        timestamp: new Date().toISOString()
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setSending(false);
    }
  };

  const handlePromptChipClick = (promptText) => {
    handleSendMessage(promptText);
  };

  if (authLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-zinc-950 text-zinc-400">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-950 text-zinc-100">
      {/* Show Auth Modal if not logged in */}
      {!isAuthenticated && <LoginModal />}

      {/* Sidebar Navigation */}
      <Sidebar
        documents={documents}
        activeDocument={activeDocument}
        onSelectDocument={(doc) => handleSelectDocument(doc)}
        onNewDocumentClick={() => setShowUploadModal(true)}
        chatSessions={chatSessions}
        activeSession={activeSession}
        onSelectSession={handleSelectSession}
        onDeleteDocument={handleDeleteDocument}
        onDeleteSession={handleDeleteSession}
        aiConfig={aiConfig}
        onOpenConfigModal={() => setShowConfigModal(true)}
      />

      {/* Main Workspace */}
      <main className="flex flex-1 overflow-hidden">
        {/* Document Viewer & Insights Pane */}
        <DocumentViewer
          document={activeDocument}
          onPromptChipClick={handlePromptChipClick}
          onReanalyzeDocument={handleReanalyzeDocument}
        />

        {/* Interactive Chat Panel */}
        <ChatPanel
          activeSession={activeSession}
          messages={messages}
          onSendMessage={handleSendMessage}
          sending={sending}
          initialPrompt={initialPrompt}
          documentTitle={activeDocument?.title}
        />
      </main>

      {/* Upload Document Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="relative w-full max-w-lg">
            <button
              onClick={() => setShowUploadModal(false)}
              className="absolute -top-12 right-0 p-2 text-zinc-400 hover:text-white transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
            <DocumentUpload onUploadSuccess={handleUploadSuccess} />
          </div>
        </div>
      )}

      {/* AI Key Configuration Modal */}
      <AIConfigModal
        isOpen={showConfigModal}
        onClose={() => setShowConfigModal(false)}
        currentConfig={aiConfig}
        onConfigUpdated={loadAIConfig}
      />
    </div>
  );
}

export default App;
