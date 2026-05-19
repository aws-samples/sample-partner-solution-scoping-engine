import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Header,
  SpaceBetween,
  Textarea,
  Button,
  Box,
  Alert,
  StatusIndicator,
  Icon,
  Grid,
  Spinner,
  Link,
  ButtonGroup,
  Modal,
  Input
} from '@cloudscape-design/components';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { sendMessage, getChatSession, updateChatName } from '../services/chatService';
import { getDocumentCFSignedUrl, getAllowedExtensions, validateFileExtensions } from '../services/fileService';
import { API_BASE_URL } from '../config';
import ChatToolbar from '../components/ChatToolbar';
import ConversationStage from '../components/ConversationStage';
import { FileClassificationUtils } from '../services/fileService.js';
import SANotification from '../components/SANotification';
import IsolatedChatInput from '../components/IsolatedChatInput';
import Documents from '../components/Documents';
import POCFundingGuidance from '../components/POCFundingGuidance';
import WAFRGuidance from '../components/WAFRGuidance';

// Add CSS for blinking animation
const blinkingStyles = `
  @keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0.3; }
  }
`;

// Inject styles
if (!document.getElementById('blinking-styles')) {
  const style = document.createElement('style');
  style.id = 'blinking-styles';
  style.textContent = blinkingStyles;
  document.head.appendChild(style);
}

/**
 * Feedback actions for messages
 */
const FeedbackActions = ({ contentToCopy }) => {
  return (
    <div style={{ position: 'absolute', bottom: '8px', right: '8px' }}>
      <ButtonGroup
        ariaLabel="Chat actions"
        variant="icon"
        onItemClick={({ detail }) => {
          if (detail.id === 'copy' && navigator.clipboard) {
            navigator.clipboard.writeText(contentToCopy)
              .catch(error => console.log('Failed to copy', error.message));
          }
        }}
        items={[
          {
            type: 'icon-button',
            id: 'copy',
            iconName: 'copy',
            text: 'Copy',
            popoverFeedback: <StatusIndicator type="success">Message copied</StatusIndicator>,
          },
        ]}
      />
    </div>
  );
};

/**
 * Support prompt items
 */
const supportPromptItems = [
  {
    text: 'Tell me more about this',
    id: 'more-info',
  },
  {
    text: 'How can I improve this?',
    id: 'improve',
  },
];

/**
 * Checks if a string contains an image URL pattern (S3 or regular URLs)
 * @param {string} content - The content to check
 * @returns {boolean} - True if the content contains an image URL pattern
 */
/**
 * Component to display citations from documents
 */
const MessageCitations = ({ citations }) => {
  if (!citations || citations.length === 0) return null;

  return (
    <Box margin={{ top: 's' }}>
      <SpaceBetween direction="vertical" size="xs">
        <Box fontWeight="bold" color="text-body-secondary">
          <Icon name="file-open" size="small" /> Sources ({citations.length})
        </Box>
        <div style={{
          backgroundColor: '#f8f9fa',
          padding: '12px',
          borderRadius: '8px',
          border: '1px solid #e9ecef'
        }}>
          <SpaceBetween direction="vertical" size="xs">
            {citations.map((citation, index) => {
              const title = citation.title || `Document ${index + 1}`;
              const location = citation.location;
              const sourceContent = citation.sourceContent;

              return (
                <div key={index} style={{
                  padding: '8px',
                  backgroundColor: 'white',
                  borderRadius: '4px',
                  border: '1px solid #dee2e6'
                }}>
                  <SpaceBetween direction="vertical" size="xxs">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Box fontWeight="bold" fontSize="body-s" color="text-body-primary">
                        {index + 1}. {title}
                      </Box>
                      {location && (
                        <Box fontSize="body-s" color="text-body-secondary">
                          {location.page && `(Page ${location.page})`}
                          {location.position && `(Position ${location.position})`}
                          {location.chunk && `(Section ${location.chunk})`}
                        </Box>
                      )}
                    </div>
                    {sourceContent && sourceContent.length > 0 && (
                      <Box fontSize="body-s" color="text-body-secondary" fontStyle="italic">
                        "{sourceContent[0].length > 150 ? sourceContent[0].substring(0, 150) + '...' : sourceContent[0]}"
                      </Box>
                    )}
                  </SpaceBetween>
                </div>
              );
            })}
          </SpaceBetween>
        </div>
      </SpaceBetween>
    </Box>
  );
};

/**
 * Component to display inline images from uploaded files
 */
const InlineImageFile = ({ file, chatId }) => {
  const [imageUrl, setImageUrl] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Memoize the file key to prevent unnecessary re-renders
  const fileKey = useMemo(() => {
    return file?.s3_key && chatId ? `${chatId}-${file.s3_key}-${file.version_id || ''}` : null;
  }, [file?.s3_key, file?.version_id, chatId]);

  useEffect(() => {
    const loadImage = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Validate required props
        if (!file) {
          throw new Error('No file provided');
        }
        if (!chatId) {
          throw new Error('No chatId provided');
        }
        if (!file.s3_key) {
          throw new Error('File missing s3_key');
        }

        // Use the same logic as MessageFiles component for getting signed URLs
        const fileName = file.s3_key.split('/').pop();

        let response;

        // Use the general document route for all files (simpler and more reliable)
        let relativePath = file.s3_key;
        if (file.s3_key.startsWith(`${chatId}/`)) {
          relativePath = file.s3_key.substring(`${chatId}/`.length);
          console.debug(`InlineImageFile - Removed full chatId prefix. Original: ${file.s3_key}, Relative: ${relativePath}`);
        } else {
          // Also check for truncated chat ID patterns (common issue with CloudFormation files)
          // Match patterns like "af-d615-4cd9-a6ff-d2e8872572a3/" which are truncated UUIDs
          const truncatedUuidPattern = /^[0-9a-f]{2,8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\//;
          if (truncatedUuidPattern.test(file.s3_key)) {
            // Find the first slash and remove everything before it
            const firstSlashIndex = file.s3_key.indexOf('/');
            if (firstSlashIndex > 0) {
              relativePath = file.s3_key.substring(firstSlashIndex + 1);
              console.debug(`InlineImageFile - Removed truncated UUID prefix. Original: ${file.s3_key}, Relative: ${relativePath}`);
            }
          }
        }

        console.debug(`InlineImageFile - Using getDocumentCFSignedUrl with relativePath: ${relativePath}`);
        response = await getDocumentCFSignedUrl(chatId, relativePath, file.version_id);
        console.debug(`InlineImageFile - getDocumentCFSignedUrl response:`, response);

        if (!response || !response.url) {
          throw new Error('No signed URL received from backend');
        }

        console.debug(`InlineImageFile - Final signed URL: ${response.url}`);
        setImageUrl(response.url);
      } catch (err) {
        console.error('InlineImageFile - Error loading image:', err);
        setError(err.message || 'Unknown error occurred');
      } finally {
        setIsLoading(false);
      }
    };

    // Only load if we have the required data
    if (file && chatId && file.s3_key) {
      loadImage();
    } else {
      console.warn('InlineImageFile - Missing required props:', { file, chatId });
      setError('Missing required file data');
      setIsLoading(false);
    }
  }, [fileKey]);

  // Helper function to check if this is an uploaded image (vs generated)
  const isUploadedImage = (file) => {
    // Check if the s3_key contains '/uploads/' indicating it's an uploaded file
    return file.s3_key && file.s3_key.includes('/uploads/');
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Spinner size="normal" />
        <span>Loading image...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Alert type="error" header="Image Load Error">
        <div>
          <strong>File:</strong> {file.original_filename || file.s3_key.split('/').pop()}<br />
          <strong>S3 Key:</strong> {file.s3_key}<br />
          <strong>Version ID:</strong> {file.version_id || 'None'}<br />
          <strong>Error:</strong> {error}
        </div>
      </Alert>
    );
  }

  // If this is an uploaded image, show it inline
  if (isUploadedImage(file)) {
    return (
      <div>
        <Box fontSize="body-s" color="text-body-secondary" margin={{ bottom: 'xs' }}>
          {file.original_filename || file.s3_key.split('/').pop()}
        </Box>
        <img
          src={imageUrl}
          alt={file.original_filename || 'Uploaded image'}
          style={{
            maxWidth: '60%',
            height: 'auto',
            borderRadius: '8px',
            margin: '10px 0',
            display: 'block'
          }}
          onError={(e) => {
            console.error('InlineImageFile - Image failed to load from URL:', imageUrl);
            console.error('InlineImageFile - Image error event:', e);
            setError(`Failed to display image from URL: ${imageUrl}`);
          }}
          onLoad={() => {
            console.debug('InlineImageFile - Image loaded successfully:', imageUrl);
          }}
        />
      </div>
    );
  }

  // If this is a generated image, show only as a download link
  return (
    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '5px' }}>
      <Button
        variant="link"
        iconName="file-open"
        onClick={() => {
          if (imageUrl) {
            window.open(imageUrl, '_blank');
          }
        }}
      >
        {file.original_filename || file.s3_key.split('/').pop()}
      </Button>
    </div>
  );
};

/**
 * Component to display files attached to messages
 */
