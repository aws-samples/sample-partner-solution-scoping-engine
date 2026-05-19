import React, { useState } from 'react';
import Button from '@cloudscape-design/components/button';
import FeedbackModal from './FeedbackModal';

/**
 * Tool for submitting positive feedback
 */
function ThumbsUpTool({ chatId, onSuccess }) {
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
            
            <FeedbackModal
                visible={modalVisible}
                onDismiss={() => setModalVisible(false)}
                chatId={chatId}
                feedbackType="positive"
                onSuccess={onSuccess}
            />
        </>
    );
}

export default ThumbsUpTool;
