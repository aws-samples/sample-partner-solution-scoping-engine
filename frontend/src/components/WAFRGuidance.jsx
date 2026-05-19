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
 * Component that provides guidance for WAFR assessment document upload
 */
function WAFRGuidance({ onFileUpload, fileInputRef, selectedFiles = [], onStartAssessment }) {
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
          header="Well-Architected Framework Assessment Ready"
        >
          <SpaceBetween direction="vertical" size="s">
            <Box>
              I'm ready to conduct a comprehensive AWS Well-Architected Framework assessment. 
              Upload your architecture documents below and I'll analyze them across all six WAFR pillars.
            </Box>
            <Box fontWeight="bold" color="text-status-info">
              Supported Documents:
            </Box>
            <div style={{ marginLeft: '16px' }}>
              <SpaceBetween direction="vertical" size="xs">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Icon name="file" size="small" />
                  <Box>Architecture Diagrams - PNG, JPG, or PDF</Box>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Icon name="file" size="small" />
                  <Box>Technical Documentation - PDF or Word documents</Box>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Icon name="file" size="small" />
                  <Box>Infrastructure Specs - Any text-based format</Box>
                </div>
              </SpaceBetween>
            </div>
            <Box fontWeight="bold" color="text-status-info" margin={{ top: 's' }}>
              For best performance and assessment accuracy, at minimum, provide the Architecture Diagram and your Infrastructure as Code template files.
            </Box>
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
              Click the button below to select your architecture documents, or drag and drop them anywhere in the chat area. 
              Assessment will start automatically when you upload the files.
            </Box>
            <SpaceBetween direction="horizontal" size="s">
              <Button
                variant="primary"
                iconName="upload"
                onClick={handleUploadClick}
              >
                Upload Architecture Documents
              </Button>
              <Button
                variant="primary"
                iconName="status-positive"
                onClick={onStartAssessment}
                disabled={selectedFiles.length === 0}
              >
                Start your WAFR Assessment
              </Button>
            </SpaceBetween>
            
            {/* Show selected files */}
            {selectedFiles.length > 0 && (
              <Box margin={{ top: 's' }}>
                <SpaceBetween direction="vertical" size="xs">
                  <Box fontWeight="bold" color="text-status-success">
                    Files Ready for Assessment ({selectedFiles.length}):
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
            <Box fontWeight="bold">What I'll assess:</Box>
            <div style={{ marginLeft: '16px' }}>
              <SpaceBetween direction="vertical" size="xxs">
                <Box>• <strong>Operational Excellence</strong> - Monitoring, automation, and operational procedures</Box>
                <Box>• <strong>Security</strong> - Identity management, data protection, and infrastructure security</Box>
                <Box>• <strong>Reliability</strong> - Fault tolerance, disaster recovery, and availability</Box>
                <Box>• <strong>Performance Efficiency</strong> - Resource optimization and scaling</Box>
                <Box>• <strong>Cost Optimization</strong> - Resource utilization and pricing models</Box>
                <Box>• <strong>Sustainability</strong> - Environmental impact and resource efficiency</Box>
              </SpaceBetween>
            </div>
          </SpaceBetween>
        </Box>
      </SpaceBetween>
    </Box>
  );
}

export default WAFRGuidance;
