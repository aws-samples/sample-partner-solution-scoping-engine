import React from 'react';
import {
  Modal,
  Box,
  SpaceBetween,
  Button,
  Alert,
  Table,
  Header,
  Icon,
  Select
} from '@cloudscape-design/components';

const FileClassificationModal = ({
  isVisible,
  onClose,
  onContinue,
  selectedFiles,
  fileClassifications,
  onFileClassification,
  autoClassifications,
  classificationOptions,
  validationResult,
  assistantPersona,
  getFileClassification,
  getSelectOptions
}) => {
  const handleDismiss = () => {
    onClose();
  };

  const handleContinue = () => {
    onContinue();
  };

  return (
    <Modal
      visible={isVisible}
      onDismiss={handleDismiss}
      header="Classify Files for Analysis"
      size="large"
      disableContentPaddings={true}
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button
              variant="link"
              onClick={handleDismiss}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleContinue}
              disabled={!validationResult.valid}
            >
              {!validationResult.valid 
                ? `Missing Required Files (${validationResult.missing.length})`
                : 'Continue with Classifications'
              }
            </Button>
          </SpaceBetween>
        </Box>
      }
    >
      <Box
        padding="l"
        margin={{ horizontal: "auto" }}
        style={{ width: "95%", maxWidth: "100%" }}
      >
        <SpaceBetween direction="vertical" size="m">
          <Box>
            <Box variant="p" margin={{ bottom: 's' }}>
              Please classify your files to help the assistant better understand and process them.
            </Box>
            {assistantPersona === 'apn_funding_assistant' && (
              <Box padding="s" backgroundColor="background-notification-blue" borderRadius="s">
                <Box fontWeight="bold" color="text-status-info">
                  POC Funding Requirements:
                </Box>
                <Box color="text-status-info">
                  • SOW Document (Required)
                  <br />
                  • Architecture Diagram (Required)
                  <br />
                  • Pricing Calculator (Optional)
                </Box>
              </Box>
            )}
          </Box>

          {/* Show validation status */}
          {(() => {
            if (!validationResult.valid && validationResult.missing.length > 0) {
              const missingLabels = validationResult.missing.map(type => {
                const option = classificationOptions.find(opt => opt.value === type);
                return option?.label;
              }).filter(Boolean);

              return (
                <Alert
                  type="warning"
                  header="Missing Required Files"
                >
                  Please classify files as: <strong>{missingLabels.join(', ')}</strong>
                </Alert>
              );
            }
            return null;
          })()}

          {/* File Classification Table */}
          <Table
            columnDefinitions={[
              {
                id: 'filename',
                header: 'File',
                cell: (item) => {
                  const autoClassificationType = autoClassifications[item.name];
                  const hasAutoClassification = !!autoClassificationType;

                  return (
                    <Box>
                      <div style={{
                        fontWeight: 'bold',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        marginBottom: '4px',
                      }}>
                        <Icon name="file" size="small" />
                        <span style={{ wordBreak: 'break-word' }}>{item.name}</span>
                      </div>
                      <div style={{
                        fontSize: '0.85em',
                        color: '#666',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                      }}>
                        <span>{Math.round((item.size || 0) / 1024)} KB</span>
                        {hasAutoClassification && (
                          <span style={{
                            color: '#0073bb',
                            fontWeight: 'normal',
                            fontSize: '0.8em'
                          }}>
                            • Auto-detected
                          </span>
                        )}
                      </div>
                    </Box>
                  );
                },
                width: '20%',
                minWidth: '100px'
              },
              {
                id: 'classification',
                header: 'Document Type',
                cell: (item) => (
                  <Box>
                    <Select
                      selectedOption={getFileClassification(item.name)}
                      onChange={({ detail }) => {
                        onFileClassification(item.name, detail.selectedOption.value);
                      }}
                      options={getSelectOptions()}
                      placeholder="Select document type..."
                      expandToViewport={true}
                    />
                  </Box>
                ),
                width: '30%',
                minWidth: '180px'
              }
            ]}
            items={selectedFiles}
            loadingText="Loading files..."
            trackBy="name"
            empty={
              <Box textAlign="center" color="inherit">
                <b>No files selected</b>
                <Box variant="p" color="inherit">
                  Please select files to classify.
                </Box>
              </Box>
            }
            header={
              <Header
                counter={`(${selectedFiles.length})`}
                description="Select the document type for each file"
              >
                Files to Classify
              </Header>
            }
            variant="borderless"
            wrapLines={false}
          />

          {/* Classification Summary */}
          {selectedFiles.length > 0 && (
            <Box padding="s" backgroundColor="background-container-alt" borderRadius="s">
              <SpaceBetween direction="horizontal" size="s" alignItems="center">
                <Box fontWeight="bold" fontSize="body-s">Summary:</Box>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {(() => {
                    const summary = {};

                    // Count classifications
                    selectedFiles.forEach(file => {
                      const classification = fileClassifications[file.name];
                      if (classification && classification !== '') {
                        const option = getSelectOptions().find(opt => opt.value === classification);
                        if (option) {
                          const cleanLabel = option.label.replace(' (Required)', '');
                          summary[cleanLabel] = (summary[cleanLabel] || 0) + 1;
                        }
                      } else {
                        // Check auto-classification
                        const autoClassificationType = autoClassifications[file.name];
                        if (autoClassificationType) {
                          const option = getSelectOptions().find(opt => opt.value === autoClassificationType);
                          if (option) {
                            const cleanLabel = option.label.replace(' (Required)', '') + ' (Auto)';
                            summary[cleanLabel] = (summary[cleanLabel] || 0) + 1;
                          }
                        } else {
                          summary['Unclassified'] = (summary['Unclassified'] || 0) + 1;
                        }
                      }
                    });

                    return Object.entries(summary).map(([type, count]) => (
                      <span key={type} style={{
                        padding: '2px 6px',
                        backgroundColor: type.includes('Unclassified') ? '#fff3cd' : '#d1ecf1',
                        borderRadius: '8px',
                        fontSize: '0.8em',
                        color: type.includes('Unclassified') ? '#856404' : '#0c5460',
                        whiteSpace: 'nowrap'
                      }}>
                        {type}: {count}
                      </span>
                    ));
                  })()}
                </div>
              </SpaceBetween>
            </Box>
          )}
        </SpaceBetween>
      </Box>
    </Modal>
  );
};

export default FileClassificationModal;