const MessageFiles = React.memo(({ files, chatId }) => {
  const [downloadStatus, setDownloadStatus] = useState({});
  const [isProcessing, setIsProcessing] = useState(false);

  // Add debug logging to track re-renders
  console.log(`🔄 MessageFiles component rendered for chatId: ${chatId}, files count: ${files?.length || 0}`);

  // Add error handling for invalid props
  if (!files || files.length === 0) return null;
  if (!chatId) {
    console.error('MessageFiles - No chatId provided');
    return null;
  }

  // Memoize file processing to prevent unnecessary re-computation
  const validFiles = useMemo(() => {
    return files.filter(file => {
      const isValid = file && (file.s3_key || file.s3_url || file.name);
      if (!isValid) {
        console.warn('MessageFiles - Invalid file object:', file);
      }
      return isValid;
    });
  }, [files]);

  if (validFiles.length === 0) {
    console.warn('MessageFiles - No valid files found');
    return null;
  }

  // Helper function to check if file is an image
  const isImageFile = useCallback((file) => {
    if (file.type && file.type.startsWith('image/')) return true;
    const fileName = file.original_filename || (file.s3_key ? file.s3_key.split('/').pop() : file.name);
    return /\.(jpg|jpeg|png|gif|bmp|svg|webp)$/i.test(fileName);
  }, []);

  // Helper function to check if this is an uploaded image (vs generated)
  const isUploadedImage = useCallback((file) => {
    // Check if the s3_key contains '/uploads/' indicating it's an uploaded file
    return file.s3_key && file.s3_key.includes('/uploads/');
  }, []);

  // Memoize file categorization to prevent unnecessary re-computation
  const { uploadedImageFiles, generatedImageFiles, otherFiles } = useMemo(() => {
    const uploaded = validFiles.filter(file => isImageFile(file) && isUploadedImage(file));
    const generated = validFiles.filter(file => isImageFile(file) && !isUploadedImage(file));
    const other = validFiles.filter(file => !isImageFile(file));
    
    return {
      uploadedImageFiles: uploaded,
      generatedImageFiles: generated,
      otherFiles: other
    };
  }, [validFiles, isImageFile, isUploadedImage]);

  const handleFileDownload = async (s3Key, versionId = null) => {
    try {
      // Extract file name from s3Key (format: <keypath>/<file_name>.<extension>)
      console.log(`handleFileDownload - s3Key: ${s3Key}`)
      console.log(`handleFileDownload - versionId: ${versionId}`)
      console.log(`handleFileDownload - contains /uploads/: ${s3Key.includes('/uploads/')}`)
      const keyParts = s3Key.split('/');
      const fileName = keyParts[keyParts.length - 1];

      setDownloadStatus(prev => ({ ...prev, [fileName]: 'loading' }));

      // Get signed URL for download using s3_key and version_id if available
      let response;

      // Check if this is an uploaded file (s3Key contains "/uploads/")
      if (s3Key.includes('/uploads/')) {
        // Try CloudFront first, then fallback to S3 if it fails
        try {
          // Extract just the filename from the full s3Key path
          const fileName = s3Key.split('/').pop(); // Get the last part (filename)
          let uploadsUrl = `${API_BASE_URL}/chats/${chatId}/documents/uploads/cf_signedurl/${fileName}`;

          // Add version_id if provided
          if (versionId) {
            uploadsUrl += `?version_id=${encodeURIComponent(versionId)}`;
          }

          console.debug(`Trying CloudFront uploads-specific URL: ${uploadsUrl}`);
          console.debug(`Extracted filename from s3Key "${s3Key}": ${fileName}`);

          const uploadsResponse = await fetch(uploadsUrl);
          if (!uploadsResponse.ok) {
            throw new Error(`CloudFront request failed: ${uploadsResponse.status}`);
          }
          response = await uploadsResponse.json();

          // Test if the CloudFront URL actually works by making a HEAD request
          const testResponse = await fetch(response.url, { method: 'HEAD' });
          if (!testResponse.ok) {
            throw new Error(`CloudFront URL test failed: ${testResponse.status}`);
          }

          console.debug(`CloudFront URL working for uploaded file: ${response.url}`);
        } catch (cfError) {
          console.warn(`CloudFront failed for uploaded file, trying S3 fallback:`, cfError);

          // Fallback to S3 signed URL for uploaded files
          try {
            const s3Url = `${API_BASE_URL}/chats/${chatId}/documents/diagram/s3_signedurl/${s3Key.split('/').pop()}`;
            console.debug(`Trying S3 fallback URL: ${s3Url}`);

            const s3Response = await fetch(s3Url);
            response = await s3Response.json();
            console.debug(`S3 fallback successful for uploaded file: ${response.url}`);
          } catch (s3Error) {
            console.error(`Both CloudFront and S3 failed for uploaded file:`, s3Error);
            throw s3Error;
          }
        }
      } else {
        // Use the general route for other files (diagrams, etc.)
        console.debug(`Using general route for s3Key: ${s3Key}`);

        // Check if s3Key contains the chatId prefix and remove it to avoid duplication
        let relativePath = s3Key;
        if (s3Key.startsWith(`${chatId}/`)) {
          relativePath = s3Key.substring(`${chatId}/`.length);
          console.debug(`MessageFiles - Removed full chatId prefix from s3Key. Original: ${s3Key}, Relative: ${relativePath}`);
        } else {
          // Also check for truncated chat ID patterns (common issue with CloudFormation files)
          // Match patterns like "af-d615-4cd9-a6ff-d2e8872572a3/" which are truncated UUIDs
          const truncatedUuidPattern = /^[0-9a-f]{2,8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\//;
          if (truncatedUuidPattern.test(s3Key)) {
            // Find the first slash and remove everything before it
            const firstSlashIndex = s3Key.indexOf('/');
            if (firstSlashIndex > 0) {
              relativePath = s3Key.substring(firstSlashIndex + 1);
              console.debug(`MessageFiles - Removed truncated UUID prefix from s3Key. Original: ${s3Key}, Relative: ${relativePath}`);
            }
          }
        }

        response = await getDocumentCFSignedUrl(chatId, relativePath, versionId);
      }

      // Method 1: Try to open in new tab first
      try {
        const link = document.createElement('a');
        link.href = response.url;
        link.target = '_blank';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        setDownloadStatus(prev => ({ ...prev, [fileName]: 'success' }));
      } catch (linkError) {
        console.error('Error opening in new tab, falling back to download:', linkError);

        // Fallback: Use fetch to get the file and force download
        try {
          const fileResponse = await fetch(response.url);
          const blob = await fileResponse.blob();
          const url = window.URL.createObjectURL(blob);

          const link = document.createElement('a');
          link.href = url;
          link.download = fileName;
          document.body.appendChild(link);
          link.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(link);

          setDownloadStatus(prev => ({ ...prev, [fileName]: 'success' }));
        } catch (downloadError) {
          console.error('Error with fallback download:', downloadError);
          throw downloadError;
        }
      }

      // Reset status after 3 seconds
      setTimeout(() => {
        setDownloadStatus(prev => {
          const newStatus = { ...prev };
          delete newStatus[fileName];
          return newStatus;
        });
      }, 3000);
    } catch (error) {
      console.error('Error downloading file:', error);
      const keyParts = s3Key.split('/');
      const fileName = keyParts[keyParts.length - 1];
      setDownloadStatus(prev => ({ ...prev, [fileName]: 'error' }));
    }
  };

  return (
    <Box>
      <SpaceBetween direction="vertical" size="s">
        {/* Render uploaded images inline */}
        {uploadedImageFiles.length > 0 && (
          <div>
            <SpaceBetween direction="vertical" size="s">
              {uploadedImageFiles.map((file, index) => (
                <InlineImageFile key={`uploaded-image-${index}`} file={file} chatId={chatId} />
              ))}
            </SpaceBetween>
          </div>
        )}

        {/* Render generated images and other files as download links */}
        {(generatedImageFiles.length > 0 || otherFiles.length > 0) && (
          <div>
            <div style={{
              display: 'flex',
              flexDirection: 'row',
              flexWrap: 'wrap',
              gap: '10px',
              alignItems: 'center'
            }}>
              {/* Render generated images as download links */}
              {generatedImageFiles.filter(file => {
                const isValid = file && file.s3_url && typeof file.s3_url === 'string';
                console.debug(`MessageFiles - Filtering generated image:`, file, `Valid: ${isValid}`);
                return isValid;
              }).map((file, index) => {
                const fileUrl = file.s3_url;
                // Extract just the filename from the S3 URL
                const urlParts = fileUrl.split('/');
                let fileName = urlParts[urlParts.length - 1];

                // Remove versionId from fileName if present
                if (fileName.includes('?versionId=')) {
                  fileName = fileName.split('?versionId=')[0];
                }

                return (
                  <div key={`gen-img-${index}`} style={{ display: 'flex', alignItems: 'center', marginBottom: '5px' }}>
                    <Button
                      variant="link"
                      iconName="file-open"
                      onClick={() => handleFileDownload(file.s3_key, file.version_id)}
                      disabled={downloadStatus[fileName] === 'loading'}
                      download={fileName}
                    >
                      {fileName}
                    </Button>
                    {downloadStatus[fileName] === 'loading' && <Spinner size="normal" />}
                    {downloadStatus[fileName] === 'success' &&
                      <StatusIndicator type="success">Downloaded</StatusIndicator>
                    }
                    {downloadStatus[fileName] === 'error' &&
                      <StatusIndicator type="error">Failed</StatusIndicator>
                    }
                  </div>
                );
              })}

              {/* Render other non-image files as download links */}
              {otherFiles.filter(file => {
                const isValid = file && file.s3_url && typeof file.s3_url === 'string';
                console.debug(`MessageFiles - Filtering file:`, file, `Valid: ${isValid}`);
                return isValid;
              }).map((file, index) => {
                const fileUrl = file.s3_url;
                // Extract just the filename from the S3 URL
                const urlParts = fileUrl.split('/');
                let fileName = urlParts[urlParts.length - 1];

                // Remove versionId from fileName if present
                if (fileName.includes('?versionId=')) {
                  fileName = fileName.split('?versionId=')[0];
                }

                return (
                  <div key={`other-${index}`} style={{ display: 'flex', alignItems: 'center', marginBottom: '5px' }}>
                    <Button
                      variant="link"
                      iconName="file-open"
                      onClick={() => handleFileDownload(file.s3_key, file.version_id)}
                      disabled={downloadStatus[fileName] === 'loading'}
                      download={fileName}
                    >
                      {fileName}
                    </Button>
                    {downloadStatus[fileName] === 'loading' && <Spinner size="normal" />}
                    {downloadStatus[fileName] === 'success' &&
                      <StatusIndicator type="success">Downloaded</StatusIndicator>
                    }
                    {downloadStatus[fileName] === 'error' &&
                      <StatusIndicator type="error">Failed</StatusIndicator>
                    }
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </SpaceBetween>
    </Box>
  );
}, (prevProps, nextProps) => {
  // Custom comparison function for React.memo
  // Only re-render if files or chatId actually changed
  if (prevProps.chatId !== nextProps.chatId) return false;
  
  // Deep comparison of files array
  if (!prevProps.files && !nextProps.files) return true;
  if (!prevProps.files || !nextProps.files) return false;
  if (prevProps.files.length !== nextProps.files.length) return false;
  
  // Compare each file's key properties
  return prevProps.files.every((prevFile, index) => {
    const nextFile = nextProps.files[index];
    return prevFile?.s3_key === nextFile?.s3_key &&
           prevFile?.s3_url === nextFile?.s3_url &&
           prevFile?.version_id === nextFile?.version_id &&
           prevFile?.name === nextFile?.name;
  });
});

const convertS3UrlsToDocumentLinks = (content) => {
  // First replace standalone S3 URLs
  let result = content.replace(
    /(?<!\]\()s3:\/\/[^\s)]+(?!\))/g,
    (url) => {
      const fileName = url.split('/').pop().split('?')[0];
      const versionMatch = url.match(/versionId=([^&\s]+)/);
      const versionId = versionMatch ? versionMatch[1] : '';
      const linkText = versionId ? `${fileName}?versionId=${versionId}` : fileName;
      return `[${linkText}](#documents)`;
    }
  );
  
  // Then replace S3 URLs inside markdown links and preserve version ID
  result = result.replace(
    /\[([^\]]+)\]\(s3:\/\/[^)]+\)/g,
    (match, linkText, url) => {
      const fullUrl = match.match(/\(([^)]+)\)/)[1];
      const versionMatch = fullUrl.match(/versionId=([^&)]+)/);
      const versionId = versionMatch ? versionMatch[1] : '';
      const newLinkText = versionId ? `${linkText}?versionId=${versionId}` : linkText;
      return `\n\n[${newLinkText}](#documents)`;
    }
  );
  
  return result;
};

const StreamingMarkdown = React.memo(({ content, isStreaming }) => {
  const lastNewlineIndex = content.lastIndexOf('\n');
  const completeContent = lastNewlineIndex > -1 ? content.slice(0, lastNewlineIndex + 1) : '';
  const incompleteContent = lastNewlineIndex > -1 ? content.slice(lastNewlineIndex + 1) : content;

  return (
    <div>
      {completeContent && (
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code: ({ node, inline, className, children, ...props }) => {
              return inline ? (
                <code {...props} style={{ backgroundColor: '#f0f0f0', padding: '2px 4px', borderRadius: '3px' }}>
                  {children}
                </code>
              ) : (
                <pre style={{ backgroundColor: '#f0f0f0', padding: '10px', borderRadius: '5px', overflowX: 'auto', whiteSpace: 'pre-wrap' }}>
                  <code {...props}>{children}</code>
                </pre>
              );
            },
            p: ({ children }) => (
              <p style={{ whiteSpace: 'pre-wrap', margin: '0.5em 0' }}>{children}</p>
            )
          }}
        >
          {completeContent}
        </ReactMarkdown>
      )}
      {incompleteContent && (
        <span style={{ whiteSpace: 'pre-wrap' }}>{incompleteContent}</span>
      )}
    </div>
  );
});

