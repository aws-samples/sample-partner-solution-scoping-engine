import React, { useState } from 'react';
import Button from '@cloudscape-design/components/button';
import Modal from '@cloudscape-design/components/modal';
import Box from '@cloudscape-design/components/box';
import SpaceBetween from '@cloudscape-design/components/space-between';
import { deleteChat } from '../../services/chatService';

/**
 * Tool for deleting a chat
 */
function DeleteChatTool({ chatId, onSuccess }) {
    const [visible, setVisible] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    
    const handleDelete = async () => {
        try {
            setLoading(true);
            await deleteChat(chatId);
            setVisible(false);
            if (onSuccess) {
                onSuccess(chatId);
            }
        } catch (err) {
            setError(err.message || 'Failed to delete chat');
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <>
            <Button
                iconName="remove"
                variant="icon"
                onClick={(e) => {
                    e.stopPropagation();
                    setError('');
                    setVisible(true);
                }}
                ariaLabel="Delete chat"
            />
            
            <Modal
                visible={visible}
                onDismiss={() => setVisible(false)}
                header="Delete Chat"
                footer={
                    <Box float="right">
                        <SpaceBetween direction="horizontal" size="xs">
                            <Button 
                                variant="link" 
                                onClick={() => setVisible(false)}
                            >
                                Cancel
                            </Button>
                            <Button 
                                variant="primary" 
                                onClick={handleDelete}
                                loading={loading}
                                danger
                            >
                                Delete
                            </Button>
                        </SpaceBetween>
                    </Box>
                }
            >
                <SpaceBetween size="m">
                    <Box variant="p">
                        Are you sure you want to delete this chat? This action cannot be undone.
                    </Box>
                    
                    {error && (
                        <Box color="text-status-error">
                            {error}
                        </Box>
                    )}
                </SpaceBetween>
            </Modal>
        </>
    );
}

export default DeleteChatTool;
