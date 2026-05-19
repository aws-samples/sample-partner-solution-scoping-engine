import React, { useState, useEffect, useRef } from 'react';
import {
  Modal,
  Box,
  SpaceBetween,
  Button,
  Spinner,
  Alert
} from '@cloudscape-design/components';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import mammoth from 'mammoth';
import { getDocumentCFSignedUrl } from '../services/fileService';
import { API_BASE_URL } from '../config';

const DocumentPreviewModal = ({ isOpen, onClose, documentId, documentType, chatId, documents }) => {
  const [documentUrl, setDocumentUrl] = useState(null);
  const [markdownContent, setMarkdownContent] = useState(null);
  const [yamlContent, setYamlContent] = useState(null);
  const [docxContent, setDocxContent] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Use ref to track abort controller for cleanup
  const abortControllerRef = useRef(null);

  // Clear state when modal closes to ensure fresh data on next open
  useEffect(() => {
    if (!isOpen) {
      console.log('WAFR_PREVIEW_DEBUG: Modal closed, clearing state');
      // Abort any in-flight requests when modal closes
      if (abortControllerRef.current) {
        console.log('WAFR_PREVIEW_DEBUG: Aborting in-flight request');
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      setDocumentUrl(null);
      setMarkdownContent(null);
      setYamlContent(null);
      setDocxContent(null);
      setError(null);
    } else {
      console.log('WAFR_PREVIEW_DEBUG: Modal opened', { documentId, documentType, chatId });
    }
  }, [isOpen]);

  // Load document when modal opens - always fetch fresh signed URL
  useEffect(() => {
    if (isOpen && documentId) {
      loadDocument();
    }
    
    // Cleanup on unmount
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [isOpen, documentId]);

  const loadDocument = async () => {
    console.log('WAFR_PREVIEW_DEBUG: loadDocument called', { 
      documentId, 
      documentType, 
      chatId,
      timestamp: new Date().toISOString()
    });
    
    // Abort any previous request
    if (abortControllerRef.current) {
      console.log('WAFR_PREVIEW_DEBUG: Aborting previous request');
      abortControllerRef.current.abort();
    }
    
    // Create new abort controller for this request
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;
    
    setLoading(true);
    setError(null);
    setMarkdownContent(null);
    setYamlContent(null);
    setDocxContent(null);
    try {
      const doc = Object.values(documents).flat().find(d => d.id === documentId);
      
      console.log('WAFR_PREVIEW_DEBUG: Found document:', doc ? {
        id: doc.id,
        s3_key: doc.s3_key,
        version_id: doc.version_id,
        original_filename: doc.original_filename
      } : 'NOT FOUND');
      
      if (!doc) {
        setError('Document not found');
        return;
      }

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
            const parts = doc.s3_key.split('/');
            if (parts.length > 1 && parts[0] === chatId) {
              relativePath = parts.slice(1).join('/');
            } else {
              relativePath = doc.s3_key;
            }
          }
          
          const response = await getDocumentCFSignedUrl(chatId, relativePath, doc.version_id);
          
          if (response && response.url) {
            setDocumentUrl(response.url);
            
            // For WAFR assessments (DOCX files), fetch and convert to HTML
            if (documentType === 'wafr_assessment') {
              try {
                // Use the URL directly - cache busting is already handled by the backend
                const fetchUrl = response.url;
                
                // Use no-store cache to prevent browser caching
                // Add credentials: 'omit' to avoid CORS preflight issues with CloudFront
                const docxResponse = await fetch(fetchUrl, {
                  cache: 'no-store',
                  mode: 'cors',
                  credentials: 'omit',  // CloudFront signed URLs don't need credentials
                  signal  // Use abort signal for cleanup
                });
                
                console.log('WAFR_PREVIEW_DEBUG: Fetch response received:', {
                  ok: docxResponse.ok,
                  status: docxResponse.status,
                  statusText: docxResponse.statusText,
                  headers: Object.fromEntries(docxResponse.headers.entries())
                });
                
                if (!docxResponse.ok) {
                  setError(`Failed to load document: ${docxResponse.status} ${docxResponse.statusText}`);
                  return;
                }
                
                const arrayBuffer = await docxResponse.arrayBuffer();
                
                const result = await mammoth.convertToHtml({ arrayBuffer });
                setDocxContent(result.value);
              } catch (docxError) {
                setError(`Failed to load document preview: ${docxError.message}`);
              }
            }
            return;
          } else {
            setError('Failed to get document URL');
            return;
          }
        } else {
          setError('Document path not found');
          return;
        }
      }
      
      // For other documents, construct the CloudFront URL directly using s3_key
      if (doc.s3_key) {
        const response = await getDocumentCFSignedUrl(chatId, doc.s3_key, doc.version_id);
        
        if (response && response.url) {
          setDocumentUrl(response.url);
          
          // Determine file type from URL or document metadata
          const filename = doc.original_filename?.toLowerCase() || response.url.toLowerCase();
          
          // If it's a markdown file, fetch the content
          if (filename.includes('.md') || documentType === 'funding_document') {
            const markdownResponse = await fetch(response.url);
            const markdownText = await markdownResponse.text();
            setMarkdownContent(markdownText);
          }
          
          // If it's a YAML file or CloudFormation template, fetch the content
          else if (filename.includes('.yaml') || filename.includes('.yml') || 
              documentType === 'cloudformation_template') {
            const yamlResponse = await fetch(response.url);
            const yamlText = await yamlResponse.text();
            setYamlContent(yamlText);
          }
          
          // If it's a text file, fetch the content and display as plain text
          else if (filename.includes('.txt') || filename.includes('.json') || filename.includes('.csv') ||
                   filename.includes('.xml') || filename.includes('.html') || filename.includes('.htm')) {
            const textResponse = await fetch(response.url);
            const textContent = await textResponse.text();
            setYamlContent(textContent); // Reuse yamlContent for plain text display
          }
          
          // If it's a DOCX file, fetch and convert to HTML
          else if (filename.includes('.docx') || documentType === 'sow_document' || documentType === 'wafr_assessment') {
            // Use the URL directly - cache busting is already handled by the backend
            const docxResponse = await fetch(response.url, {
              cache: 'no-store',
              mode: 'cors'
            });
            
            if (!docxResponse.ok) {
              throw new Error(`Failed to fetch DOCX: ${docxResponse.status} ${docxResponse.statusText}`);
            }
            
            const arrayBuffer = await docxResponse.arrayBuffer();
            const result = await mammoth.convertToHtml({ arrayBuffer });
            setDocxContent(result.value);
          }
        } else {
          setError('Failed to get document URL');
        }
      } else {
        setError('Document S3 key not found');
      }
    } catch (err) {
      // Don't show error if request was aborted
      if (err.name === 'AbortError') {
        console.log('WAFR_PREVIEW_DEBUG: Request was aborted (outer catch)');
        return;
      }
      console.error('WAFR_PREVIEW_DEBUG: loadDocument error:', err);
      setError('Failed to load document preview');
    } finally {
      setLoading(false);
    }
  };

  const renderDocumentContent = () => {
    if (loading) {
      return (
        <Box textAlign="center" padding="l">
          <Spinner size="large" />
          <Box variant="p" color="text-body-secondary">Loading document...</Box>
        </Box>
      );
    }

    if (error) {
      return <Alert type="error">{error}</Alert>;
    }

    if (!documentUrl) {
      return (
        <Box textAlign="center" padding="l">
          <Box variant="p" color="text-body-secondary">File type not supported for preview</Box>
        </Box>
      );
    }

    // For DOCX files, render the converted HTML content
    if (docxContent) {
      return (
        <div style={{ 
          textAlign: 'left',
          padding: '20px',
          backgroundColor: 'white',
          borderRadius: '4px',
          maxHeight: '70vh',
          overflow: 'auto'
        }}>
          <div 
            dangerouslySetInnerHTML={{ __html: docxContent }}
            style={{
              userSelect: 'none',
              WebkitUserSelect: 'none',
              MozUserSelect: 'none',
              msUserSelect: 'none'
            }}
          />
        </div>
      );
    }

    // For YAML files, render the content as formatted text
    if (yamlContent) {
      return (
        <div style={{ 
          textAlign: 'left',
          padding: '20px',
          backgroundColor: 'white',
          borderRadius: '4px',
          maxHeight: '70vh',
          overflow: 'auto'
        }}>
          <pre style={{ 
            whiteSpace: 'pre-wrap',
            fontFamily: 'monospace',
            fontSize: '14px',
            lineHeight: '1.5',
            margin: 0
          }}>
            {yamlContent}
          </pre>
        </div>
      );
    }

    // For markdown files, render the content inline
    if (markdownContent) {
      return (
        <div style={{ 
          textAlign: 'left',
          padding: '20px',
          backgroundColor: 'white',
          borderRadius: '4px',
          maxHeight: '70vh',
          overflow: 'auto'
        }}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              table: ({ children }) => (
                <table style={{ 
                  borderCollapse: 'collapse', 
                  width: '100%', 
                  marginBottom: '16px',
                  border: '1px solid #ddd'
                }}>
                  {children}
                </table>
              ),
              th: ({ children }) => (
                <th style={{ 
                  border: '1px solid #ddd', 
                  padding: '8px 12px', 
                  backgroundColor: '#f5f5f5',
                  fontWeight: 'bold',
                  textAlign: 'left'
                }}>
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td style={{ 
                  border: '1px solid #ddd', 
                  padding: '8px 12px'
                }}>
                  {children}
                </td>
              )
            }}
          >
            {markdownContent}
          </ReactMarkdown>
        </div>
      );
    }

    // Determine file type from URL or document metadata
    const doc = Object.values(documents).flat().find(d => d.id === documentId);
    const filename = doc?.original_filename?.toLowerCase() || documentUrl?.toLowerCase() || '';
    
    // Render based on document type and file extension
    console.log('WAFR Render Debug:', { documentType, filename, documentUrl });
    if (documentType === 'diagram' || filename.includes('.png') || filename.includes('.jpg') || 
        filename.includes('.jpeg') || filename.includes('.gif') || filename.includes('.svg')) {
      console.log('WAFR Rendering image with URL:', documentUrl);
      return (
        <img 
          src={documentUrl} 
          alt="Document preview"
          style={{ 
            maxWidth: '100%', 
            maxHeight: '70vh',
            userSelect: 'none',
            pointerEvents: 'none'
          }}
          onLoad={() => console.log('WAFR Image loaded successfully')}
          onError={(e) => console.error('WAFR Image load error:', e)}
        />
      );
    }

    // For PDFs and other documents, use iframe with restrictions
    return (
      <iframe
        src={documentUrl}
        style={{
          width: '100%',
          height: '70vh',
          border: 'none',
          userSelect: 'none',
          pointerEvents: 'none'
        }}
        title="Document preview"
      />
    );
  };

  return (
    <Modal
      visible={isOpen}
      onDismiss={onClose}
      header="Document Preview"
      size="large"
      footer={
        <Box float="right">
          <Button onClick={onClose}>Close</Button>
        </Box>
      }
    >
      <div style={{ 
        margin: '-20px',
        padding: '20px',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        userSelect: 'none',
        WebkitUserSelect: 'none',
        MozUserSelect: 'none',
        msUserSelect: 'none'
      }}>
        <div style={{ width: '90%' }}>
          {renderDocumentContent()}
        </div>
      </div>
    </Modal>
  );
};

export default DocumentPreviewModal;
