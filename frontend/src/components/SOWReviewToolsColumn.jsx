import React from 'react';
import Box from '@cloudscape-design/components/box';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Button from '@cloudscape-design/components/button';
import SOWApprovalTool from './tools/SOWApprovalTool';
import SOWRejectionTool from './tools/SOWRejectionTool';
import SOWDownloadTool from './tools/SOWDownloadTool';

/**
 * Component that renders a column of tools for SOW review
 */
function SOWReviewToolsColumn({ 
    sow, 
    onFeedbackSubmit 
}) {
    // Check if the SOW is in a stage where feedback is allowed
    const canProvideFeedback = ['SOW_GENERATED', 'SOW_REVIEW'].includes(sow.stage);
    
    // Check if SOW can be downloaded
    const canDownload = sow.s3_url && !sow.s3_url.includes('undefined');
    
    // Stop event propagation to prevent row click
    const handleToolsClick = (e) => {
        e.stopPropagation();
    };
    
    return (
        <Box padding="s" onClick={handleToolsClick} data-testid="sow-tools-column">
            <SpaceBetween direction="horizontal" size="xs">
                {/* Download button - always available if SOW exists */}
                {canDownload && (
                    <SOWDownloadTool 
                        chatId={sow.chat_id}
                        s3Url={sow.s3_url}
                    />
                )}
                
                {/* Review tools - only if review is allowed */}
                {canProvideFeedback && (
                    <>
                        <SOWApprovalTool 
                            chatId={sow.chat_id}
                            sowData={sow}
                            onSuccess={onFeedbackSubmit} 
                        />
                        
                        <SOWRejectionTool 
                            chatId={sow.chat_id}
                            sowData={sow}
                            onSuccess={onFeedbackSubmit} 
                        />
                    </>
                )}
                
                {/* Show feedback status if already reviewed */}
                {!canProvideFeedback && sow.feedback && (
                    <Box>
                        <Button
                            variant="icon"
                            iconName={sow.feedback === 'approved' ? 'status-positive' : 'status-negative'}
                            disabled
                            ariaLabel={`SOW ${sow.feedback}`}
                        />
                    </Box>
                )}
            </SpaceBetween>
        </Box>
    );
}

export default SOWReviewToolsColumn;