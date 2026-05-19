import React from 'react';
import {
  Box,
  SpaceBetween,
  Alert,
  Icon,
  Button,
  Header
} from '@cloudscape-design/components';

/**
 * Component that provides guidance for POC funding document upload
 */
function POCFundingGuidance({ onFileUpload, fileInputRef, selectedFiles = [] }) {
  const handleUploadClick = () => {
    if (fileInputRef?.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <Box margin={{ bottom: 'l' }}>
      <SpaceBetween direction="vertical" size="m">
        <Alert
          type="info"
          header="POC Funding Analysis Ready"
        >
          <SpaceBetween direction="vertical" size="s">
            <Box>
              I'm ready to analyze your POC funding request documents for compliance and eligibility. 
              Please upload the required documents below and I'll automatically provide a comprehensive analysis.
            </Box>
            <Box fontWeight="bold" color="text-status-info">
              Required Documents:
            </Box>
            <div style={{ marginLeft: '16px' }}>
              <SpaceBetween direction="vertical" size="xs">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Icon name="file" size="small" />
                  <Box>Statement of Work (SOW) - PDF or Word document</Box>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Icon name="file-image" size="small" />
                  <Box>Architecture Diagram - PNG, JPG, or PDF</Box>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Icon name="file-csv" size="small" />
                  <Box>Pricing Calculator - CSV or Excel file</Box>
                </div>
              </SpaceBetween>
            </div>
          </SpaceBetween>
        </Alert>

        <Box padding="m" backgroundColor="background-container-alt" borderRadius="m">
          <SpaceBetween direction="vertical" size="s">
            <Header variant="h3">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Icon name="upload" />
                Quick Upload
              </div>
            </Header>
            <Box color="text-body-secondary">
              Click the button below to select your POC funding documents, or drag and drop them anywhere in the chat area. 
              Analysis will start automatically when you upload the files.
            </Box>
            <Button
              variant="primary"
              iconName="upload"
              onClick={handleUploadClick}
            >
              Upload POC Documents
            </Button>
            
            {/* Show selected files */}
            {selectedFiles.length > 0 && (
              <Box margin={{ top: 's' }}>
                <SpaceBetween direction="vertical" size="xs">
                  <Box fontWeight="bold" color="text-status-success">
                    Files Ready for Analysis ({selectedFiles.length}):
                  </Box>
                  <div style={{ marginLeft: '16px' }}>
                    <SpaceBetween direction="vertical" size="xxs">
                      {selectedFiles.map((file, index) => (
                        <div key={index} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <Icon name="status-positive" size="small" />
                          <Box fontSize="body-s">{file.name}</Box>
                        </div>
                      ))}
                    </SpaceBetween>
                  </div>
                </SpaceBetween>
              </Box>
            )}
          </SpaceBetween>
        </Box>

        <Box fontSize="body-s" color="text-body-secondary">
          <SpaceBetween direction="vertical" size="xs">
            <Box fontWeight="bold">What I'll analyze:</Box>
            <div style={{ marginLeft: '16px' }}>
              <SpaceBetween direction="vertical" size="xxs">
                <Box>• Program identification and eligibility requirements</Box>
                <Box>• Financial assessment and budget compliance</Box>
                <Box>• Document correlation and consistency</Box>
                <Box>• Technical scope verification</Box>
                <Box>• AWS Well-Architected Framework validation</Box>
                <Box>• Detailed recommendations and next steps</Box>
              </SpaceBetween>
            </div>
          </SpaceBetween>
        </Box>
      </SpaceBetween>
    </Box>
  );
}

export default POCFundingGuidance;