import React from 'react';
import Box from '@cloudscape-design/components/box';
import SpaceBetween from '@cloudscape-design/components/space-between';
import DeleteChatTool from './tools/DeleteChatTool';
import ThumbsUpTool from './tools/ThumbsUpTool';
import ThumbsDownTool from './tools/ThumbsDownTool';

/**
 * Component that renders a column of tools for a chat item
 */
function ChatToolsColumn({ 
    chat, 
    onChatDelete, 
    onFeedbackSubmit 
}) {
    // Check if the chat is in a stage where feedback is allowed
    const canProvideFeedback = ['SOLUTION_PROPOSED', 'SOLUTION_FINALIZED'].includes(chat.stage);
    
    // Check if the chat is in a stage where deletion is allowed
    const canDelete = true; // Allow deletion for all stages
    
    // Stop event propagation to prevent row click
    const handleToolsClick = (e) => {
        e.stopPropagation();
    };
    
    return (
        <Box padding="s" onClick={handleToolsClick} data-testid="tools-column">
            <SpaceBetween direction="horizontal" size="xs">
                {canDelete && (
                    <DeleteChatTool 
                        key="delete-tool"
                        chatId={chat.chatId} 
                        onSuccess={onChatDelete} 
                    />
                )}
                
                {canProvideFeedback && (
                    <React.Fragment key="feedback-tools">
                        <ThumbsUpTool 
                            key="thumbs-up"
                            chatId={chat.chatId} 
                            onSuccess={onFeedbackSubmit} 
                        />
                        <ThumbsDownTool 
                            key="thumbs-down"
                            chatId={chat.chatId} 
                            onSuccess={onFeedbackSubmit} 
                        />
                    </React.Fragment>
                )}
            </SpaceBetween>
        </Box>
    );
}

export default ChatToolsColumn;
