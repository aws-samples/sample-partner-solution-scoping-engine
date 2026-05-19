import React, { useState } from 'react';
import Modal from '@cloudscape-design/components/modal';
import Box from '@cloudscape-design/components/box';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Button from '@cloudscape-design/components/button';
import Select from '@cloudscape-design/components/select';
import Textarea from '@cloudscape-design/components/textarea';
import { saveFeedback } from '../../services/chatService';

/**
 * Reusable modal component for submitting feedback
 */
function FeedbackModal({ 
    visible, 
    onDismiss, 
    chatId, 
    feedbackType, 
    onSuccess 
}) {
    const [provider, setProvider] = useState(null);
    const [detail, setDetail] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    
    const providerOptions = [
        { label: 'Self', value: 'User' },
        { label: 'Partner', value: 'Partner' },
        { label: 'Customer', value: 'Customer' }
    ];
    
    const handleSubmit = async () => {
        if (!provider) {
            setError('Please select a feedback provider');
            return;
        }
        
        try {
            setLoading(true);
            const feedback = {
                type: feedbackType,
                provider: provider.value,
                detail: detail.trim()
            };
            
            const result = await saveFeedback(chatId, feedback);
            
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
        setProvider(null);
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
                <Select
                    selectedOption={provider}
                    onChange={({ detail }) => {
                        setProvider(detail.selectedOption);
                        setError('');
                    }}
                    options={providerOptions}
                    placeholder="Select feedback provider"
                    invalid={!!error && !provider}
                    errorText={!provider ? error : ''}
                />
                
                <Textarea
                    value={detail}
                    onChange={({ detail }) => setDetail(detail.value)}
                    placeholder={placeholder}
                    rows={4}
                />
                
                {error && provider && (
                    <Box color="text-status-error">
                        {error}
                    </Box>
                )}
            </SpaceBetween>
        </Modal>
    );
}

export default FeedbackModal;
