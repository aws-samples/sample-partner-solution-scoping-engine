import React, { useState, useEffect } from 'react';
import {
  Box,
  Badge,
  Header
} from '@cloudscape-design/components';
import { API_BASE_URL } from '../config';
import ApprovalDetailsModal from './ApprovalDetailsModal';

const Approvals = ({ chatId, refreshTrigger }) => {
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalState, setModalState] = useState({ isOpen: false, approval: null });
  const [documents, setDocuments] = useState({});
  const [downloading, setDownloading] = useState({});

  const fetchApprovals = async () => {
    try {
      setLoading(true);
      
      // Fetch chat data for approvals
      const chatResponse = await fetch(`${API_BASE_URL}/chats/${chatId}`, {
        credentials: 'include'
      });
      
      // Fetch documents separately
      const documentsResponse = await fetch(`${API_BASE_URL}/chats/${chatId}/documents`, {
        credentials: 'include'
      });
      
      if (chatResponse.ok && documentsResponse.ok) {
        const chatData = await chatResponse.json();
        const documentsData = await documentsResponse.json();
        
        const approvalsData = (chatData.approvals || []).sort((a, b) => 
          new Date(b.approved_timestamp) - new Date(a.approved_timestamp)
        );
        
        setApprovals(approvalsData);
        setDocuments(documentsData.documents || {});
      }
    } catch (err) {
      console.error('Error fetching approvals:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (chatId) {
      fetchApprovals();
    }
  }, [chatId, refreshTrigger]);

  if (loading) return null;
  
  // Don't render anything if there are no approvals
  if (approvals.length === 0) return null;

  return (
    <div>
      <Header variant="h4">
        Approvals
      </Header>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '8px', maxWidth: '100%', marginTop: '16px' }}>
        {approvals.map((approval, index) => (
            <div 
              key={approval.approval_id || index}
              style={{ 
                cursor: 'default',
                border: '1px solid #e9ebed',
                borderRadius: '12px',
                backgroundColor: '#fff',
                transition: 'background-color 0.2s',
                padding: '4px',
                textAlign: 'center',
                position: 'relative'
              }}
              onMouseEnter={(e) => {
                const buttons = e.currentTarget.querySelector('.hover-buttons');
                if (buttons) buttons.style.opacity = '1';
                
                // Expand Documents section
                if (window.expandDocuments) {
                  window.expandDocuments();
                }
                
                // Highlight related documents
                setTimeout(() => {
                  const tiles = document.querySelectorAll('.document-tile');
                  
                  tiles.forEach(tile => {
                    const tileDocId = tile.getAttribute('data-doc-id');
                    if (approval.document_ids && approval.document_ids.includes(tileDocId)) {
                      tile.style.backgroundColor = '#e3f2fd';
                      tile.style.boxShadow = '0 0 0 2px #1976d2';
                    }
                  });
                }, 200);
              }}
              onMouseLeave={(e) => {
                const buttons = e.currentTarget.querySelector('.hover-buttons');
                if (buttons) buttons.style.opacity = '0';
                
                // Remove highlighting from documents
                const tiles = document.querySelectorAll('.document-tile');
                tiles.forEach(tile => {
                  tile.style.backgroundColor = '';
                  tile.style.boxShadow = '';
                });
              }}
              onMouseOut={(e) => {
                // Additional cleanup for fast cursor movement
                if (!e.currentTarget.contains(e.relatedTarget)) {
                  const buttons = e.currentTarget.querySelector('.hover-buttons');
                  if (buttons) buttons.style.opacity = '0';
                  
                  const tiles = document.querySelectorAll('.document-tile');
                  tiles.forEach(tile => {
                    tile.style.backgroundColor = '';
                    tile.style.boxShadow = '';
                  });
                }
              }}
            >
              <div style={{ fontSize: '10px', color: '#666' }}>
                {approval.approved_by}
              </div>
              <div style={{ fontSize: '10px', color: '#666' }}>
                {new Date(approval.approved_timestamp).toLocaleDateString('en-US', { 
                  month: 'short', 
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </div>
              
              <div 
                className="hover-buttons"
                style={{ 
                  position: 'absolute',
                  top: '0%',
                  left: '0%',
                  width: '100%',
                  height: '100%',
                  display: 'flex', 
                  gap: '2px', 
                  alignItems: 'center',
                  justifyContent: 'center',
                  opacity: '0',
                  backgroundColor: 'rgba(255, 255, 255, 0.4)',
                  borderRadius: '8px',
                  pointerEvents: 'none'
                }}
              >
                <button
                  onClick={async () => {
                    const approvalId = approval.approval_id;
                    try {
                      setDownloading(prev => ({ ...prev, [approvalId]: true }));
                      const response = await fetch(`${API_BASE_URL}/chats/${chatId}/approvals/${approvalId}/download`, {
                        credentials: 'include'
                      });
                      
                      if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `approval_${approvalId}_documents.zip`;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                      }
                    } catch (error) {
                      console.error('Error downloading approval documents:', error);
                    } finally {
                      setDownloading(prev => ({ ...prev, [approvalId]: false }));
                    }
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '8px',
                    borderRadius: '4px',
                    width: '30%',
                    height: '80%',
                    pointerEvents: 'auto',
                    transition: 'transform 0.1s'
                  }}
                  onMouseEnter={(e) => e.target.style.transform = 'scale(1.3)'}
                  onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
                  title="Download"
                >
                  {downloading[approval.approval_id] ? (
                    <svg key="spinner" width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" opacity="0.25"/>
                      <path d="M12 2 A10 10 0 0 1 22 12" strokeLinecap="round">
                        <animateTransform
                          attributeName="transform"
                          attributeType="XML"
                          type="rotate"
                          from="0 12 12"
                          to="360 12 12"
                          dur="1s"
                          repeatCount="indefinite"
                        />
                      </path>
                    </svg>
                  ) : (
                    <svg key="download" width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="7,10 12,15 17,10"/>
                      <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                  )}
                </button>
                <button
                  onClick={() => {
                    setModalState({ isOpen: true, approval });
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '8px',
                    borderRadius: '4px',
                    width: '30%',
                    height: '80%',
                    pointerEvents: 'auto',
                    transition: 'transform 0.1s'
                  }}
                  onMouseEnter={(e) => e.target.style.transform = 'scale(1.3)'}
                  onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
                  title="View Details"
                >
                  <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      
      <ApprovalDetailsModal
        isOpen={modalState.isOpen}
        onClose={() => setModalState({ isOpen: false, approval: null })}
        approval={modalState.approval}
        documents={documents}
      />
    </div>
  );
};

export default Approvals;