const MessageWithS3Images = React.memo(({ content, chatId }) => {
  console.log('🖼️ MessageWithS3Images render', Date.now());
  const [processedContent, setProcessedContent] = useState(content);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedUrls, setProcessedUrls] = useState(new Map());
  const [lastProcessedContent, setLastProcessedContent] = useState('');

  useEffect(() => {
    // Process image URLs in the content
    const processImageUrls = async () => {
      // Only process if content actually contains image URLs
      if (!containsImageUrl(content)) {
        setProcessedContent(convertS3UrlsToDocumentLinks(content));
        return;
      }

      // Skip processing if content hasn't changed
      if (content === lastProcessedContent) {
        return;
      }

      setIsProcessing(true);
      try {
        // Regular expression to find S3 URLs with optional version ID - but not those in parentheses
        const s3Pattern = /(?<!\()s3:\/\/([^\/]+)\/(.*?\.(jpg|jpeg|png|gif|bmp|svg|webp)(?:\.\w+)?)(?:\?versionId=([^&\s]+))?/gi;

        // Regular expression to find S3 URLs in parentheses with optional version ID (non-greedy, stops at first closing paren)
        const s3ParenthesisPattern = /\((s3:\/\/[^\/\s)]+\/[^)\s]*\.(jpg|jpeg|png|gif|bmp|svg|webp)(?:\?versionId=[^&\s)]+)?)\)/gi;

        // Regular expression to find document links in markdown format (md, docx, csv, xlsx, pptx, txt, json)
        const s3DocumentPattern = /\[([^\]]+)\]\((s3:\/\/[^\/\s)]+\/[^)\s]*\.(md|docx|csv|xlsx|pptx|txt|json)(?:\?versionId=[^&\s)]+)?)\)/gi;

        // Regular expression to find images in parentheses
        const parenthesisPattern = /\(([^\/\s)]+\.(jpg|jpeg|png|gif|bmp|svg|webp)(?:\.\w+)?)\)/gi;

        // Get all matches
        let match;
        let modifiedContent = content;
        const replacements = [];

        // Collect S3 URL replacements
        console.debug(`Getting filenames for content: ${content}`);
        while ((match = s3Pattern.exec(content)) !== null) {
          const s3Url = match[0];
          const filePath = match[2];
          const versionId = match[4]; // This will be undefined if no versionId in URL

          // Get the full URL path after s3://bucket-name/
          const urlParts = s3Url.split('/');
          // Remove the protocol and bucket name (first 3 parts: s3:, '', bucket-name)
          urlParts.splice(0, 3);
          // Get just the filename (last part)
          let fileName = urlParts[urlParts.length - 1];

          // Remove versionId from fileName if present
          if (fileName.includes('?versionId=')) {
            fileName = fileName.split('?versionId=')[0];
          }

          console.debug('S3 URL:', s3Url);
          console.debug('URL parts:', urlParts);
          console.debug('Extracted filename:', fileName);
          console.debug('Version ID:', versionId);

          // Add to replacements array
          replacements.push({
            originalUrl: s3Url,
            fileName,
            filePath,
            versionId,
            type: 's3'
          });
        }

        // Collect S3 URLs in parentheses
        while ((match = s3ParenthesisPattern.exec(content)) !== null) {
          const fullMatch = match[0]; // The entire match including parentheses
          let s3Url = match[1];       // Just the s3 URL

          // Remove any trailing parenthesis that might have been captured incorrectly
          if (s3Url.endsWith(')')) {
            s3Url = s3Url.slice(0, -1);
          }

          // Extract the path and version ID - handle case where URL might end with a closing parenthesis
          const cleanS3Url = s3Url.endsWith(')') ? s3Url.slice(0, -1) : s3Url;
          const s3UrlMatch = cleanS3Url.match(/s3:\/\/([^\/]+)\/(.*?\.(jpg|jpeg|png|gif|bmp|svg|webp)(?:\.\w+)?)(?:\?versionId=([^&\s]+))?/i);

          if (s3UrlMatch) {
            const filePath = s3UrlMatch[2];
            const versionId = s3UrlMatch[4]; // This will be undefined if no versionId in URL

            // Get the full URL path after s3://bucket-name/
            const urlParts = s3Url.split('/');
            // Remove the protocol and bucket name (first 3 parts: s3:, '', bucket-name)
            urlParts.splice(0, 3);
            // Get just the filename (last part)
            let fileName = urlParts[urlParts.length - 1];

            // Remove versionId from fileName if present
            if (fileName.includes('?versionId=')) {
              fileName = fileName.split('?versionId=')[0];
            }

            console.debug('S3 URL in parentheses:', s3Url);
            console.debug('URL parts:', urlParts);
            console.debug('Extracted filename:', fileName);
            console.debug('Version ID:', versionId);

            // Add to replacements array
            replacements.push({
              originalUrl: fullMatch,
              fileName,
              filePath,
              versionId,
              type: 's3_parenthesis'
            });
          }
        }

        // Collect parenthesis image replacements
        while ((match = parenthesisPattern.exec(content)) !== null) {
          const fullMatch = match[0]; // The entire match including parentheses
          const fileName = match[1];  // Just the filename

          console.debug('Parenthesis image:', fullMatch);
          console.debug('Extracted filename:', fileName);

          // Add to replacements array
          replacements.push({
            originalUrl: fullMatch,
            fileName,
            type: 'parenthesis'
          });
        }

        // Collect document link replacements (md, docx, csv, xlsx, etc.) and convert to #documents links
        while ((match = s3DocumentPattern.exec(content)) !== null) {
          const fullMatch = match[0]; // The entire markdown link
          const linkText = match[1];  // The link text
          const s3Url = match[2];     // The S3 URL

          console.debug('Document link found:', fullMatch);
          console.debug('Link text:', linkText);
          console.debug('S3 URL:', s3Url);

          // Convert document links to #documents links directly
          const versionMatch = s3Url.match(/versionId=([^&\s)]+)/);
          const versionId = versionMatch ? versionMatch[1] : '';
          const newLinkText = versionId ? `${linkText}?versionId=${versionId}` : linkText;
          const documentsLink = `[${newLinkText}](#documents)`;
          
          console.debug('Converting document link to:', documentsLink);
          modifiedContent = modifiedContent.split(fullMatch).join(documentsLink);
        }

        // Process all replacements
        for (const replacement of replacements) {
          try {
            // Check if we already processed this URL
            const cacheKey = `${replacement.originalUrl}_${replacement.versionId || ''}`;
            if (processedUrls.has(cacheKey)) {
              const cachedUrl = processedUrls.get(cacheKey);
              // Apply cached replacement
              if (replacement.type === 's3') {
                modifiedContent = modifiedContent.split(replacement.originalUrl).join(cachedUrl);
              } else if (replacement.type === 's3_parenthesis') {
                modifiedContent = modifiedContent.split(replacement.originalUrl).join(`(${cachedUrl})`);
              } else if (replacement.type === 'pdf') {
                const newLink = `[${replacement.linkText}](${cachedUrl})`;
                modifiedContent = modifiedContent.split(replacement.originalUrl).join(newLink);

              } else {
                modifiedContent = modifiedContent.split(replacement.originalUrl).join(`(${cachedUrl})`);
              }
              continue;
            }

            // Get CloudFront signed URL - use filePath or fileName as the s3Key
            const s3Key = replacement.filePath || replacement.fileName;
            console.debug(`Getting CloudFront URL for ${s3Key}`);

            // Check if s3Key contains the chatId prefix and remove it to avoid duplication
            let relativePath = s3Key;
            if (s3Key.startsWith(`${chatId}/`)) {
              relativePath = s3Key.substring(`${chatId}/`.length);
              console.debug(`MessageWithS3Images - Removed full chatId prefix. Original: ${s3Key}, Relative: ${relativePath}`);
            } else {
              // Also check for truncated chat ID patterns (common issue with CloudFormation files)
              // Match patterns like "af-d615-4cd9-a6ff-d2e8872572a3/" which are truncated UUIDs
              const truncatedUuidPattern = /^[0-9a-f]{2,8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\//;
              if (truncatedUuidPattern.test(s3Key)) {
                // Find the first slash and remove everything before it
                const firstSlashIndex = s3Key.indexOf('/');
                if (firstSlashIndex > 0) {
                  relativePath = s3Key.substring(firstSlashIndex + 1);
                  console.debug(`MessageWithS3Images - Removed truncated UUID prefix. Original: ${s3Key}, Relative: ${relativePath}`);
                }
              }
            }
            const response = await getDocumentCFSignedUrl(chatId, relativePath, replacement.versionId);
            console.debug(`signed url: ${response.url}`);
            console.debug(`replacement type: ${replacement.type}`)

            // Cache the result
            setProcessedUrls(prev => new Map(prev).set(cacheKey, response.url));

            if (replacement.type === 's3') {
              // Replace S3 URL with CloudFront URL - use split/join to avoid regex issues
              console.debug(`Replace s3 ${replacement.originalUrl} with ${response.url}`);
              modifiedContent = modifiedContent.split(replacement.originalUrl).join(response.url);
            } else if (replacement.type === 's3_parenthesis') {
              // Replace parenthesized S3 URL with image tag
              console.debug(`Replacing parenthesized s3 ${replacement.originalUrl} with ${response.url}`);
              modifiedContent = modifiedContent.split(replacement.originalUrl).join(
                `(${response.url})`
              );
            } else if (replacement.type === 'pdf') {
              // Replace PDF markdown link with CloudFront URL
              console.debug(`Replace PDF link ${replacement.originalUrl} with ${response.url}`);
              const newLink = `[${replacement.linkText}](${response.url})`;
              modifiedContent = modifiedContent.split(replacement.originalUrl).join(newLink);

            } else {
              // Replace parenthesis with image tag
              console.debug(`Replace parenthesis with image tag ${replacement.originalUrl} with ${response.url}`);
              modifiedContent = modifiedContent.split(replacement.originalUrl).join(
                `(${response.url})`
              );
            }
          } catch (error) {
            console.error("Failed to get CloudFront URL:", error);
          }
        }

        setProcessedContent(convertS3UrlsToDocumentLinks(modifiedContent));
        
      } finally {
        setIsProcessing(false);
      }
    };

    processImageUrls();
  }, [content, chatId, lastProcessedContent]);

  if (isProcessing) {
    return (
      <div style={{ width: '100%', overflow: 'hidden' }}>
        <ReactMarkdown
          components={{
            code: ({ node, inline, className, children, ...props }) => {
              return inline ? (
                <code {...props} style={{ backgroundColor: '#f0f0f0', padding: '2px 4px', borderRadius: '3px' }}>
                  {children}
                </code>
              ) : (
                <pre style={{ backgroundColor: '#f0f0f0', padding: '10px', borderRadius: '5px', overflowX: 'auto' }}>
                  <code {...props}>{children}</code>
                </pre>
              );
            },
            img: ({ src, alt, ...props }) => (
              <img
                src={src}
                alt={alt || "Image"}
                style={{
                  maxWidth: '60%',
                  height: 'auto',
                  borderRadius: '8px',
                  margin: '10px 0'
                }}
                {...props}
              />
            )
          }}
        >
          {content}
        </ReactMarkdown>
        <Spinner size="normal" />
      </div>
    );
  }

  return (
    <div style={{ width: '100%', overflow: 'hidden' }}>
      <ReactMarkdown
        components={{
          a: ({ href, children, ...props }) => {
            if (href === '#documents') {
              const linkText = typeof children === 'string' ? children : children.join('');
              // Map link text to actual filenames based on document type
              let fileName = linkText;
              let versionId = '';
              let displayText = linkText;
              
              // Extract version ID if it's in the link text (for converted S3 URLs)
              const versionMatch = linkText.match(/\?versionId=([^&\s)]+)/);
              if (versionMatch) {
                versionId = versionMatch[1];
                fileName = fileName.replace(/\?versionId=[^&\s)]+/, ''); // Remove version from filename
                displayText = fileName; // Clean display text without version
              }
              
              if (linkText === 'Cost Analysis Report' || linkText.toLowerCase().includes('cost') || linkText.toLowerCase().includes('pricing')) {
                fileName = 'pricing.md';
                displayText = 'Cost Analysis Report';
              } else if (linkText.toLowerCase().includes('diagram')) {
                fileName = 'diagram.png';
                displayText = linkText.includes('.png') ? 'diagram.png' : linkText;
              } else if (linkText.toLowerCase().includes('sow') || linkText.toLowerCase().includes('statement') || linkText === 'SOW Document') {
                fileName = 'ScopeOfWork.docx';
                displayText = 'SOW Document';
              } else if (linkText.toLowerCase().includes('funding') || linkText === 'Download Funding Document') {
                fileName = 'funding_analysis.md';
                displayText = 'Funding Document';
              }
              
              const documentType = fileName.includes('diagram') ? 'diagram' : 
                                 fileName.includes('pricing') ? 'pricing' : 
                                 fileName.includes('sow') ? 'sow' : 
                                 fileName.includes('funding') ? 'funding' : 'unknown';
              return (
                <a 
                  href="#" 
                  onClick={(e) => {
                    e.preventDefault();
                    window.scrollToDocument(documentType, fileName, versionId);
                  }}
                  style={{ color: '#1976d2', textDecoration: 'underline' }}
                  {...props}
                >
                  {displayText}
                </a>
              );
            }
            // Handle S3 URLs in existing markdown links
            if (href && href.startsWith('s3://')) {
              const fileName = href.split('/').pop().split('?')[0];
              const versionMatch = href.match(/versionId=([^&]+)/);
              const versionId = versionMatch ? versionMatch[1] : '';
              
              // Determine document type based on file classification
              let documentType = 'user_upload'; // Default for user uploads
              
              if (href.includes('/uploads/')) {
                // This is a user upload - try to determine type from filename and context
                // Check if this file appears in the structured message format
                const messageContent = message.content || '';
                
                if (messageContent.includes('SOW Document:') && messageContent.includes(fileName)) {
                  documentType = 'sow_document';
                } else if (messageContent.includes('Architecture Diagram:') && messageContent.includes(fileName)) {
                  documentType = 'diagram';
                } else if (messageContent.includes('Pricing Calculator:') && messageContent.includes(fileName)) {
                  documentType = 'pricing_report';
                } else if (messageContent.includes('Funding Document:') && messageContent.includes(fileName)) {
                  documentType = 'funding_document';
                } else {
                  // Fallback to filename-based detection
                  documentType = fileName.toLowerCase().includes('diagram') ? 'diagram' : 
                                fileName.toLowerCase().includes('pricing') || fileName.toLowerCase().includes('.csv') ? 'pricing_report' : 
                                fileName.toLowerCase().includes('sow') || fileName.toLowerCase().includes('.docx') ? 'sow_document' : 
                                fileName.toLowerCase().includes('funding') ? 'funding_document' : 'user_upload';
                }
              } else {
                // This is an AI-generated document - use existing logic
                documentType = fileName.includes('diagram') ? 'diagram' : 
                              fileName.includes('pricing') ? 'pricing_report' : 
                              fileName.includes('sow') ? 'sow_document' : 
                              fileName.includes('funding') ? 'funding_document' : 'user_upload';
              }
              
              return (
                <a 
                  href="#" 
                  onClick={(e) => {
                    e.preventDefault();
                    window.scrollToDocument(documentType, fileName, versionId);
                  }}
                  style={{ color: '#1976d2', textDecoration: 'underline' }}
                  {...props}
                >
                  {children}
                </a>
              );
            }
            return <a href={href} {...props}>{children}</a>;
          },
          code: ({ node, inline, className, children, ...props }) => {
            return inline ? (
              <code {...props} style={{ backgroundColor: '#f0f0f0', padding: '2px 4px', borderRadius: '3px' }}>
                {children}
              </code>
            ) : (
              <pre style={{ backgroundColor: '#f0f0f0', padding: '10px', borderRadius: '5px', overflowX: 'auto' }}>
                <code {...props}>{children}</code>
              </pre>
            );
          },
          img: ({ src, alt, ...props }) => {
            return (
              <img
                src={src}
                alt={alt || "Image"}
                style={{
                  maxWidth: '60%',
                  height: 'auto',
                  display: 'block'
                }}
                {...props}
              />
            );
          },
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison function for React.memo
  // Only re-render if content or chatId actually changed
  return prevProps.content === nextProps.content && prevProps.chatId === nextProps.chatId;
});

