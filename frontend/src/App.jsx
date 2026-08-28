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
import { X, Loader2, Menu, FileText, MessageSquare, Plus } from 'lucide-react';

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
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [mobileTab, setMobileTab] = useState('doc'); // 'doc' | 'chat'

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
    if (session.messages && Array.isArray(session.messages)) {
      setMessages(session.messages);
    } else {
      setMessages([]);
    }
    loadSessionMessages(session.id);
  };

  const handleSelectSession = (session, existingDocs = documents) => {
    setActiveSession(session);
    localStorage.setItem('activeSessionId', session.id);

    // Instant 0ms display from local cache
    if (session.messages && Array.isArray(session.messages)) {
      setMessages(session.messages);
    } else {
      setMessages([]);
    }

    if (session.document) {
      const matchedDoc = existingDocs.find((d) => String(d.id) === String(session.document));
      if (matchedDoc) {
        setActiveDocument(matchedDoc);
        localStorage.setItem('activeDocumentId', matchedDoc.id);
      }
    } else {
      setActiveDocument(null);
      localStorage.removeItem('activeDocumentId');
    }

    loadSessionMessages(session.id);
  };

  const loadSessionMessages = async (sessionId) => {
    try {
      const msgs = await fetchSessionMessages(sessionId);
      const messageList = Array.isArray(msgs) ? msgs : (msgs.results || []);
      setMessages(messageList);
      // Cache messages inside chatSessions array for instant zero-lag switching
      setChatSessions((prev) =>
        prev.map((s) => (s.id === sessionId ? { ...s, messages: messageList } : s))
      );
    } catch (err) {
      console.error('Failed to load messages:', err);
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
        const updatedList = [
          ...messages,
          response.user_message,
          response.assistant_message
        ];
        setMessages((prev) => [
          ...prev.slice(0, prev.length - 1),
          response.user_message,
          response.assistant_message
        ]);
        setChatSessions((prevSessions) =>
          prevSessions.map((s) =>
            s.id === currentSession.id ? { ...s, messages: updatedList } : s
          )
        );
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
    setMobileTab('chat');
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
    <div className="flex h-[100dvh] w-screen overflow-hidden bg-zinc-950 text-zinc-100 flex-col lg:flex-row">
      {/* Show Auth Modal if not logged in */}
      {!isAuthenticated && <LoginModal />}

      {/* Sidebar Navigation (Desktop persistent + Mobile slide-over drawer) */}
      <Sidebar
        isOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
        documents={documents}
        activeDocument={activeDocument}
        onSelectDocument={(doc) => {
          handleSelectDocument(doc);
          setMobileTab('doc');
          setIsMobileMenuOpen(false);
        }}
        onNewDocumentClick={() => {
          setShowUploadModal(true);
          setIsMobileMenuOpen(false);
        }}
        chatSessions={chatSessions}
        activeSession={activeSession}
        onSelectSession={(session) => {
          handleSelectSession(session);
          setMobileTab('chat');
          setIsMobileMenuOpen(false);
        }}
        onDeleteDocument={handleDeleteDocument}
        onDeleteSession={handleDeleteSession}
        aiConfig={aiConfig}
        onOpenConfigModal={() => {
          setShowConfigModal(true);
          setIsMobileMenuOpen(false);
        }}
      />

      {/* Mobile Top Navigation Header (< lg) */}
      <header className="lg:hidden h-14 bg-zinc-900/90 border-b border-zinc-800/80 px-3 flex items-center justify-between flex-shrink-0 z-30 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsMobileMenuOpen(true)}
            className="p-2 text-zinc-300 hover:text-white hover:bg-zinc-800/80 rounded-xl transition-colors active:scale-95"
            title="Open Menu"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-1.5">
            <img src="/logo.png" alt="DocMind" className="w-6 h-6 rounded-lg object-cover" />
            <span className="font-semibold text-sm text-zinc-100">DocMind</span>
          </div>
        </div>

        {/* Mobile Tab Segmented Switcher & Quick Upload */}
        <div className="flex items-center gap-2">
          <div className="flex bg-zinc-950 p-0.5 rounded-xl border border-zinc-800 text-xs font-medium">
            <button
              onClick={() => setMobileTab('doc')}
              className={`flex items-center gap-1 px-3 py-1 rounded-lg transition-all ${
                mobileTab === 'doc'
                  ? 'bg-indigo-600 text-white shadow-sm font-semibold'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Doc</span>
            </button>
            <button
              onClick={() => setMobileTab('chat')}
              className={`flex items-center gap-1 px-3 py-1 rounded-lg transition-all ${
                mobileTab === 'chat'
                  ? 'bg-indigo-600 text-white shadow-sm font-semibold'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Chat</span>
            </button>
          </div>

          <button
            onClick={() => setShowUploadModal(true)}
            className="p-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl shadow-sm transition-colors active:scale-95"
            title="Upload Document"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Workspace (Desktop: Side-by-side, Mobile: Switched by mobileTab) */}
      <main className="flex flex-1 flex-col lg:flex-row overflow-hidden min-h-0">
        {/* Document Viewer & Insights Pane */}
        <div className={`flex-1 flex flex-col min-h-0 overflow-hidden ${mobileTab === 'doc' ? 'flex' : 'hidden lg:flex'}`}>
          <DocumentViewer
            document={activeDocument}
            onPromptChipClick={handlePromptChipClick}
            onReanalyzeDocument={handleReanalyzeDocument}
          />
        </div>

        {/* Interactive Chat Panel */}
        <div className={`w-full lg:w-[380px] xl:w-[420px] flex flex-col min-h-0 overflow-hidden flex-shrink-0 ${mobileTab === 'chat' ? 'flex' : 'hidden lg:flex'}`}>
          <ChatPanel
            activeSession={activeSession}
            messages={messages}
            onSendMessage={handleSendMessage}
            sending={sending}
            initialPrompt={initialPrompt}
            documentTitle={activeDocument?.title}
          />
        </div>
      </main>

      {/* Upload Document Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="relative w-full max-w-lg mx-auto">
            <button
              onClick={() => setShowUploadModal(false)}
              className="absolute -top-10 right-0 sm:-top-12 sm:right-0 p-2 text-zinc-400 hover:text-white transition-colors"
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
