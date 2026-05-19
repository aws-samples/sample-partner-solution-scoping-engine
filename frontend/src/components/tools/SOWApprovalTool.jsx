import React, { useState } from 'react';
import Button from '@cloudscape-design/components/button';
import SOWFeedbackModal from './SOWFeedbackModal';

/**
 * Tool for approving SOW documents
 */
function SOWApprovalTool({ chatId, sowData, onSuccess }) {
    const [modalVisible, setModalVisible] = useState(false);
    
    return (
        <>
            <Button
                iconName="status-positive"
                variant="icon"
                onClick={(e) => {
                    e.stopPropagation();
                    setModalVisible(true);
                }}
                ariaLabel="Approve SOW"
                title="Approve this Statement of Work"
            />
            
            <SOWFeedbackModal
                visible={modalVisible}
                onDismiss={() => setModalVisible(false)}
                chatId={chatId}
                sowData={sowData}
                feedbackType="approved"
                onSuccess={onSuccess}
            />
        </>
    );
}

export default SOWApprovalTool;