// Memoized message component to prevent unnecessary re-renders
const MemoizedMessage = React.memo(({ message, index, chatId, isLoading, messages }) => {
  // Function to check if a message is within an SA Review section
  const isInSAReviewSection = (messageIndex) => {
    // Check if this message itself is the start message
    if (messages[messageIndex].type === 'system' && messages[messageIndex].content?.startsWith('Solutions Architect review started by')) {
      return true;
    }
    
    // Find the most recent start/end messages before this message
    let lastStartIndex = -1;
    let lastEndIndex = -1;
    
    for (let i = messageIndex - 1; i >= 0; i--) {
      if (messages[i].type === 'system') {
        if (messages[i].content?.startsWith('Solutions Architect review started by') && lastStartIndex === -1) {
          lastStartIndex = i;
        }
        if (messages[i].content?.startsWith('Solutions Architect review ended') && lastEndIndex === -1) {
          lastEndIndex = i;
        }
      }
      
      // Stop if we found both or if we found an end before a start
      if (lastEndIndex !== -1 && (lastStartIndex === -1 || lastEndIndex > lastStartIndex)) {
        return false; // Most recent action was an end
      }
      if (lastStartIndex !== -1 && (lastEndIndex === -1 || lastStartIndex > lastEndIndex)) {
        return true; // Most recent action was a start
      }
    }
    
    return false; // No start found or ended review
  };
  
  // Check if this message and adjacent messages are SA Review messages
  const isCurrentSAReview = isInSAReviewSection(index);
  const isPrevSAReview = index > 0 && isInSAReviewSection(index - 1);
  const isNextSAReview = index < messages.length - 1 && isInSAReviewSection(index + 1);
  
  const showTopLine = isCurrentSAReview && isPrevSAReview;
  const showBottomLine = isCurrentSAReview && isNextSAReview;
  const showSideBar = isCurrentSAReview;

  if (message.type === 'alert') {
    return (
      <Alert
        key={`alert-${index}`}
        header={message.header || "Error"}
        type="error"
        statusIconAriaLabel="Error"
      >
        {message.content}
      </Alert>
    );
  }

  return (
    <div key={`message-container-${index}`} style={{ position: 'relative' }}>
      {/* Vertical line for SA Review messages */}
      {showSideBar && (
        <div style={{
          position: 'absolute',
          left: '50px',
          top: showTopLine ? '-10px' : '0px',
          bottom: showBottomLine ? '-10px' : '0px',
          width: '2px',
          borderLeft: '2px dotted #0073bb',
          backgroundColor: 'transparent',
          zIndex: 1
        }} />
      )}
      
      <div className="message-row">
        {message.type === 'assistant' && (
          <div className="message-avatar assistant">
            {message.avatarLoading ? (
              <Spinner size="normal" />
            ) : (
              <Icon name="gen-ai" />
            )}
          </div>
        )}
        {message.type === 'user' && (
          <div className="message-avatar user">
            U
          </div>
        )}
        {message.type === 'system' && (
          <div className="message-avatar system">
            <Icon name="notification" />
          </div>
        )}
        <Box
          key={`message-${index}`}
          padding={{ top: 'm', bottom: 'm', left: 'l', right: 'l' }}
          color={message.type === 'user' ? 'text-body-secondary' : 'text-body-primary'}
          backgroundColor={message.type === 'user' ? 'background-container' : 'background-container-alt'}
          borderRadius="l"
          margin={{ left: message.type === 'assistant' ? 'xs' : 'xs', right: message.type === 'user' ? 's' : 'xxxl' }}
          className="enhanced-chat-bubble"
          data-type={message.type}
          style={{ flex: 1 }}
        >
          <SpaceBetween direction="vertical" size="xs">
            <Box color="text-body-secondary" fontSize="body-s">
              {new Date(message.timestamp).toLocaleTimeString()}
            </Box>
            <Box style={message.type === 'system' ? { fontStyle: 'italic' } : {}}>
              {typeof message.content === 'string' ? (
                message.type === 'assistant' ? (
                  <StreamingMarkdown content={message.content} isStreaming={message.avatarLoading} />
                ) : message.type === 'system' ? (
                  <span style={{ fontStyle: 'italic' }}>
                    {message.content.split('\n').map((line, i) => (
                      <React.Fragment key={i}>
                        {line}
                        {i < message.content.split('\n').length - 1 && <br />}
                      </React.Fragment>
                    ))}
                  </span>
                ) : (
                  // Handle user messages with simple markdown
                  <ReactMarkdown
                      components={{
                        a: ({ href, children, ...props }) => {
                          if (href === '#documents') {
                            const linkText = typeof children === 'string' ? children : children.join('');
                            return (
                              <a
                                href="#documents"
                                onClick={(e) => {
                                  e.preventDefault();
                                  if (window.scrollToDocument) {
                                    // Extract filename and version from link text
                                    let fileName = linkText;
                                    let versionId = '';
                                    const versionMatch = linkText.match(/\?versionId=([^&\s)]+)/);
                                    if (versionMatch) {
                                      versionId = versionMatch[1];
                                      fileName = fileName.replace(/\?versionId=[^&\s)]+/, '');
                                    }
                                    window.scrollToDocument('user_upload', fileName, versionId);
                                  }
                                }}
                                style={{ color: '#0073bb', textDecoration: 'underline', cursor: 'pointer' }}
                                {...props}
                              >
                                {children}
                              </a>
                            );
                          }
                          return <a href={href} {...props}>{children}</a>;
                        }
                      }}
                    >
                      {convertS3UrlsToDocumentLinks(message.content)}
                    </ReactMarkdown>
                )
              ) : (
                message.content
              )}
            </Box>
          </SpaceBetween>

          {(message.files && message.files.length > 0) && (
            <Box padding={{ top: 's', bottom: 's' }}>
              <MessageFiles
                key={`files-${message.message_id || message.frontend_message_id || index}-${message.filesUpdatedAt || 'initial'}`}
                files={message.files}
                chatId={chatId}
              />
            </Box>
          )}

          {(message.citations && message.citations.length > 0) && (
            <MessageCitations citations={message.citations} />
          )}

          {message.type === 'assistant' && (index !== messages.length - 1 || !isLoading) && (
            <FeedbackActions contentToCopy={message.contentToCopy || message.content} />
          )}
        </Box>
      </div>
    </div>
  );
});

