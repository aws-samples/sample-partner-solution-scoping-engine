import React, { useState } from 'react';
import Button from '@cloudscape-design/components/button';
import SOWFeedbackModal from './SOWFeedbackModal';

/**
 * Tool for rejecting SOW documents
 */
function SOWRejectionTool({ chatId, sowData, onSuccess }) {
    const [modalVisible, setModalVisible] = useState(false);
    
    return (
        <>
            <Button
                iconName="status-negative"
                variant="icon"
                onClick={(e) => {
                    e.stopPropagation();
                    setModalVisible(true);
                }}
                ariaLabel="Reject SOW"
                title="Reject this Statement of Work"
            />
            
            <SOWFeedbackModal
                visible={modalVisible}
                onDismiss={() => setModalVisible(false)}
                chatId={chatId}
                sowData={sowData}
                feedbackType="rejected"
                onSuccess={onSuccess}
            />
        </>
    );
}

export default SOWRejectionTool;