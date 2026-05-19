import React, { useState } from 'react';
import Button from '@cloudscape-design/components/button';
import Modal from '@cloudscape-design/components/modal';
import Box from '@cloudscape-design/components/box';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Input from '@cloudscape-design/components/input';
import { updateChatName } from '../../services/chatService';

/**
 * Tool for editing a chat name
 */
function EditChatNameTool({ chatId, currentName, onSuccess }) {
    const [visible, setVisible] = useState(false);
    const [name, setName] = useState(currentName || '');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    
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
            <Button
                iconName="edit"
                variant="icon"
                onClick={(e) => {
                    e.stopPropagation();
                    setName(currentName || '');
                    setError('');
                    setVisible(true);
                }}
                ariaLabel="Edit chat name"
            />
            
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

export default EditChatNameTool;