// Error boundary component
class ChatPageErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ChatPage Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Container>
          <Alert
            type="error"
            header="Application Error"
          >
            <div>
              <p>Something went wrong while loading the chat page.</p>
              <p><strong>Error:</strong> {this.state.error?.message || 'Unknown error'}</p>
              <Button onClick={() => window.location.reload()}>
                Reload Page
              </Button>
            </div>
          </Alert>
        </Container>
      );
    }

    return this.props.children;
  }
}

const ChatPageContent = () => {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [error, setError] = useState('');
  const [chatData, setChatData] = useState(null);
  const [isConnected, setIsConnected] = useState(true);
  const [toolbarRefreshTrigger, setToolbarRefreshTrigger] = useState(0);
  const [documentRefreshTrigger, setDocumentRefreshTrigger] = useState(0);
  const [files, setFiles] = useState([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [userHasScrolled, setUserHasScrolled] = useState(false);
  const [allowedExtensions, setAllowedExtensions] = useState([]);
  const [acceptAttribute, setAcceptAttribute] = useState('');
  const [isEditingName, setIsEditingName] = useState(false);
  const [editingChatName, setEditingChatName] = useState('');
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  
  const handleEditChatName = () => {
    setEditingChatName(chatData?.chat_name || '');
    setIsEditingName(true);
  };

  const handleSaveChatName = async () => {
    if (!editingChatName.trim()) return;
    
    try {
      const updatedChat = await updateChatName(chatId, editingChatName);
      setChatData(prev => ({ ...prev, chat_name: updatedChat.chatName }));
      setIsEditingName(false);
      
      // Refresh side panel to show updated name
      if (window.refreshRecentChats) {
        window.refreshRecentChats();
      }
    } catch (error) {
      console.error('Error updating chat name:', error);
      setIsEditingName(false);
    }
  };

  const handleCancelEdit = () => {
    setIsEditingName(false);
    setEditingChatName('');
  };

  const handleNameKeyDown = (e) => {
    const key = e.detail?.key || e.key;
    if (key === 'Enter') {
      e.preventDefault();
      handleSaveChatName();
    } else if (key === 'Escape') {
      e.preventDefault();
      handleCancelEdit();
    }
  };

  const addSystemMessage = (content) => {
    const systemMessage = {
      type: 'system',
      content: content,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, systemMessage]);
  };

  const messageCountRef = useRef(0);
  const fileInputRef = useRef(null);

  // Load chat history when component mounts
  useEffect(() => {
    const loadChatHistory = async () => {
      try {
        setIsInitialLoading(true);
        setError('');

        // Handle case where chatId might be invalid
        if (!chatId) {
          setError('Invalid chat ID. Please try starting a new chat.');
          setIsInitialLoading(false);
          return;
        }

        console.debug(`Loading chat history for chat ID: ${chatId}`);
        const data = await getChatSession(chatId);

        // Handle empty or undefined data
        if (!data) {
          setError('No chat data found. The chat may have been deleted or may not exist.');
          setIsInitialLoading(false);
          return;
        }

        console.debug('Chat data received1:', data);
        setChatData(data);

        // Initialize messages array
        let initialMessages = [];

        // If messages array exists in the response, use it
        if (data && Array.isArray(data.messages)) {
          console.debug(`Found ${data.messages.length} messages in chat history`);
          initialMessages = data.messages.map(msg => {
            let message;
            // Handle different message formats
            if (msg.M && msg.M.role && msg.M.content) {
              // DynamoDB format
              const role = msg.M.role.S;
              message = {
                type: role === 'user' ? 'user' : role === 'system' ? 'system' : 'assistant',
                content: msg.M.content.S,
                timestamp: msg.M.message_timestamp?.S || new Date().toISOString()
              };

              // Extract files if they exist
              if (msg.M.files && msg.M.files.L) {
                try {
                  // Parse the files array from DynamoDB format
                  const filesArray = [];

                  msg.M.files.L.forEach(fileItem => {
                    if (fileItem.M) {
                      const file = {
                        file_size: fileItem.M.file_size?.S || '',
                        s3_key: fileItem.M.s3_key?.S || '',
                        s3_url: fileItem.M.s3_url?.S || '',
                        type: fileItem.M.type?.S || '',
                        version_id: fileItem.M.version_id?.S || ''
                      };

                      // Only add files with valid s3_url
                      if (file.s3_url) {
                        filesArray.push(file);
                      }
                    }
                  });

                  if (filesArray.length > 0) {
                    message.files = filesArray;
                  }
                } catch (error) {
                  console.error('Error parsing files:', error);
                }
              }

              // Extract citations if they exist
              if (msg.M.citations && msg.M.citations.L) {
                try {
                  // Parse the citations array from DynamoDB format
                  const citationsArray = [];

                  msg.M.citations.L.forEach(citationItem => {
                    if (citationItem.M) {
                      const citation = {
                        title: citationItem.M.title?.S || '',
                        location: {},
                        sourceContent: []
                      };

                      // Parse location if it exists
                      if (citationItem.M.location && citationItem.M.location.M) {
                        const loc = citationItem.M.location.M;
                        if (loc.page?.S) citation.location.page = loc.page.S;
                        if (loc.position?.S) citation.location.position = loc.position.S;
                        if (loc.chunk?.S) citation.location.chunk = loc.chunk.S;
                      }

                      // Parse sourceContent if it exists
                      if (citationItem.M.sourceContent && citationItem.M.sourceContent.L) {
                        citationItem.M.sourceContent.L.forEach(contentItem => {
                          if (contentItem.S) {
                            citation.sourceContent.push(contentItem.S);
                          }
                        });
                      }

                      citationsArray.push(citation);
                    }
                  });

                  if (citationsArray.length > 0) {
                    message.citations = citationsArray;
                  }
                } catch (error) {
                  console.error('Error parsing citations:', error);
                }
              }
            } else {
              // Regular format
              message = {
                type: msg.role === 'user' ? 'user' : 'assistant',
                content: msg.content,
                timestamp: msg.message_timestamp || new Date().toISOString()
              };

              // Extract files if they exist
              if (msg.files && Array.isArray(msg.files)) {
                message.files = msg.files;
              }

              // Extract citations if they exist
              if (msg.citations && Array.isArray(msg.citations)) {
                message.citations = msg.citations;
              }
            }

            if (message.type === 'assistant') {
              message.contentToCopy = message.content;
            }

            return message;
          });
        }

        // No need to process S3 URLs anymore - just return messages as-is
        const markedMessages = initialMessages;

        // Sort messages by timestamp
        markedMessages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        setMessages(markedMessages);
      } catch (err) {
        console.error('Error loading chat history:', err);
        setError('Failed to load chat history. Please try again later.');
      } finally {
        setIsInitialLoading(false);
      }
    };

    loadChatHistory();
  }, [chatId]);

  // Load allowed file extensions from backend
  useEffect(() => {
    const loadAllowedExtensions = async () => {
      try {
        const extensions = await getAllowedExtensions();
        setAllowedExtensions(extensions);
        
        // Create accept attribute for file input (add dots to extensions)
        const acceptValue = extensions.map(ext => ext.startsWith('.') ? ext : `.${ext}`).join(',');
        setAcceptAttribute(acceptValue);
        
        console.log('Loaded allowed extensions:', extensions);
        console.log('Generated accept attribute:', acceptValue);
      } catch (error) {
        console.error('Failed to load allowed extensions:', error);
        // Fallback to common extensions if loading fails
        const fallbackExtensions = ['txt', 'csv', 'json', 'pdf', 'docx', 'xlsx', 'pptx', 'md', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg'];
        setAllowedExtensions(fallbackExtensions);
        setAcceptAttribute(fallbackExtensions.map(ext => `.${ext}`).join(','));
      }
    };

    loadAllowedExtensions();
  }, []);

  // Listen for user interaction to disable auto-scroll
  useEffect(() => {
    const handleUserInteraction = () => {
      setUserHasScrolled(true);
      
      // Re-enable after 3 seconds if at bottom
      setTimeout(() => {
        const isAtBottom = window.innerHeight + window.scrollY >= document.body.offsetHeight - 100;
        if (isAtBottom) {
          setUserHasScrolled(false);
        }
      }, 3000);
    };
    
    // Listen for various user interaction events
    window.addEventListener('wheel', handleUserInteraction, { passive: true });
    window.addEventListener('touchstart', handleUserInteraction, { passive: true });
    window.addEventListener('keydown', (e) => {
      if (['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End'].includes(e.key)) {
        handleUserInteraction();
      }
    });
    
    return () => {
      window.removeEventListener('wheel', handleUserInteraction);
      window.removeEventListener('touchstart', handleUserInteraction);
      window.removeEventListener('keydown', handleUserInteraction);
    };
  }, []);

  // Auto-scroll every 300ms during streaming, but only if user hasn't scrolled away
  useEffect(() => {
    let autoScrollInterval;
    
    if (isLoading && !userHasScrolled) {
      autoScrollInterval = setInterval(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 1000); // Reduced from 300ms to 1000ms
    }
    
    return () => {
      if (autoScrollInterval) {
        clearInterval(autoScrollInterval);
      }
    };
  }, [isLoading, userHasScrolled]);

  // Handle connection status
  useEffect(() => {
    const handleOnline = () => setIsConnected(true);
    const handleOffline = () => setIsConnected(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Handle scroll to bottom button visibility
  useEffect(() => {
    const handleScroll = () => {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const scrollHeight = document.documentElement.scrollHeight;
      const clientHeight = window.innerHeight;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
      setShowScrollToBottom(!isNearBottom && scrollHeight > clientHeight + 200);
    };

    window.addEventListener('scroll', handleScroll);
    setTimeout(handleScroll, 1000);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [messages]);

  const scrollToBottom = () => {
    window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' });
  };

  // Handle file selection with validation
  const handleFileSelect = async (event) => {
    console.log('🔍 FILES DEBUG - handleFileSelect triggered');
    const selectedFiles = Array.from(event.target.files);
    console.log('🔍 FILES DEBUG - selectedFiles from input:', selectedFiles.length, selectedFiles.map(f => f.name));
    if (selectedFiles.length > 0) {
      try {
        // Validate file extensions
        const validation = await validateFileExtensions(selectedFiles);
        console.log('🔍 FILES DEBUG - validation result:', validation);
        
        if (validation.validFiles.length > 0) {
          setFiles(prevFiles => {
            const newFiles = [...prevFiles, ...validation.validFiles];
            console.log('🔍 FILES DEBUG - setFiles called, new files array:', newFiles.length, newFiles.map(f => f.name));
            return newFiles;
          });
          console.log(`Selected ${validation.validFiles.length} valid files:`, validation.validFiles.map(f => f.name));
        }
        
        // Show error for invalid files
        if (validation.invalidFiles.length > 0) {
          const invalidFileNames = validation.invalidFiles.map(item => item.file.name).join(', ');
          const allowedExts = validation.allowedExtensions.join(', ');
          setError(`Invalid file types: ${invalidFileNames}. Allowed extensions: ${allowedExts}`);
          
          console.warn('Invalid files rejected:', validation.invalidFiles);
          
          // Clear error after 5 seconds
          setTimeout(() => setError(''), 5000);
        }
      } catch (error) {
        console.error('Error validating files:', error);
        setError('Error validating file types. Please try again.');
        setTimeout(() => setError(''), 5000);
      }
    }
    // Reset the input so the same file can be selected again if needed
    event.target.value = '';
  };

  // Handle drag and drop
  const handleDragOver = (event) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (event) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = async (event) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(false);

    const droppedFiles = Array.from(event.dataTransfer.files);
    if (droppedFiles.length > 0) {
      try {
        // Validate file extensions
        const validation = await validateFileExtensions(droppedFiles);
        
        if (validation.validFiles.length > 0) {
          setFiles(prevFiles => [...prevFiles, ...validation.validFiles]);
          console.log(`Dropped ${validation.validFiles.length} valid files:`, validation.validFiles.map(f => f.name));
        }
        
        // Show error for invalid files
        if (validation.invalidFiles.length > 0) {
          const invalidFileNames = validation.invalidFiles.map(item => item.file.name).join(', ');
          const allowedExts = validation.allowedExtensions.join(', ');
          setError(`Invalid file types: ${invalidFileNames}. Allowed extensions: ${allowedExts}`);
          
          console.warn('Invalid files rejected:', validation.invalidFiles);
          
          // Clear error after 5 seconds
          setTimeout(() => setError(''), 5000);
        }
      } catch (error) {
        console.error('Error validating dropped files:', error);
        setError('Error validating file types. Please try again.');
        setTimeout(() => setError(''), 5000);
      }
    }
  };

  // Remove a file from the selected files
  const handleRemoveFile = (index) => {
    setFiles(prevFiles => prevFiles.filter((_, i) => i !== index));
  };



  // Separate the actual message sending logic
  const executeSendMessage = async (content, options = {}, filesToSend = []) => {
    console.log('🔧 executeSendMessage called with:', {
      content: content.substring(0, 50) + '...',
      options,
      filesToSendCount: filesToSend.length,
      fileClassifications: options.fileClassifications
    });

    // Create display content for UI
    let displayContent = content;

    // Generate temporary ID for frontend message tracking
    const tempMessageId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // Always show user message
    const userMessage = {
      type: 'user',
      frontend_message_id: tempMessageId,
      content: displayContent,
      timestamp: new Date().toISOString(),
      files: filesToSend.length > 0 ? filesToSend.map(f => ({
        name: f.name || 'Unknown file',
        size: f.size || 0
      })).filter(f => f.name !== 'Unknown file') : undefined
    };

    setMessages(prev => [...prev, userMessage]);

    setIsLoading(true);
    setError('');

    // Debug logging
    console.log('Sending message:', content);
    console.log('Sending files:', filesToSend.length);
    console.log('File classifications:', options.fileClassifications);

    try {
      // Create assistant message placeholder
      const assistantMessage = {
        type: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        avatarLoading: true,
        files: []
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Prepare options for sendMessage
      const sendOptions = {
        files: filesToSend,
        frontend_message_id: tempMessageId,  // Send temporary ID to backend
        ...options
      };

      // Automatically set POC funding intent for APN Funding Assistant when files are uploaded
      if (chatData?.assistant_persona === 'apn_funding_assistant' && filesToSend.length > 0) {
        sendOptions.intent = 'poc_funding_review';
        console.log('APN Funding Assistant detected with files - setting intent to poc_funding_review');
      }

      await sendMessage(chatId, content, (response) => {
        // ... existing streaming response handling logic ...
        let responseContent = '';
        console.debug(`Streaming response object: ${response}`);
        console.log('🔍 INSIGHT DEBUG - Raw response:', response);

        // Handle different response types
        if (typeof response === 'string' && response.includes('{"type":"message_update"')) {
          // Handle message update
          try {
            const messageUpdate = JSON.parse(response);
            console.log('📝 Message update received:', messageUpdate);
            
            // Update the specific user message
            setMessages(prev => {
              const newMessages = [...prev];
              console.log('🔍 Looking for frontend_message_id:', messageUpdate.frontend_message_id);
              console.log('🔍 Looking for message_id:', messageUpdate.message_id);
              console.log('🔍 Available user messages:', newMessages.filter(msg => msg.type === 'user').map(msg => ({
                content: msg.content?.substring(0, 50) + '...',
                frontend_message_id: msg.frontend_message_id,
                message_id: msg.message_id,
                hasFrontendId: !!msg.frontend_message_id,
                hasMessageId: !!msg.message_id
              })));
              
              // Try frontend_message_id first (most reliable)
              let messageIndex = newMessages.findIndex(msg => 
                msg.type === 'user' && 
                msg.frontend_message_id === messageUpdate.frontend_message_id
              );
              
              // Fallback to backend message_id if available
              if (messageIndex === -1 && messageUpdate.message_id) {
                messageIndex = newMessages.findIndex(msg => 
                  msg.type === 'user' && 
                  msg.message_id === messageUpdate.message_id
                );
                console.log('🔄 Fallback to message_id search, index found:', messageIndex);
              }
              
              console.log('🔍 Message index found:', messageIndex);
              
              if (messageIndex !== -1) {
                newMessages[messageIndex] = {
                  ...newMessages[messageIndex],
                  content: messageUpdate.content,
                  message_id: messageUpdate.message_id, // Store backend ID
                  frontend_message_id: messageUpdate.frontend_message_id, // Keep frontend ID
                  filesUpdated: true,
                  filesUpdatedAt: Date.now()
                };
                console.log('✅ Updated user message with file links using frontend_message_id');
              } else {
                console.log('❌ No matching user message found for frontend_message_id:', messageUpdate.frontend_message_id);
                // Try position-based fallback - update the most recent user message
                const lastUserIndex = newMessages.length >= 2 ? newMessages.length - 2 : -1;
                if (lastUserIndex >= 0 && newMessages[lastUserIndex].type === 'user') {
                  console.log('🔄 Final fallback: Updating user message at position', lastUserIndex);
                  newMessages[lastUserIndex] = {
                    ...newMessages[lastUserIndex],
                    content: messageUpdate.content,
                    message_id: messageUpdate.message_id, // Add the backend message_id
                    frontend_message_id: messageUpdate.frontend_message_id, // Add frontend ID
                    filesUpdated: true,
                    filesUpdatedAt: Date.now()
                  };
                  console.log('✅ Updated user message with final fallback method');
                }
              }
              
              return newMessages;
            });
            
            return; // Don't process as regular response
          } catch (error) {
            console.error('Error parsing message update:', error);
          }
        }
        
        // if response has tool_result JSON structure, extract files and add them to the message
        if (typeof response === 'string' && response.includes('{"type":"tool_result"')) {
          try {
            const toolResult = JSON.parse(response);
            responseContent = toolResult.content;
            console.debug(`toolResult: ${JSON.stringify(toolResult)}`);
            console.log('🔍 INSIGHT DEBUG - Tool result received:', toolResult);

            // Extract files if they exist
            if (toolResult.files) {
              const files = Object.values(toolResult.files);
              console.debug(`files: ${JSON.stringify(files)}`);

              // Check if this is file upload metadata (contains "Files uploaded successfully")
              if (toolResult.content && toolResult.content.includes('Files uploaded successfully')) {
                console.debug('Detected file upload metadata, updating user message with:', files);
                // Update the USER message (second to last) with the processed file metadata
                setMessages(prev => {
                  const newMessages = [...prev];
                  if (newMessages.length >= 2) {
                    const userMessageIndex = newMessages.length - 2; // User message is second to last
                    const userMessage = newMessages[userMessageIndex];

                    if (userMessage.type === 'user') {
                      // Update user message with processed file metadata
                      newMessages[userMessageIndex] = {
                        ...userMessage,
                        files: files, // Replace with processed S3 metadata
                        filesUpdatedAt: Date.now()
                      };
                      console.log('Updated user message with processed file metadata:', files.length);
                    }
                  }
                  return newMessages;
                });
              } else {
                // This is a regular tool result - add to assistant message
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMessage = newMessages[newMessages.length - 1];

                  // Merge new files with any existing files
                  const existingFiles = lastMessage.files || [];
                  const updatedFiles = [...existingFiles, ...files];

                  // Update the last assistant message with files
                  newMessages[newMessages.length - 1] = {
                    ...lastMessage,
                    files: updatedFiles,
                    hasFiles: true,
                    avatarLoading: true,
                    filesUpdatedAt: Date.now()
                  };

                  console.log('Files added to assistant message during streaming:', updatedFiles.length);
                  return newMessages;
                });
              }
            }
          } catch (error) {
            console.error('Error parsing tool result:', error);
            responseContent = response; // Fallback to using the raw response
          }
        } else {
          responseContent = response;
          console.debug(`Processing responseContent: ${responseContent.substring(0, 100)}...`);

          setMessages(prev => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];

            // Check if response is complete
            const isComplete = responseContent.trim().length > 0 &&
              !responseContent.endsWith("...") &&
              !responseContent.includes("Using tool");

            // Check if the FULL accumulated content contains image URLs


            // Extract files from S3 URLs in content for the MessageFiles component
            let extractedFiles = lastMessage.files || [];
            // Skip S3 URL extraction - files are already displayed inline in message content

            // Update the last assistant message with new content
            newMessages[newMessages.length - 1] = {
              ...assistantMessage,
              content: responseContent,
              avatarLoading: !isComplete,
              contentToCopy: responseContent,
              files: extractedFiles,
              filesUpdatedAt: extractedFiles.length > (lastMessage.files?.length || 0) ? Date.now() : lastMessage.filesUpdatedAt
            };

            return newMessages;
          });
        }
      }, sendOptions);
    } catch (err) {
      setError(err.message || 'Failed to send message. Please try again.');
      // Remove the last message on error
      setMessages(prev => prev.slice(0, -1));
    } finally {
      // First set isLoading to false
      setIsLoading(false);

      // Then update the avatar loading state to match isLoading
      setMessages(prev => {
        const newMessages = [...prev];
        if (newMessages.length > 0) {
          const lastMessage = newMessages[newMessages.length - 1];
          if (lastMessage.type === 'assistant') {
            newMessages[newMessages.length - 1] = {
              ...lastMessage,
              avatarLoading: false
            };
          }
        }
        return newMessages;
      });

      // Trigger toolbar refresh to update button states based on new conversation stage
      setToolbarRefreshTrigger(prev => prev + 1);
      // Trigger document refresh to show new documents
      setDocumentRefreshTrigger(prev => prev + 1);
    }
  };

  // Create ref for ChatToolbar to access its handleSendMessage method
  const chatToolbarRef = useRef(null);

  // Internal function that actually executes the message without validation
  const executeMessageInternal = useCallback(async (messageContent, options = {}) => {
    const content = messageContent || '';

    console.log('🔧 executeMessageInternal called with:', {
      content: content.substring(0, 50) + '...',
      options,
      filesCount: files.length,
      filesArray: files.map(f => f.name)
    });
    console.log('🔧 FILES DEBUG - files state at executeMessageInternal:', files);

    // Capture files before clearing them
    const filesToSend = [...files];
    console.log('🔧 FILES DEBUG - filesToSend captured:', filesToSend.length, filesToSend.map(f => f.name));

    // Clear files after capturing them
    setFiles([]);

    // Execute the actual send message
    await executeSendMessage(content, options, filesToSend);
  }, [files]);

  const handleSendMessage = useCallback(async (messageContent = null, options = {}) => {
    console.log('🔍 handleSendMessage called with:', messageContent);
    console.log('🔍 FILES DEBUG - files state at handleSendMessage:', files.length, files.map(f => f.name));
    // Use provided content - messageContent is now required when called from isolated input
    const content = messageContent || '';

    // Check if we have content or files to send
    if ((!content.trim() && files.length === 0) || !isConnected) {
      console.log('🔍 handleSendMessage early return - no content or not connected');
      console.log('🔍 FILES DEBUG - early return because: content empty?', !content.trim(), 'files empty?', files.length === 0, 'connected?', isConnected);
      return;
    }

    // For APN Funding Assistant with files, delegate to ChatToolbar for validation
    if (chatData?.assistant_persona === 'apn_funding_assistant' && files.length > 0) {
      console.log('🔧 ChatPage: APN assistant detected with files, delegating to ChatToolbar');
      console.log('🔧 ChatPage: chatToolbarRef.current:', chatToolbarRef.current);
      console.log('🔧 ChatPage: files count:', files.length);
      
      // Use ChatToolbar's handleSendMessage method which includes validation
      if (chatToolbarRef.current && chatToolbarRef.current.handleSendMessage) {
        console.log('🔧 ChatPage: Calling ChatToolbar.handleSendMessage');
        // Don't clear files here - let ChatToolbar handle the flow
        chatToolbarRef.current.handleSendMessage(content, options);
        return;
      } else {
        console.error('🔧 ChatPage: ChatToolbar ref not available or handleSendMessage not exposed');
      }
    }

    // For other cases, execute directly
    await executeMessageInternal(content, options);
  }, [files, isConnected, chatId, chatData?.assistant_persona, executeMessageInternal]);

  const handleKeyPress = useCallback((event) => {
    const key = event.detail?.key || event.key;
    const shiftKey = event.detail?.shiftKey || event.shiftKey;

    if (key === 'Enter' && !shiftKey) {
      event.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  const handleInputChange = useCallback(({ detail }) => {
    setInputValue(detail.value);
  }, []);

  // Show loading spinner while initial chat history is loading
  if (isInitialLoading) {
    return (
      <div className="chat-container">
        <Container
          header={
            <Header variant="h2">
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <img
                  src="/aws_icon_32.jpg"
                  alt="AWS Logo"
                  style={{
                    height: '32px',
                    marginRight: '10px',
                    display: 'inline-block'
                  }}
                  onError={(e) => {
                    console.error("Failed to load image");
                    e.target.style.display = 'none';
                  }}
                />
                {isEditingName ? (
                  <Input
                    value={editingChatName}
                    onChange={({ detail }) => setEditingChatName(detail.value)}
                    onKeyDown={handleNameKeyDown}
                    onBlur={handleSaveChatName}
                    autoFocus
                    style={{ width: '300px' }}
                  />
                ) : (
                  <span 
                    onClick={handleEditChatName}
                    style={{ 
                      cursor: 'pointer',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      transition: 'background-color 0.2s'
                    }}
                    onMouseEnter={(e) => e.target.style.backgroundColor = '#f0f0f0'}
                    onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
                    title="Click to edit chat name"
                  >
                    {chatData?.chat_name || 'Chat with SERA'}
                  </span>
                )}
              </div>
            </Header>
          }
          fitHeight
        >
          <Box textAlign="center" padding="xl">
            <SpaceBetween direction="vertical" size="l">
              <Spinner size="large" />
              <Box variant="p">Loading chat history...</Box>
            </SpaceBetween>
          </Box>
        </Container>
      </div>
    );
  }

  return (
    <div className="chat-container">
      <Container
        header={
          <Header
            variant="h2"
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <StatusIndicator
                  type={isConnected ? "success" : "error"}
                >
                  {isConnected ? "Connected" : "Offline"}
                </StatusIndicator>
                <Button
                  iconName="close"
                  variant="icon"
                  onClick={() => navigate('/')}
                />
              </SpaceBetween>
            }
          >
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <img
                src="/aws_icon_32.jpg"
                alt="AWS Logo"
                style={{
                  height: '32px',
                  marginRight: '10px',
                  display: 'inline-block'
                }}
                onError={(e) => {
                  console.error("Failed to load image");
                  e.target.style.display = 'none';
                }}
              />
              {isEditingName ? (
                <Input
                  value={editingChatName}
                  onChange={({ detail }) => setEditingChatName(detail.value)}
                  onKeyDown={handleNameKeyDown}
                  onBlur={handleSaveChatName}
                  autoFocus
                  style={{ width: '300px' }}
                />
              ) : (
                <span 
                  onClick={handleEditChatName}
                  style={{ 
                    cursor: 'pointer',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    transition: 'background-color 0.2s'
                  }}
                  onMouseEnter={(e) => e.target.style.backgroundColor = '#f0f0f0'}
                  onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
                  title="Click to edit chat name"
                >
                  {chatData?.chat_name || 'Chat with SERA'}
                </span>
              )}
            </div>
          </Header>
        }
        fitHeight
      >
        <SpaceBetween direction="vertical" size="l" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 70px)' }}>
          {import.meta.env.VITE_SHOW_BETA_DISCLAIMER === 'true' && (
            <Alert
              type="warning"
              dismissible={false}
              header="Beta Disclaimer"
            >
              <div dangerouslySetInnerHTML={{ __html: import.meta.env.VITE_BETA_DISCLAIMER_TEXT }} />
            </Alert>
          )}

          {error && (
            <Alert
              type="error"
              header="Error"
              dismissible
              onDismiss={() => setError('')}
            >
              {error}
            </Alert>
          )}

          {/* POC Funding Guidance for APN Funding Assistant */}
          {chatData?.assistant_persona === 'apn_funding_assistant' && messages.length === 0 && (
            <POCFundingGuidance 
              onFileUpload={handleFileSelect}
              fileInputRef={fileInputRef}
              selectedFiles={files}
            />
          )}

          {/* WAFR Guidance for Well-Architected Framework Assistant */}
          {chatData?.assistant_persona === 'aws_well_architected_framework_assistant' && messages.length === 0 && (
            <WAFRGuidance 
              onFileUpload={handleFileSelect}
              fileInputRef={fileInputRef}
              selectedFiles={files}
              onStartAssessment={() => {
                if (files.length > 0) {
                  executeSendMessage('Please perform a comprehensive WAFR assessment', {}, files);
                  setFiles([]); // Clear files after sending
                }
              }}
            />
          )}

          <div style={{ position: 'relative', flex: 1, overflow: 'auto' }}>
            {showScrollToBottom && (
              <button
                onClick={scrollToBottom}
                style={{
                  position: 'fixed',
                  top: '60px',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  zIndex: 1000,
                  width: '50px',
                  height: '50px',
                  borderRadius: '50%',
                  backgroundColor: 'rgba(107, 114, 128, 0.7)',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
                }}
                title="Scroll to bottom"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                  <polyline points="7,13 12,18 17,13"/>
                  <polyline points="7,6 12,11 17,6"/>
                </svg>
              </button>
            )}
            
            <div style={{ overflow: 'auto', height: '100%' }} ref={messagesContainerRef}>
              <div className="messages" role="region" aria-label="Chat">
              <SpaceBetween direction="vertical" size="l">
                {messages.length === 0 ? (
                  <Box textAlign="center" padding="xl" color="text-body-secondary">
                    {chatData?.assistant_persona === 'apn_funding_assistant' 
                      ? "Ready to analyze your POC funding documents! Upload your SOW, architecture diagram, and pricing calculator to get started."
                      : chatData?.assistant_persona === 'aws_well_architected_framework_assistant'
                      ? "Ready to assess your architecture! Upload your architecture diagrams or technical documentation to get started."
                      : "No messages yet. Start the conversation!"
                    }
                  </Box>
                ) : (
                  messages.map((message, index) => (
                    <MemoizedMessage
                      key={`message-${index}-${message.timestamp}`}
                      message={message}
                      index={index}
                      chatId={chatId}
                      isLoading={isLoading}
                      messages={messages}
                    />
                  ))
                )}
              </SpaceBetween>
            </div>
            <div ref={messagesEndRef} />
            </div>
          </div>

          <Box>
            <SANotification
              chatId={chatId}
              onMergeComplete={() => window.location.reload()}
            />

            {/* File preview area */}
            {files.length > 0 && (
              <Box
                padding="s"
                borderRadius="m"
                margin={{ bottom: 's' }}
                style={{
                  backgroundColor: '#e3f2fd', // Light blue background
                  border: '1px solid #bbdefb' // Light blue border
                }}
              >
                <SpaceBetween direction="vertical" size="xs">
                  <Box fontWeight="bold" color="text-body-primary">Files to upload ({files.length}):</Box>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {files.map((file, index) => (
                      <div key={index} style={{
                        display: 'flex',
                        alignItems: 'center',
                        backgroundColor: '#ffffff',
                        padding: '6px 12px',
                        borderRadius: '12px', // More rounded corners
                        border: '1px solid #90caf9', // Light blue border for individual files
                        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)', // Subtle shadow
                        transition: 'all 0.2s ease'
                      }}>
                        <Icon name="file" size="small" style={{ color: '#1976d2' }} />
                        <span style={{
                          margin: '0 8px',
                          fontSize: '14px',
                          color: '#1565c0' // Blue text color
                        }}>
                          {file.name} ({Math.round(file.size / 1024)}KB)
                        </span>
                        <Button
                          iconName="close"
                          variant="icon"
                          size="small"
                          onClick={() => handleRemoveFile(index)}
                          ariaLabel={`Remove ${file.name}`}
                          // style={{
                          //   color: '#757575'
                          // }}
                        />
                      </div>
                    ))}
                  </div>
                </SpaceBetween>
              </Box>
            )}

            <div
              className="prompt-container"
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              style={{
                position: 'relative',
                border: isDragOver ? '2px dashed #0073bb' : 'none',
                borderRadius: isDragOver ? '8px' : '0',
                backgroundColor: isDragOver ? 'rgba(0, 115, 187, 0.05)' : 'transparent',
                transition: 'all 0.2s ease'
              }}
            >
              {isDragOver && (
                <div style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  backgroundColor: 'rgba(0, 115, 187, 0.1)',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  zIndex: 10,
                  pointerEvents: 'none'
                }}>
                  <Box textAlign="center" color="text-body-secondary">
                    <Icon name="upload" size="large" />
                    <Box margin={{ top: 's' }}>
                      {chatData?.assistant_persona === 'apn_funding_assistant' 
                        ? "Drop your POC funding documents here (SOW, Architecture Diagram, Pricing Calculator)"
                        : "Drop files here to upload"
                      }
                    </Box>
                  </Box>
                </div>
              )}
              <ConversationStage
                chatId={chatId}
                refreshTrigger={toolbarRefreshTrigger}
                loading={isLoading}
                onAddSystemMessage={addSystemMessage}
                onChatDataUpdate={() => {
                  // Refresh chat data but preserve existing messages to avoid re-processing images
                  getChatSession(chatId).then(data => {
                    setChatData(data);
                    // Don't reload messages - they're already up to date from addSystemMessage
                  }).catch(err => {
                    console.error('Error refreshing chat data:', err);
                  });
                }}
              />
              <IsolatedChatInput
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
                isConnected={isConnected}
                pocMode={chatData?.assistant_persona === 'apn_funding_assistant'}
                wafrMode={chatData?.assistant_persona === 'aws_well_architected_framework_assistant'}
                selectedFiles={files}
                disabled={
                  // Disable SA copy chat when in final stages
                  (chatData?.source_chat_id && chatData?.review_status && ['ready_for_user', 'complete_no_changes', 'rejected', 'reassigned', 'merged', 'cancelled'].includes(chatData.review_status)) ||
                  // Disable original chat during active review
                  (!chatData?.source_chat_id && chatData?.review_status && ['requested', 'in_progress', 'ready_for_merge'].includes(chatData.review_status))
                }
              />
              <div className="toolbar-container">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileSelect}
                    style={{ display: 'none' }}
                    multiple
                    accept={acceptAttribute}
                  />
                  <ChatToolbar
                    ref={chatToolbarRef}
                    chatId={chatId}
                    onSendMessage={executeMessageInternal}
                    refreshTrigger={toolbarRefreshTrigger}
                    disabled={
                      isLoading ||
                      // Disable SA copy chat when in final stages
                      (chatData?.source_chat_id && chatData?.review_status && ['ready_for_user', 'complete_no_changes', 'rejected', 'reassigned', 'merged', 'cancelled'].includes(chatData.review_status)) ||
                      // Disable original chat during active review
                      (!chatData?.source_chat_id && chatData?.review_status && ['requested', 'in_progress', 'ready_for_merge'].includes(chatData.review_status))
                    }
                    onFileUpload={handleFileSelect}
                    fileInputRef={fileInputRef}
                    chatLoading={isLoading}
                    isConnected={isConnected}
                    selectedFiles={files}
                    assistantPersona={chatData?.assistant_persona}
                  />
                </div>
              </div>
            </div>
          </Box>

          {/* Documents Section */}
          <Box>
            <Documents 
              chatId={chatId} 
              refreshTrigger={documentRefreshTrigger}
              isReviewCopy={!!chatData?.source_chat_id}
            />
          </Box>

        </SpaceBetween>
      </Container>
      
    </div>
  );
};

