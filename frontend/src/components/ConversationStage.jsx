import React, { useState, useEffect } from 'react';
import apiClient from '../services/apiClient';
import { getChatSession, requestSAReview, cancelSAReview } from '../services/chatService';
import SAReviewCommentModal from './tools/SAReviewCommentModal';

/**
 * ConversationStage component that displays the current conversation stage and review stage
 */
const ConversationStage = ({ chatId, refreshTrigger, loading = false, onAddSystemMessage, onChatDataUpdate }) => {
    const [currentStage, setCurrentStage] = useState('');
    const [reviewStage, setReviewStage] = useState('');
    const [reviewStatus, setReviewStatus] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [isPolling, setIsPolling] = useState(false);
    const [circleOpacity, setCircleOpacity] = useState(1);
    const [isReviewChat, setIsReviewChat] = useState(false);
    const [canRequest, setCanRequest] = useState(false);
    const [canCancel, setCanCancel] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [pendingAction, setPendingAction] = useState(null);
    const [actionLoading, setActionLoading] = useState(false);

    // Helper function to get display name for stage
    const getStageDisplayName = (stage) => {
        switch (stage) {
            case 'INITIAL': return 'Initial';
            case 'GATHERING_INFO': return 'Gathering Info';
            case 'SOLUTION_PROPOSED': return 'Solution Proposed';
            case 'SOLUTION_FINALIZED': return 'Solution Finalized';
            default: return 'Initial';
        }
    };

    // Helper function to calculate progress percentage
    const getStageProgress = (stage) => {
        switch (stage) {
            case 'INITIAL': return 25;
            case 'GATHERING_INFO': return 50;
            case 'SOLUTION_PROPOSED': return 75;
            case 'SOLUTION_FINALIZED': return 100;
            default: return 25;
        }
    };

    // Check if review status should be blinking (active states)
    const shouldBlink = (status) => {
        return ['requested', 'in_progress'].includes(status);
    };

    // Polling effect for active review states
    useEffect(() => {
        let pollInterval;
        let blinkInterval;
        
        if (shouldBlink(reviewStage)) {
            setIsPolling(true);
            pollInterval = setInterval(() => {
                fetchChatStage(false); // Don't show loading during polling
            }, 5000); // Poll every 5 seconds
            
            // Blink the circle
            blinkInterval = setInterval(() => {
                setCircleOpacity(prev => prev === 1 ? 0.3 : 1);
            }, 800); // Blink every 800ms
        } else {
            setIsPolling(false);
            setCircleOpacity(1);
        }
        
        return () => {
            if (pollInterval) {
                clearInterval(pollInterval);
            }
            if (blinkInterval) {
                clearInterval(blinkInterval);
            }
        };
    }, [reviewStage, chatId]);

    // Polling effect for review chats to monitor original chat status
    useEffect(() => {
        let reviewPollInterval;
        
        if (isReviewChat && reviewStage === 'in_progress') {
            // Poll the original chat to see if review was cancelled
            reviewPollInterval = setInterval(async () => {
                try {
                    const chatData = await getChatSession(chatId);
                    const originalChatId = chatData.source_chat_id;
                    
                    if (originalChatId) {
                        const originalChatData = await getChatSession(originalChatId);
                        const originalReviewStatus = originalChatData.review_status;
                        
                        // If original chat review status is no longer 'in_progress', the review was cancelled
                        if (originalReviewStatus !== 'in_progress') {
                            // Add system message
                            if (onAddSystemMessage) {
                                onAddSystemMessage('Review cancelled by customer.');
                            }
                            
                            // Update this review chat's status using the same API as the modal
                            try {
                                await cancelSAReview(chatId, 'Cancelled by customer');
                                // Refresh to get updated data
                                fetchChatStage(false);
                                
                                // Refresh recent reviews in sidebar
                                if (window.refreshRecentChats) {
                                    window.refreshRecentChats();
                                }
                            } catch (updateError) {
                                console.error('Error updating review chat status:', updateError);
                                // Still refresh even if update fails
                                fetchChatStage(false);
                            }
                        }
                    }
                } catch (error) {
                    console.error('Error polling original chat status:', error);
                }
            }, 10000); // Poll every 10 seconds for review chats
        }
        
        return () => {
            if (reviewPollInterval) {
                clearInterval(reviewPollInterval);
            }
        };
    }, [isReviewChat, reviewStage, chatId]);

    // Helper function to get user-friendly review status names
    const getReviewDisplayName = (status) => {
        switch (status) {
            case 'none': return 'None';
            case 'requested': return 'Requested';
            case 'in_progress': return 'In Progress';
            case 'ready_for_merge': return 'Ready for Merge';
            case 'complete_no_changes': return 'OK As Is';
            case 'ready_for_user': return 'Approved';
            case 'reassigned': return 'Reassigned';
            case 'rejected': return 'Rejected';
            case 'merged': return 'Merged';
            case 'dismissed': return 'Dismissed';
            case 'cancelled': return 'Cancelled';
            case 'Not Eligible': return 'Not Eligible';
            default: return status || 'Not Eligible';
        }
    };

    // Helper function to get colors for review status
    const getReviewStatusColor = (status) => {
        switch (status) {
            case 'none': return '#6b7280'; // gray
            case 'requested': return '#f59e0b'; // amber
            case 'in_progress': return '#eab308'; // yellow
            case 'ready_for_merge': return '#8b5cf6'; // purple
            case 'complete_no_changes': return '#10b981'; // emerald
            case 'ready_for_user': return '#10b981'; // emerald
            case 'reassigned': return '#f59e0b'; // amber
            case 'rejected': return '#ef4444'; // red
            case 'merged': return '#059669'; // green
            case 'dismissed': return '#6b7280'; // gray
            case 'cancelled': return '#6b7280'; // gray
            case 'Not Eligible': return '#6b7280'; // gray
            default: return '#6b7280'; // gray
        }
    };

    // Fetch current conversation stage and review status
    const fetchChatStage = async (showLoading = true) => {
        try {
            if (showLoading) {
                setIsLoading(true);
            }
            const chatData = await getChatSession(chatId);
            const stage = chatData.stage || '';
            const newReviewStatus = chatData.review_status || '';
            const isReviewChatFlag = chatData.source_chat_id; // If this exists, it's an SA review chat
            
            // Check if review status changed
            const statusChanged = newReviewStatus !== reviewStatus;
            
            setCurrentStage(stage);
            setReviewStatus(newReviewStatus);
            setIsReviewChat(!!isReviewChatFlag);
            
            // Set defaults
            let reviewStageDisplay = '';
            let canRequestReview = false;
            let canCancelRequest = false;
            
            if (isReviewChatFlag) {
                // This is an SA review chat - use the raw status for color matching
                reviewStageDisplay = newReviewStatus || 'in_progress';
            } else if (!newReviewStatus || newReviewStatus === 'none') {
                // No record in db
                if (stage === 'SOLUTION_PROPOSED' || stage === 'SOLUTION_FINALIZED') {
                    reviewStageDisplay = 'Ready to Request';
                    canRequestReview = true;
                } else {
                    reviewStageDisplay = 'Not Eligible';
                }
            } else {
                // Use the actual status
                reviewStageDisplay = newReviewStatus;
                
                // Determine button availability based on status
                if (newReviewStatus === 'requested' || newReviewStatus === 'in_progress') {
                    canCancelRequest = true;
                } else if (newReviewStatus === 'rejected' || 
                          (newReviewStatus !== 'ready_for_merge' && newReviewStatus !== 'ready_for_user')) {
                    // Can request again for rejected or completed statuses
                    canRequestReview = (stage === 'SOLUTION_PROPOSED' || stage === 'SOLUTION_FINALIZED');
                }
            }
            
            setReviewStage(reviewStageDisplay);
            setCanRequest(canRequestReview);
            setCanCancel(canCancelRequest);
            if (statusChanged && onChatDataUpdate) {
                onChatDataUpdate(chatData);
            }
            
            console.debug(`Current conversation stage: ${stage}, review_status: ${newReviewStatus}, display: ${reviewStageDisplay}`);
        } catch (error) {
            console.error('Error fetching chat stage:', error);
        } finally {
            if (showLoading) {
                setIsLoading(false);
            }
        }
    };

    const handleSAAction = async (action, comment = '') => {
        try {
            const requestBody = {
                action,
                sa_copy_chat_id: chatId,
                comment: comment.trim()
            };
            
            const result = await apiClient.post('/sa-review/actions', requestBody);
            
            if (!result.success) {
                throw new Error(result.error);
            }

            // Refresh the chat stage after action
            fetchChatStage();
        } catch (error) {
            console.error('SA action error:', error);
        }
    };

    const showModal = (action) => {
        setPendingAction(action);
        setModalVisible(true);
    };

    const handleModalConfirm = async (approvalData) => {
        if (!pendingAction) return;
        
        setActionLoading(true);
        try {
            let result;
            
            // Extract comment and documentIds from approvalData
            let comment = '';
            let documentIds = [];
            
            if (typeof approvalData === 'object' && approvalData !== null) {
                comment = approvalData.comment || '';
                documentIds = approvalData.documentIds || [];
            } else {
                comment = approvalData || '';
            }
            
            if (pendingAction === 'request') {
                result = await requestSAReview(chatId, comment);
            } else if (pendingAction === 'cancel') {
                result = await cancelSAReview(chatId, comment);
            } else {
                // SA actions: mark_ready, complete_no_changes, reject, reassign
                const requestBody = {
                    action: pendingAction,
                    sa_copy_chat_id: chatId,
                    comment: comment,
                    documentIds: documentIds
                };
                
                result = await apiClient.post('/sa-review/actions', requestBody);
                
                if (!result.success) {
                    throw new Error(result.error);
                }
                
                // Add system message to frontend UI immediately
                let saSystemMessage = '';
                switch (pendingAction) {
                    case 'mark_ready':
                        saSystemMessage = 'Marked as ready for user';
                        break;
                    case 'complete_no_changes':
                        saSystemMessage = 'Approved solution as-is';
                        break;
                    case 'reject':
                        saSystemMessage = 'Rejected solution';
                        break;
                    case 'reassign':
                        saSystemMessage = 'Reassigned to another SA';
                        break;
                }
                if (comment.trim()) {
                    saSystemMessage += ` - Comment: ${comment.trim()}`;
                }
                
                if (onAddSystemMessage) {
                    onAddSystemMessage(saSystemMessage);
                }
            }
            
            if (result?.system_message && onAddSystemMessage) {
                onAddSystemMessage(result.system_message);
            }
            fetchChatStage();
            
            // Refresh main chat data and recent chats after request/cancel actions
            if (onChatDataUpdate) {
                onChatDataUpdate();
            }
            
            if (window.refreshRecentChats) {
                window.refreshRecentChats();
            }
            
            // Refresh main chat data for disabled state after SA actions
            if (onChatDataUpdate && ['mark_ready', 'complete_no_changes', 'reject', 'reassign'].includes(pendingAction)) {
                onChatDataUpdate();
            }
            
            // Refresh recent chats/reviews in sidebar
            if (window.refreshRecentChats) {
                window.refreshRecentChats();
            }
        } catch (error) {
            console.error(`Error ${pendingAction}ing SA review:`, error);
        } finally {
            setActionLoading(false);
            setModalVisible(false);
            setPendingAction(null);
        }
    };

    const handleModalDismiss = () => {
        setModalVisible(false);
        setPendingAction(null);
    };

    useEffect(() => {
        if (chatId) {
            fetchChatStage();
        }
    }, [chatId]);

    // Re-fetch stage when refreshTrigger changes (after assistant responses)
    useEffect(() => {
        if (chatId && refreshTrigger > 0) {
            console.log(`Refreshing chat stage due to trigger: ${refreshTrigger}`);
            fetchChatStage();
        }
    }, [refreshTrigger, chatId]);

    return (
        <div style={{ 
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '12px', 
            color: '#5f6b7a', 
            fontWeight: '500',
            padding: '4px 8px',
            backgroundColor: '#f2f3f3',
            borderRadius: '4px',
            border: '1px solid #d5dbdb',
            margin: '8px 0'
        }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                <div style={{ 
                    flex: 1, 
                    height: '20px', 
                    backgroundColor: '#c0c0c0', 
                    borderRadius: '8px',
                    overflow: 'hidden',
                    maxWidth: '180px',
                    position: 'relative',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                }}>
                    <div style={{
                        position: 'absolute',
                        left: 0,
                        top: 0,
                        height: '100%',
                        backgroundColor: '#0073bb',
                        width: `${getStageProgress(currentStage)}%`,
                        transition: 'width 0.3s ease',
                        borderRadius: '8px'
                    }} />
                    <span style={{ 
                        position: 'relative', 
                        zIndex: 1, 
                        fontSize: '11px', 
                        fontWeight: '500',
                        color: getStageProgress(currentStage) >= 50 ? '#fff' : '#333'
                    }}>
                        {getStageDisplayName(currentStage)}
                    </span>
                </div>
                
                <div style={{ margin: '0 16px', display: 'flex', gap: '8px' }}>
                    {isLoading ? 'Loading...' : (
                        <>
                            {!isReviewChat && (
                                <>
                                    <button 
                                        style={{
                                            padding: '4px 12px',
                                            fontSize: '11px',
                                            backgroundColor: (canRequest && !loading) ? '#0073bb' : '#cccccc',
                                            color: (canRequest && !loading) ? 'white' : '#666666',
                                            border: 'none',
                                            borderRadius: '6px',
                                            cursor: canRequest ? 'pointer' : 'not-allowed',
                                            boxShadow: canRequest ? '0 2px 4px rgba(0,0,0,0.1)' : 'none',
                                            fontWeight: '500'
                                        }}
                                        disabled={!canRequest}
                                        onMouseOver={(e) => {
                                            if (canRequest && !loading) e.target.style.backgroundColor = '#005a9e';
                                        }}
                                        onMouseOut={(e) => {
                                            if (canRequest && !loading) e.target.style.backgroundColor = '#0073bb';
                                        }}
                                        onClick={() => {
                                            if (!canRequest || loading) return;
                                            showModal('request');
                                        }}
                                    >
                                        {(reviewStage === 'Cancelled' || reviewStage === 'Rejected') && canRequest ? 'Request Again!' : 'Request Review'}
                                    </button>
                                    
                                    <button 
                                        style={{
                                            padding: '4px 12px',
                                            fontSize: '11px',
                                            backgroundColor: (canCancel && !loading) ? '#dc3545' : '#cccccc',
                                            color: (canCancel && !loading) ? 'white' : '#666666',
                                            border: 'none',
                                            borderRadius: '6px',
                                            cursor: (canCancel && !loading) ? 'pointer' : 'not-allowed',
                                            boxShadow: (canCancel && !loading) ? '0 2px 4px rgba(0,0,0,0.1)' : 'none',
                                    fontWeight: '500'
                                }}
                                disabled={!canCancel || loading}
                                onMouseOver={(e) => {
                                    if (canCancel && !loading) e.target.style.backgroundColor = '#c82333';
                                }}
                                onMouseOut={(e) => {
                                    if (canCancel && !loading) e.target.style.backgroundColor = '#dc3545';
                                }}
                                onClick={() => {
                                    if (!canCancel || loading) return;
                                    showModal('cancel');
                                }}
                                    >
                                        Cancel Review
                                    </button>
                                </>
                            )}
                            {isReviewChat && (
                                <>
                                    <button
                                        style={{
                                            padding: '4px 12px',
                                            fontSize: '11px',
                                            width: '120px',
                                            backgroundColor: reviewStatus === 'in_progress' ? '#fd7e14' : '#cccccc',
                                            color: reviewStatus === 'in_progress' ? 'white' : '#666666',
                                            border: 'none',
                                            borderRadius: '6px',
                                            cursor: reviewStatus === 'in_progress' ? 'pointer' : 'not-allowed',
                                            boxShadow: reviewStatus === 'in_progress' ? '0 2px 4px rgba(0,0,0,0.1)' : 'none',
                                            fontWeight: '500'
                                        }}
                                        disabled={reviewStatus !== 'in_progress'}
                                        onMouseOver={(e) => {
                                            if (reviewStatus === 'in_progress') e.target.style.backgroundColor = '#e8681a';
                                        }}
                                        onMouseOut={(e) => {
                                            if (reviewStatus === 'in_progress') e.target.style.backgroundColor = '#fd7e14';
                                        }}
                                        onClick={() => showModal('mark_ready')}
                                    >
                                        Ready For User
                                    </button>
                                    
                                    <button
                                        style={{
                                            padding: '4px 12px',
                                            fontSize: '11px',
                                            width: '120px',
                                            backgroundColor: reviewStatus === 'in_progress' ? '#28a745' : '#cccccc',
                                            color: reviewStatus === 'in_progress' ? 'white' : '#666666',
                                            border: 'none',
                                            borderRadius: '6px',
                                            cursor: reviewStatus === 'in_progress' ? 'pointer' : 'not-allowed',
                                            boxShadow: reviewStatus === 'in_progress' ? '0 2px 4px rgba(0,0,0,0.1)' : 'none',
                                            fontWeight: '500'
                                        }}
                                        disabled={reviewStatus !== 'in_progress'}
                                        onMouseOver={(e) => {
                                            if (reviewStatus === 'in_progress') e.target.style.backgroundColor = '#218838';
                                        }}
                                        onMouseOut={(e) => {
                                            if (reviewStatus === 'in_progress') e.target.style.backgroundColor = '#28a745';
                                        }}
                                        onClick={() => showModal('complete_no_changes')}
                                    >
                                        Approve As-Is
                                    </button>
                                    
                                    <button
                                        style={{
                                            padding: '4px 12px',
                                            fontSize: '11px',
                                            width: '120px',
                                            backgroundColor: reviewStatus === 'in_progress' ? '#dc3545' : '#cccccc',
                                            color: reviewStatus === 'in_progress' ? 'white' : '#666666',
                                            border: 'none',
                                            borderRadius: '6px',
                                            cursor: reviewStatus === 'in_progress' ? 'pointer' : 'not-allowed',
                                            boxShadow: reviewStatus === 'in_progress' ? '0 2px 4px rgba(0,0,0,0.1)' : 'none',
                                            fontWeight: '500'
                                        }}
                                        disabled={reviewStatus !== 'in_progress'}
                                        onMouseOver={(e) => {
                                            if (reviewStatus === 'in_progress') e.target.style.backgroundColor = '#c82333';
                                        }}
                                        onMouseOut={(e) => {
                                            if (reviewStatus === 'in_progress') e.target.style.backgroundColor = '#dc3545';
                                        }}
                                        onClick={() => showModal('reject')}
                                    >
                                        Reject
                                    </button>
                                    
                                    <button
                                        style={{
                                            padding: '4px 12px',
                                            fontSize: '11px',
                                            width: '120px',
                                            backgroundColor: reviewStatus === 'in_progress' ? '#6c757d' : '#cccccc',
                                            color: reviewStatus === 'in_progress' ? 'white' : '#666666',
                                            border: 'none',
                                            borderRadius: '6px',
                                            cursor: reviewStatus === 'in_progress' ? 'pointer' : 'not-allowed',
                                            boxShadow: reviewStatus === 'in_progress' ? '0 2px 4px rgba(0,0,0,0.1)' : 'none',
                                            fontWeight: '500'
                                        }}
                                        disabled={reviewStatus !== 'in_progress'}
                                        onMouseOver={(e) => {
                                            if (reviewStatus === 'in_progress') e.target.style.backgroundColor = '#5a6268';
                                        }}
                                        onMouseOut={(e) => {
                                            if (reviewStatus === 'in_progress') e.target.style.backgroundColor = '#6c757d';
                                        }}
                                        onClick={() => showModal('reassign')}
                                    >
                                        Reassign
                                    </button>
                                </>
                            )}
                        </>
                    )}
                </div>
                
                <div style={{ fontSize: '12px' }}>
                    <span 
                        style={{
                            display: 'inline-block',
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            backgroundColor: getReviewStatusColor(reviewStage),
                            marginRight: '6px',
                            opacity: isPolling ? circleOpacity : 1,
                            transition: 'opacity 0.5s ease-in-out'
                        }}
                    />
                    <span>
                        {getReviewDisplayName(reviewStage)}
                    </span>
                </div>
            </div>
            
            <SAReviewCommentModal
                visible={modalVisible}
                onDismiss={handleModalDismiss}
                onConfirm={handleModalConfirm}
                action={pendingAction}
                loading={actionLoading}
                chatId={chatId}
            />
        </div>
    );
};

export default ConversationStage;
