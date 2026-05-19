import { useState, useEffect } from 'react';
import Container from '@cloudscape-design/components/container';
import Header from '@cloudscape-design/components/header';
import Table from '@cloudscape-design/components/table';
import Box from '@cloudscape-design/components/box';
import Button from '@cloudscape-design/components/button';
import SpaceBetween from '@cloudscape-design/components/space-between';
import { useNavigate } from 'react-router-dom';
import { getMyReviews } from '../services/chatService';

const MyReviewsPage = () => {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchMyReviews = async () => {
      try {
        const data = await getMyReviews();
        setReviews(data.chats || []);
      } catch (error) {
        console.error('Error fetching my reviews:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchMyReviews();
  }, []);

  const getStatusBadge = (status) => {
    const colors = {
      'in_progress': 'orange',
      'ready_for_merge': 'blue',
      'complete_no_changes': 'green',
      'ready_for_user': 'green',
      'rejected': 'red',
      'dismissed': 'grey'
    };
    return (
      <span style={{ 
        color: colors[status] || 'black',
        fontWeight: 'bold'
      }}>
        {status?.replace(/_/g, ' ') || 'Unknown'}
      </span>
    );
  };

  return (
    <Container
      header={
        <Header variant="h1">
          My Reviews
        </Header>
      }
    >
      <Table
        columnDefinitions={[
          {
            id: 'chatName',
            header: 'Chat Name',
            cell: item => (
              <Button
                variant="link"
                onClick={() => {
                  navigate(`/chat/${item.chatId}`);
                  setTimeout(() => {
                    if (window.refreshRecentChats) {
                      window.refreshRecentChats();
                    }
                  }, 100);
                }}
              >
                {item.chatName || `Chat ${item.chatId?.substring(0, 8)}...`}
              </Button>
            )
          },
          {
            id: 'reviewStatus',
            header: 'Status',
            cell: item => getStatusBadge(item.reviewStatus)
          },
          {
            id: 'lastUpdated',
            header: 'Last Updated',
            cell: item => {
              const date = item.updatedAt || item.timestamp;
              if (!date) return 'Unknown';
              try {
                return new Date(date).toLocaleDateString();
              } catch {
                return 'Invalid Date';
              }
            }
          }
        ]}
        items={reviews}
        loading={loading}
        empty={
          <Box textAlign="center" color="inherit">
            <b>No reviews assigned to you</b>
          </Box>
        }
      />
    </Container>
  );
};

export default MyReviewsPage;
