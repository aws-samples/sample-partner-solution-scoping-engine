import React, { useState, useEffect } from 'react';
import { Modal, Box, Button, SpaceBetween, Input, Alert, Spinner } from '@cloudscape-design/components';
import { getDocumentCFSignedUrl } from '../../services/fileService';

const SAReviewCommentModal = ({ visible, onDismiss, onConfirm, action, loading, chatId }) => {
  const [comment, setComment] = useState('');
  const [documentsToApprove, setDocumentsToApprove] = useState([]);
  const [loadingDocuments, setLoadingDocuments] = useState(false);

  useEffect(() => {
    if (visible && (action === 'mark_ready' || action === 'complete_no_changes') && chatId) {
      fetchDocumentsToApprove();
    }
  }, [visible, action, chatId]);

  const handleRemoveDocument = (indexToRemove) => {
    const updatedDocs = documentsToApprove.filter((_, index) => index !== indexToRemove);
    setDocumentsToApprove(updatedDocs);
  };

  const handleDocumentClick = async (doc) => {
    try {
      // Extract S3 key from the S3 URL
      const s3Key = doc.url.split('/').slice(3).join('/').split('?')[0]; // Remove domain and query params
      const versionId = doc.url.includes('versionId=') ? doc.url.split('versionId=')[1] : null;
      
      // Get CloudFront signed URL
      const cfResponse = await getDocumentCFSignedUrl(chatId, s3Key, versionId);
      window.open(cfResponse.url, '_blank');
    } catch (error) {
      console.error('Error getting CloudFront URL:', error);
      // Fallback to original S3 URL
      window.open(doc.url, '_blank');
    }
  };

  const getDocumentDisplayName = (docType, docName) => {
    // For CloudFormation templates, show "CFN: filename"
    if (docType === 'cloudformation_template') {
      return docName ? `CFN: ${docName}` : 'CloudFormation Template';
    }
    
    // For other types, use friendly names
    const typeMap = {
      'sow_document': 'SOW Document',
      'diagram': 'Architecture Diagram', 
      'pricing_report': 'Pricing Report',
      'funding_document': 'Funding Document'
    };
    
    return typeMap[docType] || docType;
  };

  const fetchDocumentsToApprove = async () => {
    setLoadingDocuments(true);
    try {
      const response = await fetch(`/api/sa-review/preview-approval/${chatId}`, {
        credentials: 'include'
      });
      const data = await response.json();
      if (data.success) {
        console.log('Documents from API:', data.documents);
        setDocumentsToApprove(data.documents || []);
      }
    } catch (error) {
      console.error('Error fetching documents to approve:', error);
    } finally {
      setLoadingDocuments(false);
    }
  };

  const handleConfirm = () => {
    // Pass the list of document IDs to approve along with the comment
    const approvalData = {
      comment: comment,
      documentIds: documentsToApprove.map(doc => doc.doc_id)
    };
    onConfirm(approvalData);
    setComment('');
  };

  const handleDismiss = () => {
    onDismiss();
    setComment('');
    setDocumentsToApprove([]);
  };

  const getActionText = () => {
    switch (action) {
      case 'mark_ready': return 'Mark Ready for User';
      case 'complete_no_changes': return 'Approve As-Is';
      case 'reject': return 'Reject';
      case 'reassign': return 'Reassign';
      case 'cancel': return 'Submit';
      case 'request': return 'Request Review';
      default: return 'Confirm Action';
    }
  };

  const showDocumentApproval = action === 'mark_ready' || action === 'complete_no_changes';

  return (
    <>
      <style>
        {`
          .document-row-hover:hover {
            background-color: #e8e8e8 !important;
          }
        `}
      </style>
      <Modal
      onDismiss={handleDismiss}
      visible={visible}
      header={`${getActionText()} - Add Comment`}
      closeAriaLabel="Close modal"
      size="medium"
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={handleDismiss}>
              Close
            </Button>
            <Button 
              variant="primary" 
              onClick={handleConfirm}
              loading={loading}
            >
              {getActionText()}
            </Button>
          </SpaceBetween>
        </Box>
      }
    >
      <SpaceBetween size="m">
        {showDocumentApproval && (
          <div>
            <h4>Documents to be approved:</h4>
            {loadingDocuments ? (
              <Spinner />
            ) : documentsToApprove.length > 0 ? (
              <Box>
                {documentsToApprove.map((doc, index) => (
                  <div 
                    key={index} 
                    style={{ 
                      marginBottom: '8px', 
                      padding: '8px', 
                      backgroundColor: '#f5f5f5', 
                      borderRadius: '4px', 
                      width: '90%', 
                      cursor: 'pointer',
                      border: '1px solid transparent',
                      transition: 'background-color 0.2s ease',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}
                    className="document-row-hover"
                    onClick={() => handleDocumentClick(doc)}
                  >
                    <div>
                      <strong>{getDocumentDisplayName(doc.type, doc.name)}</strong>
                      <div style={{ fontSize: '12px', color: '#666' }}>
                        Size: {doc.file_size ? Math.round(doc.file_size / 1024) : 'Unknown'} KB | Created: {new Date(doc.created_timestamp).toLocaleString()}
                      </div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveDocument(index);
                      }}
                      style={{
                        background: 'none',
                        border: 'none',
                        fontSize: '16px',
                        cursor: 'pointer',
                        color: '#666',
                        padding: '4px',
                        borderRadius: '2px'
                      }}
                      onMouseEnter={(e) => e.target.style.color = '#d32f2f'}
                      onMouseLeave={(e) => e.target.style.color = '#666'}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </Box>
            ) : (
              <div style={{ width: '90%' }}>
                <Alert type="info">No documents found to approve.</Alert>
              </div>
            )}
          </div>
        )}
        
        <div>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Enter your comment here (optional)..."
            rows={4}
            style={{
              width: '90%',
              resize: 'none',
              padding: '8px',
              border: '1px solid #ccc',
              borderRadius: '4px',
              fontFamily: 'inherit'
            }}
          />
        </div>
      </SpaceBetween>
    </Modal>
    </>
  );
};

export default SAReviewCommentModal;
