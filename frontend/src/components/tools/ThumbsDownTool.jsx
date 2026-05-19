import React, { useState } from 'react';
import Button from '@cloudscape-design/components/button';
import FeedbackModal from './FeedbackModal';

/**
 * Tool for submitting negative feedback
 */
function ThumbsDownTool({ chatId, onSuccess }) {
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
            
            <FeedbackModal
                visible={modalVisible}
                onDismiss={() => setModalVisible(false)}
                chatId={chatId}
                feedbackType="negative"
                onSuccess={onSuccess}
            />
        </>
    );
}

export default ThumbsDownTool;