const ChatPage = () => {
  // Add scroll to document function to window
  useEffect(() => {
    window.scrollToDocument = (documentType, fileName, versionId = '', docId = '') => {
      // Expand the Documents section
      if (window.expandDocuments) {
        window.expandDocuments();
      }
      
      // Wait for expansion, then find and scroll to the specific tile
      setTimeout(() => {
        const tiles = document.querySelectorAll('.document-tile');
        let targetTile = null;
        
        tiles.forEach(tile => {
          tile.style.backgroundColor = '';
          tile.style.border = '1px solid #e9ebed';
          
          console.log('Checking tile:', tile.dataset.filename, 'version:', tile.dataset.versionId, 'docId:', tile.dataset.docId);
          console.log('Looking for:', fileName, 'version:', versionId, 'type:', documentType, 'docId:', docId);
          
          // For calculator links, match by document ID
          if (documentType === 'calculator_link') {
            if (tile.dataset.docId === docId) {
              console.log('Calculator link match! Highlighting tile');
              targetTile = tile;
              tile.style.backgroundColor = '#e3f2fd';
              tile.style.border = '2px solid #1976d2';
              setTimeout(() => {
                tile.style.backgroundColor = '';
                tile.style.border = '1px solid #e9ebed';
              }, 3000);
            }
          }
          // For user uploads, match by filename and version ID
          else if (documentType === 'user_upload') {
            if (tile.dataset.filename === fileName && tile.dataset.versionId === versionId) {
              console.log('User upload match! Highlighting tile');
              targetTile = tile;
              tile.style.backgroundColor = '#e3f2fd';
              tile.style.border = '2px solid #1976d2';
              setTimeout(() => {
                tile.style.backgroundColor = '';
                tile.style.border = '1px solid #e9ebed';
              }, 3000);
            }
          } else {
            // For AI-generated documents, use existing logic
            if (tile.dataset.filename === fileName) {
              console.log('Filename matches!');
              // If version ID is provided, match it too for uniqueness
              if (versionId && tile.dataset.versionId !== versionId) {
                console.log('Version mismatch, skipping');
                return; // Skip this tile if version doesn't match
              }
              console.log('Full match! Highlighting tile');
              targetTile = tile;
              tile.style.backgroundColor = '#e3f2fd';
              tile.style.border = '2px solid #1976d2';
              setTimeout(() => {
                tile.style.backgroundColor = '';
                tile.style.border = '1px solid #e9ebed';
              }, 3000);
            }
          }
        });
        
        // Scroll to the specific tile if found
        if (targetTile) {
          targetTile.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
          // Fallback to documents section if tile not found
          const documentsSection = document.querySelector('[data-testid="documents-section"]');
          if (documentsSection) {
            documentsSection.scrollIntoView({ behavior: 'smooth' });
          }
        }
      }, 500);
    };
    
    return () => {
      delete window.scrollToDocument;
    };
  }, []);

  return (
    <ChatPageErrorBoundary>
      <ChatPageContent />
    </ChatPageErrorBoundary>
  );
};

export default ChatPage;
