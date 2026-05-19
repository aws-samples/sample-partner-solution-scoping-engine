import React, { useState } from 'react';
import Button from '@cloudscape-design/components/button';
import SAFeedbackModal from './SAFeedbackModal';

/**
 * Tool for submitting positive SA feedback
 */
function SAThumbsUpTool({ chatId, onSuccess }) {
    const [modalVisible, setModalVisible] = useState(false);
    
    return (
        <>
            <Button
                iconName="thumbs-up"
                variant="icon"
                onClick={(e) => {
                    e.stopPropagation();
                    setModalVisible(true);
                }}
                ariaLabel="Positive feedback"
            />
            
            <SAFeedbackModal
                visible={modalVisible}
                onDismiss={() => setModalVisible(false)}
                chatId={chatId}
                feedbackType="positive"
                onSuccess={onSuccess}
            />
        </>
    );
}

export default SAThumbsUpTool;
