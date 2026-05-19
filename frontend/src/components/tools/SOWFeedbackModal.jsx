import React, { useState } from 'react';
import Modal from '@cloudscape-design/components/modal';
import Box from '@cloudscape-design/components/box';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Button from '@cloudscape-design/components/button';
import Textarea from '@cloudscape-design/components/textarea';
import ColumnLayout from '@cloudscape-design/components/column-layout';
import { submitSOWFeedback } from '../../services/sowService';

/**
 * Modal component for submitting SOW feedback (approval/rejection)
 */
function SOWFeedbackModal({ 
    visible, 
    onDismiss, 
    chatId, 
    sowData,
    feedbackType, 
    onSuccess 
}) {
    const [comments, setComments] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    
    const handleSubmit = async () => {
        try {
            setLoading(true);
            setError('');
            
            // Validate required comments for rejection
            if (feedbackType === 'rejected' && !comments.trim()) {
                setError('Comments are required when rejecting a SOW');
                return;
            }
            
            const feedback = {
                feedback_type: feedbackType,
                comments: comments.trim()
            };
            
            const result = await submitSOWFeedback(chatId, feedback);
            
            if (onSuccess) {
                onSuccess(result);
            }
            
            onDismiss();
        } catch (err) {
            setError(err.message || 'Failed to submit SOW feedback');
        } finally {
            setLoading(false);
        }
    };
    
    const handleDismiss = () => {
        setComments('');
        setError('');
        onDismiss();
    };
    
    const isApproval = feedbackType === 'approved';
    const title = isApproval ? 'Approve Statement of Work' : 'Reject Statement of Work';
    const placeholder = isApproval 
        ? 'Optional: Add comments about what was good about this SOW...' 
        : 'Please explain what issues need to be addressed in this SOW...';
    const submitButtonText = isApproval ? 'Approve' : 'Reject';
    const submitButtonVariant = isApproval ? 'primary' : 'normal';
    
    // Format currency
    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount || 0);
    };
    
    return (
        <Modal
            visible={visible}
            onDismiss={handleDismiss}
            header={title}
            size="medium"
            footer={
                <Box float="right">
                    <SpaceBetween direction="horizontal" size="xs">
                        <Button 
                            variant="link" 
                            onClick={handleDismiss}
                            disabled={loading}
                        >
                            Cancel
                        </Button>
                        <Button 
                            variant={submitButtonVariant}
                            onClick={handleSubmit}
                            loading={loading}
                        >
                            {submitButtonText}
                        </Button>
                    </SpaceBetween>
                </Box>
            }
        >
            <SpaceBetween size="m">
                {/* SOW Summary */}
                <Box>
                    <h3>SOW Summary</h3>
                    <ColumnLayout columns={2} variant="text-grid">
                        <div>
                            <Box variant="awsui-key-label">Project</Box>
                            <div>{sowData.project_title || sowData.chat_name}</div>
                        </div>
                        <div>
                            <Box variant="awsui-key-label">Customer</Box>
                            <div>{sowData.customer_name}</div>
                        </div>
                        <div>
                            <Box variant="awsui-key-label">Template Type</Box>
                            <div>{sowData.template_type}</div>
                        </div>
                        <div>
                            <Box variant="awsui-key-label">Estimated Cost</Box>
                            <div>{formatCurrency(sowData.estimated_project_cost)}</div>
                        </div>
                        <div>
                            <Box variant="awsui-key-label">Partner</Box>
                            <div>{sowData.partner_name}</div>
                        </div>
                        <div>
                            <Box variant="awsui-key-label">Created By</Box>
                            <div>{sowData.created_by}</div>
                        </div>
                    </ColumnLayout>
                </Box>
                
                {/* Feedback Section */}
                <Box>
                    <h3>
                        {isApproval ? 'Approval Comments' : 'Rejection Feedback'}
                        {!isApproval && <span style={{ color: 'red' }}> *</span>}
                    </h3>
                    <Textarea
                        value={comments}
                        onChange={({ detail }) => setComments(detail.value)}
                        placeholder={placeholder}
                        rows={4}
                        invalid={!isApproval && !comments.trim() && error}
                    />
                    {!isApproval && (
                        <Box variant="small" color="text-status-subdued">
                            * Comments are required when rejecting a SOW
                        </Box>
                    )}
                </Box>
                
                {error && (
                    <Box color="text-status-error">
                        {error}
                    </Box>
                )}
                
                {/* Action Confirmation */}
                <Box>
                    <Box variant="awsui-key-label">Action</Box>
                    <div>
                        {isApproval 
                            ? 'This SOW will be marked as approved and can proceed to customer delivery.'
                            : 'This SOW will be marked as rejected and returned for revision.'
                        }
                    </div>
                </Box>
            </SpaceBetween>
        </Modal>
    );
}

export default SOWFeedbackModal;