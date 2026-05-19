import React from 'react';
import {
  Modal,
  Box,
  SpaceBetween,
  Button,
  Header
} from '@cloudscape-design/components';

const ApprovalDetailsModal = ({ isOpen, onClose, approval, documents }) => {
  if (!approval) return null;

  const getDocumentInfo = (docId) => {
    if (!documents) return { name: docId, size: 'Unknown', type: 'Unknown' };
    
    // Find the document directly by ID in the documents object
    const doc = documents[docId];
    if (!doc) return { name: docId, size: 'Unknown', type: 'Unknown' };
    
    // Get readable name based on document type
    let name = doc.name || 'Unnamed Document';
    if (doc.document_type === 'diagram') name = 'Architecture Diagram';
    else if (doc.document_type === 'pricing_report') name = 'Pricing Report';
    else if (doc.document_type === 'sow_document') name = 'SOW Document';
    else if (doc.document_type === 'calculator_link') name = 'Pricing Calculator Link';
    else if (doc.document_type === 'cloudformation_template') {
      const filename = doc.s3_key ? doc.s3_key.split('/').pop() : 'template';
      name = `CFN: ${filename}`;
    }
    else if (doc.document_type === 'funding_document') name = 'Funding Document';
    
    // Format file size
    const formatSize = (bytes) => {
      if (!bytes || bytes === 0) return 'Unknown';
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(1024));
      return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    };
    
    return {
      name,
      size: doc.document_type === 'calculator_link' ? null : formatSize(doc.file_size),
      createdDate: doc.created_timestamp ? new Date(doc.created_timestamp).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      }) : 'Unknown'
    };
  };

  return (
    <Modal
      visible={isOpen}
      onDismiss={onClose}
      header="Approval Details"
      size="large"
      footer={
        <Box float="right">
          <Button variant="primary" onClick={onClose}>Close</Button>
        </Box>
      }
    >
      <div style={{ width: '90%', margin: '0 auto' }}>
        <SpaceBetween direction="vertical" size="l">
        <Box padding="s" style={{ 
          backgroundColor: '#f0f8ff', 
          borderRadius: '8px',
          border: '1px solid #d1ecf1'
        }}>
          <SpaceBetween direction="vertical" size="s">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Box variant="h3" style={{ margin: 0, color: '#0066cc' }}>
                Approval #{approval.approval_id?.substring(0, 8)}
              </Box>
              <Box style={{ 
                backgroundColor: '#28a745', 
                color: 'white', 
                padding: '4px 12px', 
                borderRadius: '16px',
                fontSize: '12px',
                fontWeight: 'bold'
              }}>
                APPROVED
              </Box>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <Box>
                <Box variant="small" style={{ fontWeight: 'bold', color: '#666' }}>Approved by</Box>
                <Box style={{ fontSize: '14px' }}>{approval.approved_by}</Box>
              </Box>
              <Box>
                <Box variant="small" style={{ fontWeight: 'bold', color: '#666' }}>Date & Time</Box>
                <Box style={{ fontSize: '14px' }}>{new Date(approval.approved_timestamp).toLocaleString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })}</Box>
              </Box>
            </div>
            
            {approval.comment && (
              <Box>
                <Box variant="small" style={{ fontWeight: 'bold', color: '#666' }}>Comment</Box>
                <Box style={{ 
                  fontSize: '14px', 
                  fontStyle: 'italic',
                  backgroundColor: 'white',
                  padding: '8px',
                  borderRadius: '4px',
                  border: '1px solid #e9ebed'
                }}>
                  "{approval.comment}"
                </Box>
              </Box>
            )}
          </SpaceBetween>
        </Box>

        <Box>
          <Header variant="h3" style={{ marginBottom: '12px' }}>
            Approved Documents ({approval.document_ids?.length || 0})
          </Header>
          <div style={{ display: 'grid', gap: '8px' }}>
            {approval.document_ids?.map((docId, index) => {
              const docInfo = getDocumentInfo(docId);
              return (
                <div
                  key={index} 
                  style={{ 
                    backgroundColor: 'white', 
                    borderRadius: '8px',
                    border: '1px solid #e9ebed',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    padding: '16px'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#f8f9fa';
                    e.currentTarget.style.transform = 'translateY(-1px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'white';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}
                  onClick={() => {
                    // Close modal first
                    onClose();
                    
                    // Find the document and scroll to it
                    const doc = documents[docId];
                    if (doc) {
                      if (doc.document_type === 'calculator_link') {
                        // For calculator links, use the document ID directly
                        if (window.scrollToDocument) {
                          window.scrollToDocument('calculator_link', docId, '', docId);
                        }
                      } else if (doc.s3_key) {
                        // For other documents, use the existing logic
                        const fileName = doc.s3_key.split('/').pop();
                        const documentType = doc.document_type || 'unknown';
                        const versionId = doc.version_id || '';
                        
                        if (window.scrollToDocument) {
                          window.scrollToDocument(documentType, fileName, versionId);
                        }
                      }
                    }
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box style={{ fontWeight: 'bold', fontSize: '14px' }}>{docInfo.name}</Box>
                    {docInfo.size && (
                      <Box style={{ 
                        backgroundColor: '#f8f9fa', 
                        padding: '2px 8px', 
                        borderRadius: '12px',
                        fontSize: '11px',
                        color: '#666'
                      }}>
                        {docInfo.size}
                      </Box>
                    )}
                  </div>
                  <Box style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                    Created: {docInfo.createdDate}
                  </Box>
                </div>
              );
            }) || (
              <Box textAlign="center" padding="l" style={{ color: '#666', fontStyle: 'italic' }}>
                No documents specified
              </Box>
            )}
          </div>
        </Box>
      </SpaceBetween>
      </div>
    </Modal>
  );
};

export default ApprovalDetailsModal;
