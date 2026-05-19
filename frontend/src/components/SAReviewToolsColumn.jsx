import React from 'react';
import Box from '@cloudscape-design/components/box';
import SpaceBetween from '@cloudscape-design/components/space-between';
import ThumbsUpTool from './tools/SAThumbsUpTool';
import ThumbsDownTool from './tools/SAThumbsDownTool';

/**
 * Component that renders a column of tools for Solutions Architect review
 */
function SAReviewToolsColumn({ 
    chat, 
    onFeedbackSubmit 
}) {
    // Check if the chat is in a stage where feedback is allowed
    const canProvideFeedback = ['SOLUTION_PROPOSED', 'SOLUTION_FINALIZED'].includes(chat.stage);
    
    // Stop event propagation to prevent row click
    const handleToolsClick = (e) => {
        e.stopPropagation();
    };
    
    return (
        <Box padding="s" onClick={handleToolsClick} data-testid="tools-column">
            <SpaceBetween direction="horizontal" size="xs">
                {canProvideFeedback && (
                    <>
                        <ThumbsUpTool 
                            chatId={chat.chatId} 
                            onSuccess={onFeedbackSubmit} 
                        />
                        
                        <ThumbsDownTool 
                            chatId={chat.chatId} 
                            onSuccess={onFeedbackSubmit} 
                        />
                    </>
                )}
            </SpaceBetween>
        </Box>
    );
}

export default SAReviewToolsColumn;
