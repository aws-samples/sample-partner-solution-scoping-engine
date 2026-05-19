import React, { useState, useEffect } from 'react';
import { Alert, Button, SpaceBetween } from '@cloudscape-design/components';
import apiClient from '../services/apiClient';

const SANotification = ({ chatId, onMergeComplete }) => {
  const [notification, setNotification] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (chatId) {
      checkNotification();
    }
  }, [chatId]);

  const checkNotification = async () => {
    try {
      const response = await fetch(`/api/sa-review/notification/${chatId}`, {
        credentials: 'include'
      });
      const result = await response.json();
      
      // Don't show notifications if this is not the user's chat or if there's no notification
      if (result.success && result.notification?.status !== 'no_notification' && result.notification?.status !== 'not_owner') {
        setNotification(result.notification);
      } else {
        setNotification(null);
      }
    } catch (err) {
      console.error('Error checking notification:', err);
      setNotification(null);
    }
  };

  const handleMerge = async () => {
    setLoading(true);
    try {
      const result = await apiClient.post('/sa-review/merge', { chat_id: chatId });
      
      if (result.success) {
        setNotification(null);
        onMergeComplete?.(result);
      } else {
        console.error('Merge failed:', result.error);
      }
    } catch (err) {
      console.error('Merge failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDismiss = async () => {
    setLoading(true);
    try {
      const result = await apiClient.post('/sa-review/dismiss', { chat_id: chatId });
      
      if (result.success) {
        setNotification(null);
      } else {
        console.error('Dismiss failed:', result.error);
      }
    } catch (err) {
      console.error('Dismiss failed:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!notification) return null;

  const saReviewer = notification.sa_reviewer || 'Unknown SA';

  return (
    <Alert
      type={notification.status === 'ready_for_merge' ? 'info' : 'success'}
      header={`SA Review: ${saReviewer}`}
      action={
        notification.status === 'ready_for_merge' ? (
          <SpaceBetween direction="horizontal" size="s">
            <Button variant="primary" loading={loading} onClick={handleMerge}>
              Accept Changes
            </Button>
            <Button loading={loading} onClick={handleDismiss}>
              Dismiss
            </Button>
          </SpaceBetween>
        ) : (
          <Button loading={loading} onClick={handleDismiss}>
            Dismiss
          </Button>
        )
      }
    >
      {notification.message}
    </Alert>
  );
};

export default SANotification;
