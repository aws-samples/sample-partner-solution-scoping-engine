import React, { useState } from 'react';
import Modal from '@cloudscape-design/components/modal';
import Box from '@cloudscape-design/components/box';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Button from '@cloudscape-design/components/button';
import Textarea from '@cloudscape-design/components/textarea';
import { saveSAFeedback } from '../../services/chatService';

/**
 * Modal component for submitting Solutions Architect feedback
 */
function SAFeedbackModal({ 
    visible, 
    onDismiss, 
    chatId, 
    feedbackType, 
    onSuccess 
}) {
    const [detail, setDetail] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    
    const handleSubmit = async () => {
        try {
            setLoading(true);
            const feedback = {
                type: feedbackType,
                provider: 'Solutions Architect',
                detail: detail.trim()
            };
            
            const result = await saveSAFeedback(chatId, feedback);
            
            if (onSuccess) {
                onSuccess(result);
            }
            
            onDismiss();
        } catch (err) {
            setError(err.message || 'Failed to submit feedback');
        } finally {
            setLoading(false);
        }
    };
    
    const handleDismiss = () => {
        setDetail('');
        setError('');
        onDismiss();
    };
    
    const isPositive = feedbackType === 'positive';
    const title = isPositive ? 'Positive Feedback' : 'Negative Feedback';
    const placeholder = isPositive 
        ? 'What was good about this solution?' 
        : 'What was the issue with this solution that caused negative feedback?';
    
    return (
        <Modal
            visible={visible}
            onDismiss={handleDismiss}
            header={title}
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
                <Box>
                    <strong>Feedback Provider:</strong> Solutions Architect
                </Box>
                
                <Textarea
                    value={detail}
                    onChange={({ detail }) => setDetail(detail.value)}
                    placeholder={placeholder}
                    rows={4}
                />
                
                {error && (
                    <Box color="text-status-error">
                        {error}
                    </Box>
                )}
            </SpaceBetween>
        </Modal>
    );
}

export default SAFeedbackModal;
