import React, { useState, useEffect } from 'react';
import apiClient from '../services/apiClient';
import {
  Container,
  Header,
  SpaceBetween,
  Box,
  Button,
  StatusIndicator,
  Alert,
  Spinner,
  ExpandableSection,
  Badge,
  Modal
} from '@cloudscape-design/components';
import { API_BASE_URL } from '../config';
import { getDocumentCFSignedUrl } from '../services/fileService';
import DocumentPreviewModal from './DocumentPreviewModal';
import Approvals from './Approvals';

// Add CSS for blinking animation
const blinkingStyle = `
  @keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0.3; }
  }
  .blinking {
    animation: blink 1.5s infinite;
  }
  @keyframes smoothBlink {
    0%, 100% { background-color: #0972d3; }
    50% { background-color: #b3d4f0; }
  }
  .smooth-blinking {
    animation: smoothBlink 1.2s ease-in-out infinite;
  }
`;

// Inject CSS into document head
if (!document.getElementById('documents-blinking-styles')) {
  const style = document.createElement('style');
  style.id = 'documents-blinking-styles';
  style.textContent = blinkingStyle;
  document.head.appendChild(style);
}

const Documents = ({ chatId, refreshTrigger, isReviewCopy = false }) => {
  const [documents, setDocuments] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [approving, setApproving] = useState({});
  const [expanded, setExpanded] = useState(false);
  const [previewModal, setPreviewModal] = useState({ isOpen: false, documentId: null, documentType: null });
  const [statusModal, setStatusModal] = useState({ isOpen: false, status: null, loading: false });
  const [isSA, setIsSA] = useState(false);

  // Listen for expand requests
  useEffect(() => {
    window.expandDocuments = () => setExpanded(true);
    return () => delete window.expandDocuments;
  }, []);

  // Check if user is Solutions Architect
  const checkIsSA = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/user/is-sa`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setIsSA(data.is_sa);
      }
    } catch (err) {
      // Silently fail - user will be treated as non-SA
    }
  };

  // Document type display names
  const documentTypeNames = {
    // AI-generated (existing)
    diagram: 'Architecture Diagrams',
    sow_document: 'Statements of Work',
    pricing_report: 'Cost Analysis Reports',
    funding_document: 'Funding Documents',
    cloudformation_template: 'CloudFormation Templates',
    calculator_link: 'Calculator Links',
    
    // User uploads (mapped to existing types or new categories)
    user_upload: 'Other Uploaded Files'  // For unclassified or unmapped uploads
  };

  // Helper function to determine if a document is an architecture diagram
  const isArchitectureDiagram = (doc) => {
    // AI-generated diagrams
    if (doc.document_type === 'diagram') return true;
    
    // User uploaded diagrams - check classification and filename
    if (doc.tool_name === 'user_uploaded') {
      return doc.document_classification === 'architecture_diagram' ||
             doc.original_filename?.toLowerCase().includes('diagram') ||
             doc.original_filename?.toLowerCase().includes('architecture');
    }
    
    return false;
  };

  // Helper function to determine if a document can be previewed
  const canPreviewDocument = (doc) => {
    // Always allow preview for architecture diagrams
    if (isArchitectureDiagram(doc)) return true;
    
    // Allow preview for AI-generated documents
    if (doc.document_type === 'sow_document') return true;
    if (doc.document_type === 'funding_document') return true;
    if (doc.document_type === 'pricing_report') return true;
    if (doc.document_type === 'cloudformation_template') return true;
    if (doc.document_type === 'calculator_link') return true;
    if (doc.document_type === 'wafr_assessment') return true;
    
    // Allow preview for user uploads based on file extension or classification
    if (doc.tool_name === 'user_uploaded') {
      const filename = doc.original_filename?.toLowerCase() || '';
      const classification = doc.document_classification || '';
      
      // Image files
      if (filename.includes('.png') || filename.includes('.jpg') || filename.includes('.jpeg') || 
          filename.includes('.gif') || filename.includes('.svg') || filename.includes('.bmp')) return true;
      
      // Document files (including PDF)
      if (filename.includes('.pdf') || filename.includes('.docx') || filename.includes('.doc')) return true;
      
      // Text/code files
      if (filename.includes('.md') || filename.includes('.txt') || filename.includes('.yaml') || 
          filename.includes('.yml') || filename.includes('.json') || filename.includes('.csv') ||
          filename.includes('.xml') || filename.includes('.html') || filename.includes('.htm')) return true;
      
      // Based on classification
      if (['sow_document', 'funding_document', 'technical_document', 'presentation', 'pricing_calculator_csv'].includes(classification)) return true;
    }
    
    return false;
  };

  // Helper function to get classification display name
  const getClassificationDisplayName = (classification) => {
    const displayNames = {
      'sow_document': 'SOW Document',
      'architecture_diagram': 'Architecture Diagram',
      'pricing_calculator_csv': 'Pricing Calculator',
      'funding_document': 'Funding Document',
      'cloudformation_template': 'CloudFormation Template',
      'technical_document': 'Technical Document',
      'contract': 'Contract',
      'presentation': 'Presentation'
    };
    
    return displayNames[classification] || classification?.replace('_', ' ').toUpperCase() || 'Unclassified';
  };

  // Fetch documents for the chat
  const fetchDocuments = async () => {
    try {
      setLoading(true);
      console.log('🔍 Fetching documents for chat:', chatId);
      const response = await fetch(`${API_BASE_URL}/chats/${chatId}/documents`, {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('📄 Documents response:', data);
        
        // Group documents by type
        const grouped = {};
        Object.entries(data.documents || {}).forEach(([docId, doc]) => {
          const type = doc.document_type || 'other';
          if (!grouped[type]) grouped[type] = [];
          grouped[type].push({ id: docId, ...doc });
          
          // Debug log each document
          console.log('📄 Document found:', {
            id: docId,
            tool_name: doc.tool_name,
            approved: doc.approved,
            document_type: doc.document_type,
            original_filename: doc.original_filename
          });
        });
        
        // Sort each group by creation timestamp, newest first
        Object.keys(grouped).forEach(type => {
          grouped[type].sort((a, b) => new Date(b.created_timestamp) - new Date(a.created_timestamp));
        });
        
        setDocuments(grouped);
      } else {
        setError('Failed to load documents');
      }
    } catch (err) {
      setError('Error loading documents');
    } finally {
      setLoading(false);
    }
  };

  // Approve document
  const approveDocument = async (documentId) => {
    try {
      setApproving(prev => ({ ...prev, [documentId]: true }));
      
      await apiClient.post(`/chats/${chatId}/documents/${documentId}/approve`);
      
      // Refresh documents to show updated approval status
      await fetchDocuments();
    } catch (err) {
      setError('Error approving document');
    } finally {
      setApproving(prev => ({ ...prev, [documentId]: false }));
    }
  };

  // Download document
  const downloadDocument = async (documentId, documentType) => {
    try {
      const doc = Object.values(documents).flat().find(d => d.id === documentId);
      
      // Debug logging
      console.log('🔍 Download attempt:', {
        documentId,
        documentType,
        doc: doc ? {
          id: doc.id,
          tool_name: doc.tool_name,
          approved: doc.approved,
          document_type: doc.document_type
        } : 'NOT_FOUND',
        isSA,
        isReviewCopy
      });
      
      if (!doc.approved && !(isSA || isReviewCopy) && doc.tool_name !== 'user_uploaded') {
        console.log('❌ Download blocked: Document not approved and not user uploaded');
        setError('Document not approved for download');
        setTimeout(() => setError(null), 1000);
        return;
      }
      
      console.log('✅ Download allowed - proceeding...');

      // For diagrams and WAFR assessments, use the actual s3_key from the document metadata
      if (documentType === 'diagram' || documentType === 'wafr_assessment') {
        if (doc.s3_key) {
          // Handle both migrated and new chat s3_key formats
          let relativePath;
          if (doc.s3_key.startsWith(`${chatId}/`)) {
            // New format: s3_key includes chatId prefix, remove it
            relativePath = doc.s3_key.replace(`${chatId}/`, '');
          } else {
            // Migrated format: s3_key is the full path, extract relative part
            // For migrated chats, s3_key = "96297ab7-faac-4555-b082-22d728df8590/pricing/pricing.md"
            // We need just "pricing/pricing.md"
            const parts = doc.s3_key.split('/');
            if (parts.length > 1 && parts[0] === chatId) {
              relativePath = parts.slice(1).join('/');
            } else {
              relativePath = doc.s3_key;
            }
          }
          console.log('WAFR Download Debug:', { 
            documentType, 
            s3_key: doc.s3_key, 
            relativePath, 
            version_id: doc.version_id,
            chatId 
          });
          
          const response = await getDocumentCFSignedUrl(chatId, relativePath, doc.version_id);
          console.log('WAFR Download CloudFront URL response:', response);
          
          if (response && response.url) {
            window.open(response.url, '_blank');
            return;
          } else {
            console.error('WAFR Download: Failed to get URL, response:', response);
            setError('Failed to get download URL');
            return;
          }
        } else {
          console.error('WAFR Download: Document missing s3_key:', doc);
          setError('Document path not found');
          return;
        }
      }
      
      // Fallback for other document types
      const response = await fetch(`${API_BASE_URL}/chats/${chatId}/documents/${documentId}/download`, {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        window.open(data.download_url, '_blank');
      } else {
        setError('Failed to download document');
      }
    } catch (err) {
      setError('Error downloading document');
    }
  };

  useEffect(() => {
    if (chatId) {
      fetchDocuments();
    }
  }, [chatId, refreshTrigger]);

  useEffect(() => {
    checkIsSA();
  }, []);

  // Debug: Log documents whenever they change
  useEffect(() => {
    console.log('Documents changed:', documents);
    console.log('Documents type:', typeof documents);
    console.log('Documents length:', documents?.length);
    if (documents?.length > 0) {
      console.log('First document:', documents[0]);
      console.log('Calculator links:', documents.filter(doc => doc.document_type === 'calculator_link'));
    }
  }, [documents]);

  // Poll calculator link statuses every 10 seconds
  useEffect(() => {
    console.log('Polling effect triggered, documents:', documents);
    
    // Convert documents object to array
    const documentsArray = Object.values(documents).flat();
    console.log('Documents array length:', documentsArray.length);
    
    if (documentsArray.length === 0) {
      console.log('No documents found, skipping polling');
      return;
    }

    const calculatorLinks = documentsArray.filter(doc => 
      doc.document_type === 'calculator_link' && 
      ['pending', 'running'].includes(doc.status)
    );

    console.log('Calculator links found:', calculatorLinks.length, calculatorLinks);

    if (calculatorLinks.length === 0) {
      console.log('No pending/running calculator links, skipping polling');
      return;
    }

    console.log('Starting polling for', calculatorLinks.length, 'calculator links');
    const pollInterval = setInterval(async () => {
      console.log('Polling calculator link statuses...');
      for (const doc of calculatorLinks) {
        try {
          console.log(`Polling status for job ${doc.id}`);
          const response = await fetch(`${API_BASE_URL}/nova/status/${doc.id}?chat_id=${chatId}`, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
          });
          if (response.ok) {
            const statusData = await response.json();
            console.log(`Status update for job ${doc.id}:`, statusData);
            
            // Update document in state if status changed
            setDocuments(prevDocs => {
              const updatedDocs = { ...prevDocs };
              // Find and update the document across all categories
              Object.keys(updatedDocs).forEach(category => {
                updatedDocs[category] = updatedDocs[category].map(prevDoc => 
                  prevDoc.id === doc.id 
                    ? { ...prevDoc, ...statusData }
                    : prevDoc
                );
              });
              return updatedDocs;
            });
          } else {
            console.error(`Failed to poll status for job ${doc.id}:`, response.status, response.statusText);
          }
        } catch (error) {
          console.error(`Error polling status for job ${doc.id}:`, error);
        }
      }
    }, 10000); // Poll every 10 seconds

    return () => {
      console.log('Cleaning up polling interval');
      clearInterval(pollInterval);
    };
  }, [documents, chatId]);

  const totalDocuments = Object.values(documents).reduce((sum, docs) => sum + docs.length, 0);

  return (
    <>
    <ExpandableSection
      data-testid="documents-section"
      headerText={`Documents (${totalDocuments})`}
      expanded={expanded}
      onChange={({ detail }) => setExpanded(detail.expanded)}
      defaultExpanded={true}
    >
      <div style={{ paddingTop: '16px', position: 'relative' }}>
      {loading && (
        <Box textAlign="center" padding="l">
          <Spinner size="large" />
          <Box variant="p" color="text-body-secondary">Loading documents...</Box>
        </Box>
      )}

      {error && (
        <div style={{ 
          position: 'absolute', 
          top: '10px', 
          right: '10px', 
          zIndex: 1000, 
          maxWidth: '250px',
          backgroundColor: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '6px',
          padding: '8px 12px',
          fontSize: '12px',
          color: '#dc2626',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>{error}</span>
            <button 
              onClick={() => setError(null)}
              style={{ 
                background: 'none', 
                border: 'none', 
                color: '#dc2626', 
                cursor: 'pointer',
                marginLeft: '8px',
                fontSize: '14px'
              }}
            >
              ×
            </button>
          </div>
        </div>
      )}

      {!loading && totalDocuments === 0 && (
        <Box textAlign="center" padding="l">
          <Box variant="p" color="text-body-secondary">
            No documents have been generated for this chat yet.
          </Box>
        </Box>
      )}

      {!loading && totalDocuments > 0 && (
        <SpaceBetween direction="vertical" size="m" style={{ marginTop: '24px' }}>
          {/* Approvals Section - First */}
          <Box style={{ marginBottom: '16px' }}>
            <Approvals 
              chatId={chatId} 
              refreshTrigger={refreshTrigger}
            />
          </Box>
          
          {Object.entries(documents).map(([type, docs]) => (
            <Box key={type} style={{ marginBottom: '16px' }}>
              <Header variant="h4" style={{ marginBottom: '12px' }}>
                {documentTypeNames[type] || type}
              </Header>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '8px', maxWidth: '100%', marginTop: '16px' }}>
                {docs.map((doc) => (
                  <div 
                    key={doc.id} 
                    className="document-tile"
                    data-filename={doc.s3_key ? doc.s3_key.split('/').pop() : 'unknown'}
                    data-version-id={doc.version_id || ''}
                    data-doc-id={doc.id}
                    style={{ 
                      cursor: 'default',
                      border: '1px solid #e9ebed',
                      borderRadius: '12px',
                      backgroundColor: doc.approved ? '#fff' : '#f9f9f9',
                      transition: 'background-color 0.2s',
                      padding: '12px',
                      textAlign: 'center',
                      position: 'relative'
                    }}
                    onMouseEnter={(e) => {
                      const buttons = e.currentTarget.querySelector('.hover-buttons');
                      if (buttons) buttons.style.opacity = '1';
                    }}
                    onMouseLeave={(e) => {
                      const buttons = e.currentTarget.querySelector('.hover-buttons');
                      if (buttons) buttons.style.opacity = '0';
                    }}
                  >
                    <SpaceBetween direction="vertical" size="xs">
                      {(doc.name || (doc.document_type === 'cloudformation_template' && doc.s3_key)) && (
                        <Box variant="small" style={{ fontSize: '11px', fontWeight: 'bold' }}>
                          {doc.name || (doc.s3_key ? doc.s3_key.split('/').pop() : 'Unknown')}
                        </Box>
                      )}
                      
                      {/* Show classification and source for user uploads */}
                      {doc.tool_name === 'user_uploaded' && (
                        <>
                          {doc.document_classification && (
                            <Box variant="small" color="text-body-secondary" style={{ fontSize: '9px', fontStyle: 'italic' }}>
                              {getClassificationDisplayName(doc.document_classification)}
                            </Box>
                          )}
                          <Box variant="small" color="text-body-secondary" style={{ fontSize: '8px' }}>
                            📤 Uploaded
                          </Box>
                        </>
                      )}
                      
                      <div 
                        className="hover-buttons"
                        style={{ 
                          position: 'absolute',
                          top: '0%',
                          left: '0%',
                          width: '100%',
                          height: '100%',
                          display: 'flex', 
                          gap: '8px', 
                          alignItems: 'center',
                          justifyContent: 'center',
                          opacity: '0',
                          backgroundColor: 'rgba(255, 255, 255, 0.4)',
                          borderRadius: '8px',
                          pointerEvents: 'none'
                        }}
                      >
                        {/* Show download button for all documents except calculator links */}
                        {doc.document_type !== 'calculator_link' && (
                          <button
                            onClick={() => {
                              downloadDocument(doc.id, doc.document_type);
                            }}
                            style={{
                              background: 'none',
                              border: 'none',
                              cursor: 'pointer',
                              padding: '8px',
                              borderRadius: '4px',
                              width: canPreviewDocument(doc) ? '25%' : '50%', // Wider when no preview available
                              height: '50%',
                              pointerEvents: 'auto',
                              transition: 'transform 0.1s'
                            }}
                            onMouseEnter={(e) => e.target.style.transform = 'scale(1.3)'}
                            onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
                            title="Download"
                          >
                            <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                              <polyline points="7,10 12,15 17,10"/>
                              <line x1="12" y1="15" x2="12" y2="3"/>
                            </svg>
                          </button>
                        )}
                        
                        {/* Show preview button for all previewable documents */}
                        {canPreviewDocument(doc) && (
                          <button
                            onClick={async () => {
                              if (doc.document_type === 'calculator_link') {
                                // For calculator links, fetch and show live status in modal
                                setStatusModal({ isOpen: true, status: null, loading: true });
                                
                                try {
                                  const response = await fetch(`${API_BASE_URL}/nova/status/${doc.id}?chat_id=${chatId}`, {
                                    credentials: 'include'
                                  });
                                  
                                  if (response.ok) {
                                    const statusData = await response.json();
                                    setStatusModal({ isOpen: true, status: statusData, loading: false });
                                  } else {
                                    setStatusModal({ 
                                      isOpen: true, 
                                      status: { error: `Failed to fetch status for job ${doc.id}` }, 
                                      loading: false 
                                    });
                                  }
                                } catch (error) {
                                  setStatusModal({ 
                                    isOpen: true, 
                                    status: { error: `Error fetching status: ${error.message}` }, 
                                    loading: false 
                                  });
                                }
                              } else {
                                setPreviewModal({ isOpen: true, documentId: doc.id, documentType: doc.document_type });
                              }
                            }}
                            style={{
                              background: 'none',
                              border: 'none',
                              cursor: 'pointer',
                              padding: '8px',
                              borderRadius: '4px',
                              width: '25%',
                              height: '50%',
                              pointerEvents: 'auto',
                              transition: 'transform 0.1s'
                            }}
                            onMouseEnter={(e) => e.target.style.transform = 'scale(1.3)'}
                            onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
                            title="Preview"
                          >
                            <svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                              <circle cx="12" cy="12" r="3"/>
                            </svg>
                          </button>
                        )}
                      </div>
                      
                      <Box variant="small" color="text-body-secondary" style={{ fontSize: '10px' }}>
                        {new Date(doc.created_timestamp).toLocaleDateString('en-US', { 
                          month: 'short', 
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </Box>
                      
                      <Box variant="small" color={doc.approved ? "text-status-success" : "text-body-secondary"} style={{ fontSize: '10px' }}>
                        {doc.approved ? "approved" : "not approved"}
                      </Box>
                      
                      {doc.document_type === 'calculator_link' && (
                        <div style={{ marginTop: '4px' }}>
                          <div style={{
                            width: '100%',
                            height: '3px',
                            backgroundColor: '#e9ebed',
                            borderRadius: '2px',
                            overflow: 'hidden'
                          }}>
                            <div style={{
                              width: `${
                                doc.status === 'failed' && (doc.actions_completed || 0) === 0 && (doc.actions_total || 0) > 0 
                                  ? 15 
                                  : doc.status === 'failed' && (doc.actions_completed || 0) === 0 && (doc.actions_total || 0) === 0
                                  ? 100
                                  : ['pending', 'running'].includes(doc.status) && (doc.actions_completed || 0) === 0 && (doc.actions_total || 0) === 0
                                  ? 15
                                  : ((doc.actions_completed || 0) / (doc.actions_total || 1)) * 100
                              }%`,
                              height: '100%',
                              backgroundColor: doc.status === 'failed' ? 'red' : 
                                               doc.status === 'completed' ? '#037f0c' : '#0972d3',
                              transition: 'width 0.3s ease'
                            }} className={['pending', 'running'].includes(doc.status) ? 'smooth-blinking' : ''} />
                          </div>
                        </div>
                      )}
                    </SpaceBetween>
                  </div>
                ))}
              </div>
            </Box>
          ))}
        </SpaceBetween>
      )}
      </div>
    </ExpandableSection>
    
    <DocumentPreviewModal
      isOpen={previewModal.isOpen}
      onClose={() => setPreviewModal({ isOpen: false, documentId: null, documentType: null })}
      documentId={previewModal.documentId}
      documentType={previewModal.documentType}
      chatId={chatId}
      documents={documents}
    />
    
    <Modal
      onDismiss={() => setStatusModal({ isOpen: false, status: null, loading: false })}
      visible={statusModal.isOpen}
      header="Calculator Link Status"
      size="large"
    >
      <div style={{ width: '90%', margin: '0 auto' }}>
      {statusModal.loading ? (
        <Box textAlign="center">
          <Spinner size="large" />
          <Box variant="p" margin={{ top: "m" }}>Loading status...</Box>
        </Box>
      ) : statusModal.status ? (
        <SpaceBetween direction="vertical" size="m">
          <Box>
            <strong>Job ID:</strong> {statusModal.status.job_id}
          </Box>
          <Box>
            <strong>Status:</strong> <StatusIndicator type={
              statusModal.status.status === 'completed' ? 'success' :
              statusModal.status.status === 'failed' ? 'error' :
              statusModal.status.status === 'running' ? 'in-progress' : 'pending'
            }>{statusModal.status.status}</StatusIndicator>
          </Box>
          {!statusModal.status.error && (
            <Box>
              <strong>Progress:</strong> 
              <Box margin={{ top: "xs" }} style={{ wordBreak: "break-word" }}>
                {statusModal.status.progress || 'No progress info'}
              </Box>
            </Box>
          )}
          <Box>
            <strong>Actions:</strong> {statusModal.status.actions_completed || 0}/{statusModal.status.actions_total || 0}
            <Box margin={{ top: "xs" }}>
              <div style={{
                width: '90%',
                height: '8px',
                backgroundColor: '#e9ebed',
                borderRadius: '4px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${
                    statusModal.status.status === 'failed' && (statusModal.status.actions_completed || 0) === 0 && (statusModal.status.actions_total || 0) > 0 
                      ? 15 
                      : statusModal.status.status === 'failed' && (statusModal.status.actions_completed || 0) === 0 && (statusModal.status.actions_total || 0) === 0
                      ? 100
                      : ['pending', 'running'].includes(statusModal.status.status) && (statusModal.status.actions_completed || 0) === 0 && (statusModal.status.actions_total || 0) === 0
                      ? 15
                      : ((statusModal.status.actions_completed || 0) / (statusModal.status.actions_total || 1)) * 100
                  }%`,
                  height: '100%',
                  backgroundColor: statusModal.status.status === 'failed' ? 'red' : 
                                   statusModal.status.status === 'completed' ? '#037f0c' : '#0972d3',
                  transition: 'width 0.3s ease'
                }} className={['pending', 'running'].includes(statusModal.status.status) ? 'smooth-blinking' : ''} />
              </div>
            </Box>
          </Box>
          {statusModal.status.result && (
            <Box>
              <strong>Result:</strong> 
              <Box margin={{ top: "xs" }}>
                {(() => {
                  // Find the document to check approval status
                  const currentDoc = Object.values(documents).flat().find(d => d.id === statusModal.status.job_id);
                  const isApproved = currentDoc?.approved;
                  
                  if (!isApproved && !isSA) {
                    return <span style={{ color: '#d13212' }}>Document needs to be approved before viewing the link</span>;
                  } else {
                    return (
                      <a href={statusModal.status.result} target="_blank" rel="noopener noreferrer">
                        {statusModal.status.result}
                      </a>
                    );
                  }
                })()}
              </Box>
            </Box>
          )}
          {statusModal.status.error && (
            <Box>
              <strong>Error:</strong>
              <div style={{ marginTop: '8px', color: 'red', wordBreak: "break-word" }}>
                {statusModal.status.error}
              </div>
            </Box>
          )}
        </SpaceBetween>
      ) : null}
      </div>
    </Modal>
    </>
  );
};

export default Documents;
