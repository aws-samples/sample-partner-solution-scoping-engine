import React, { useState } from 'react';
import Box from '@cloudscape-design/components/box';
import Button from '@cloudscape-design/components/button';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Modal from '@cloudscape-design/components/modal';
import Input from '@cloudscape-design/components/input';
import Link from '@cloudscape-design/components/link';
import { useNavigate } from 'react-router-dom';
import { updateChatName } from '../services/chatService';

/**
 * Component that renders a chat name with an edit button
 */
function ChatNameCell({ chatId, chatName, onSuccess }) {
    const [visible, setVisible] = useState(false);
    const [name, setName] = useState(chatName || '');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    
    const displayName = chatName || `Chat ${chatId.substring(0, 8)}...`;
    
    const handleEditClick = (e) => {
        e.stopPropagation();
        setName(chatName || '');
        setError('');
        setVisible(true);
    };
    
    const handleChatClick = (e) => {
        e.preventDefault();
        navigate(`/chat/${chatId}`);
        
        // Refresh recent chats in sidebar
        setTimeout(() => {
            if (window.refreshRecentChats) {
                window.refreshRecentChats();
            }
        }, 100);
    };
    
    const handleSubmit = async () => {
        if (!name.trim()) {
            setError('Chat name is required');
            return;
        }
        
        if (!/^[a-zA-Z0-9-]+$/.test(name)) {
            setError('Chat name can only contain letters, numbers, and hyphens (no spaces)');
            return;
        }
        
        try {
            setLoading(true);
            const result = await updateChatName(chatId, name);
            setVisible(false);
            if (onSuccess) {
                onSuccess(result);
            }
        } catch (err) {
            setError(err.message || 'Failed to update chat name');
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <>
            <SpaceBetween direction="horizontal" size="xs" alignItems="center">
                <Link 
                    href="#" 
                    onFollow={handleChatClick}
                >
                    {displayName}
                </Link>
                <Button
                    iconName="edit"
                    variant="icon"
                    onClick={handleEditClick}
                    ariaLabel="Edit chat name"
                />
            </SpaceBetween>
            
            <Modal
                visible={visible}
                onDismiss={() => setVisible(false)}
                header="Edit Chat Name"
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
                                onClick={handleSubmit}
                                loading={loading}
                            >
                                Save
                            </Button>
                        </SpaceBetween>
                    </Box>
                }
            >
                <SpaceBetween size="m">
                    <Input
                        value={name}
                        onChange={({ detail }) => {
                            setName(detail.value);
                            setError('');
                        }}
                        placeholder="Enter chat name"
                        invalid={!!error}
                        errorText={error}
                    />
                    <Box color="text-body-secondary">
                        Chat name can only contain letters, numbers, and hyphens (no spaces).
                    </Box>
                </SpaceBetween>
            </Modal>
        </>
    );
}

export default ChatNameCell;
