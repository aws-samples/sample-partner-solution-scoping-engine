import React, { useState } from 'react';
import Button from '@cloudscape-design/components/button';
import SAFeedbackModal from './SAFeedbackModal';

/**
 * Tool for submitting negative SA feedback
 */
function SAThumbsDownTool({ chatId, onSuccess }) {
    const [modalVisible, setModalVisible] = useState(false);
    
    return (
        <>
            <Button
                iconName="thumbs-down"
                variant="icon"
                onClick={(e) => {
                    e.stopPropagation();
                    setModalVisible(true);
                }}
                ariaLabel="Negative feedback"
            />
            
            <SAFeedbackModal
                visible={modalVisible}
                onDismiss={() => setModalVisible(false)}
                chatId={chatId}
                feedbackType="negative"
                onSuccess={onSuccess}
            />
        </>
    );
}

export default SAThumbsDownTool;
