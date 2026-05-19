// File: frontend/src/App.jsx
import { useState, useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import AppLayout from "@cloudscape-design/components/app-layout";
import Box from "@cloudscape-design/components/box";
import SideNavigation from "@cloudscape-design/components/side-navigation";
import Button from "@cloudscape-design/components/button";
import Modal from "@cloudscape-design/components/modal";
import FormField from "@cloudscape-design/components/form-field";
import Input from "@cloudscape-design/components/input";
import Header from "@cloudscape-design/components/header";
import Alert from "@cloudscape-design/components/alert";
import Spinner from "@cloudscape-design/components/spinner";
import { getCsrfToken } from './utils/csrf';

import SpaceBetween from "@cloudscape-design/components/space-between";
import "@cloudscape-design/global-styles/index.css";
// Import custom styles
import "./custom.css";

// Import Page Components
import HomePage from './pages/HomePage';
import ChatPage from './pages/ChatPage';
import AllChatsPage from './pages/AllChatsPage';
import SolutionsArchitectReviewPage from './pages/SolutionsArchitectReviewPage';
import MyReviewsPage from './pages/MyReviewsPage';
import SOWReviewPage from './pages/SOWReviewPage';
import SettingsPage from './pages/SettingsPage';
import { getRecentChats, getRecentSAReviews, updateChatName, getAllChats } from './services/chatService';
import HelpPage from './pages/HelpPage';
import LoggedOutPage from './pages/LoggedOutPage';
import { useAuth } from './hooks/useAuth';
import ProtectedRoute from './components/ProtectedRoute';
const LoginPage = () => <Box padding="l"><h2>Login Page Placeholder</h2></Box>; // Or handle via redirect
const NotFoundPage = () => <Box padding="l"><h2>404 - Page Not Found</h2></Box>;
const HealthPage = () => ({ status: "ok", service: "sera-frontend", timestamp: new Date().toISOString() });

function App() {
  // Basic state for side navigation (can be expanded)
  const [navigationOpen, setNavigationOpen] = useState(true);
  const [recentChats, setRecentChats] = useState([]);
  const [recentReviews, setRecentReviews] = useState([]);
  const [pendingReviewCount, setPendingReviewCount] = useState(0);
  const [inProgressReviewCount, setInProgressReviewCount] = useState(0);
  const [isLoadingChats, setIsLoadingChats] = useState(true);
  const [chatsError, setChatsError] = useState(null);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingChat, setEditingChat] = useState(null);
  const [newChatName, setNewChatName] = useState('');
  const [nameError, setNameError] = useState('');
  const [updateError, setUpdateError] = useState('');
  const [userRole, setUserRole] = useState(null);

  // Authentication state management - must be after all useState hooks
  const { isAuthenticated, user, loading } = useAuth();

  // Initialize CSRF token on app load
  useEffect(() => {
    getCsrfToken().catch(error => {
      console.error('Failed to initialize CSRF token:', error);
    });
  }, []);

  // Check if user is SA
  useEffect(() => {
    const checkSARole = async () => {
      try {
        const response = await fetch('/api/user/is-sa', {
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          setUserRole(data.is_sa ? 'sa' : 'sales');
        } else {
          setUserRole('sales');
        }
      } catch (error) {
        setUserRole('sales');
      }
    };
    
    checkSARole();
  }, []); 

  // Fetch recent chats when the app loads
  useEffect(() => {
    const fetchRecentChats = async () => {
      try {
        console.debug('Fetching recent chats');
        setIsLoadingChats(true);
        setChatsError(null);
        const chats = await getRecentChats();
        const reviews = await getRecentSAReviews();
        console.debug('Received chats:', chats);
        console.debug('Received reviews:', reviews);
        setRecentChats(chats);
        setRecentReviews(reviews);
        
        // Count in-progress reviews
        const inProgressCount = reviews.filter(review => 
          review.reviewStatus === 'in_progress'
        ).length;
        setInProgressReviewCount(inProgressCount);
        
        // Get pending review count from SOLUTION_REVIEW API
        try {
          const pendingReviews = await getAllChats('SOLUTION_REVIEW', 1, 0);
          setPendingReviewCount(pendingReviews.total || 0);
        } catch (error) {
          console.error('Error fetching pending review count:', error);
          setPendingReviewCount(0);
        }
      } catch (error) {
        console.error('Error fetching chats:', error);
        setChatsError('Failed to load recent chats');
      } finally {
        setIsLoadingChats(false);
      }
    };

    fetchRecentChats();
  }, []);

  // Helper function to get user-friendly review status names
  const getReviewDisplayName = (status) => {
    switch (status) {
      case 'none': return 'None';
      case 'requested': return 'requested';
      case 'in_progress': return 'in progress';
      case 'ready_for_merge': return 'ready for merge';
      case 'complete_no_changes': return 'OK as is';
      case 'ready_for_user': return 'approved';
      case 'reassigned': return 'reassigned';
      case 'rejected': return 'rejected';
      case 'merged': return 'merged';
      case 'dismissed': return 'dismissed';
      default: return status || 'Unknown';
    }
  };

  // Function to refresh recent chats - expose globally
  const refreshRecentChats = async () => {
    try {
      console.debug('Refreshing recent chats');
      const chats = await getRecentChats();
      const reviews = await getRecentSAReviews();
      setRecentChats(chats);
      setRecentReviews(reviews);
      
      // Count in-progress reviews
      const inProgressCount = reviews.filter(review => 
        review.reviewStatus === 'in_progress'
      ).length;
      setInProgressReviewCount(inProgressCount);
      
      // Get pending review count from SOLUTION_REVIEW API
      try {
        const pendingReviews = await getAllChats('SOLUTION_REVIEW', 1, 0);
        setPendingReviewCount(pendingReviews.total || 0);
      } catch (error) {
        console.error('Error fetching pending review count:', error);
        setPendingReviewCount(0);
      }
    } catch (error) {
      console.error('Error refreshing recent chats:', error);
    }
  };

  // Expose refresh function globally
  useEffect(() => {
    window.refreshRecentChats = refreshRecentChats;
    return () => {
      delete window.refreshRecentChats;
    };
  }, []);

  const handleEditClick = (e, chat) => {
    e.stopPropagation();
    e.preventDefault();
    setEditingChat(chat);
    setNewChatName(chat.chatName || '');
    setNameError('');
    setUpdateError('');
    setEditModalVisible(true);
  };

  const validateChatName = (name) => {
    if (!name.trim()) {
      setNameError('Chat name cannot be empty');
      return false;
    }
    if (name.length > 50) {
      setNameError('Chat name cannot exceed 50 characters');
      return false;
    }
    // Only allow letters, numbers, and hyphens with no spaces
    const nameRegex = /^[a-zA-Z0-9-]+$/;
    if (!nameRegex.test(name)) {
      setNameError('Chat name can only contain letters, numbers, and hyphens (no spaces)');
      return false;
    }
    setNameError('');
    return true;
  };

  const handleSave = async () => {
    if (!validateChatName(newChatName)) {
      return;
    }

    try {
      const updatedChat = await updateChatName(editingChat.chatId, newChatName);
      
      // Update the chat in the local state
      setRecentChats(recentChats.map(chat => 
        chat.chatId === editingChat.chatId 
          ? { ...chat, chatName: updatedChat.chatName } 
          : chat
      ));
      
      setEditModalVisible(false);
    } catch (err) {
      console.error('Error updating chat name:', err);
      setUpdateError('Sorry! Something went wrong');
    }
  };

  // Generate recent chat items for the sidebar
  const generateRecentChatItems = () => {
    // If still loading, show a loading item with spinner
    if (isLoadingChats) {
      return [
        {
          type: "link",
          text: (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Spinner size="small" />
              <span>Loading recent chats...</span>
            </div>
          ),
          disabled: true
        }
      ];
    }
    
    // If there was an error, show error message
    if (chatsError) {
      return [
        {
          type: "link",
          text: chatsError,
          disabled: true
        }
      ];
    }
    
    // If no chats, show a message
    if (!recentChats || recentChats.length === 0) {
      return [
        {
          type: "link",
          text: "No recent chats",
          disabled: true
        }
      ];
    }
    
    // Otherwise, return links to each chat
    return recentChats.map(chat => ({
      type: "link",
      text: chat.chatName || `Chat ${chat.chatId.substring(0, 8)}...`,
      href: `/chat/${chat.chatId}`,
    }));
  };

  const generateRecentReviewItems = () => {
    // If loading, show loading message
    if (isLoadingChats) {
      return [
        {
          type: "link",
          text: "Loading...",
          disabled: true
        }
      ];
    }
    
    // If there was an error, show error message
    if (chatsError) {
      return [
        {
          type: "link",
          text: chatsError,
          disabled: true
        }
      ];
    }
    
    // If no reviews, show a message
    if (!recentReviews || recentReviews.length === 0) {
      return [
        {
          type: "link",
          text: "No recent reviews",
          disabled: true
        }
      ];
    }
    
    // Otherwise, return links to each review
    return recentReviews.map(review => ({
      type: "link",
      text: (
        <div style={{ 
          display: 'flex', 
          width: '100%', 
          justifyContent: 'space-between',
          alignItems: 'center',
          minWidth: 0
        }}>
          <span style={{
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            flexGrow: 1,
            minWidth: 0
          }}>
            {review.chatName || `Review ${review.chatId.substring(0, 8)}...`}
          </span>
          <span style={{
            fontSize: '0.8em',
            color: review.reviewStatus === 'rejected' ? 'red' :
                   review.reviewStatus === 'dismissed' ? 'gray' :
                   review.reviewStatus === 'reassigned' ? 'gray' :
                   review.reviewStatus === 'cancelled' ? 'gray' :
                   review.reviewStatus === 'complete_no_changes' ? 'green' :
                   review.reviewStatus === 'ready_for_user' ? 'green' :
                   review.reviewStatus === 'merged' ? 'green' :
                   review.reviewStatus === 'in_progress' ? 'orange' : 'blue',
            marginLeft: '4px'
          }}>
            {getReviewDisplayName(review.reviewStatus)}
          </span>
        </div>
      ),
      href: `/chat/${review.chatId}`,
    }));
  };

  // Add loading state for authentication check
  if (loading) {
    return (
      <Box textAlign="center" padding="xxl">
        <Spinner size="large" />
        <Box variant="p" color="text-status-info" margin={{ top: 's' }}>
          Loading application...
        </Box>
      </Box>
    );
  }

  return (
    <>
      <AppLayout
        navigation={
          isAuthenticated ? (
            <SideNavigation
              activeHref={window.location.pathname}
              header={{ href: "/", text: "SERA" }}
              items={[
                { type: "link", text: "New Chat / Home", href: "/" },
                { 
                  type: "section", 
                  text: "Recent Chats", 
                  items: generateRecentChatItems()
                },
                ...(userRole === 'sa' ? [{
                  type: "section", 
                  text: "Recent Reviews", 
                  items: generateRecentReviewItems()
                }] : []),
                { 
                  type: "section", 
                  text: "All Chats",
                  items: [
                    { type: "link", text: "View All Chats", href: "/chats" }
                  ]
                },
                { type: "divider" },
                ...(userRole === 'sa' ? [{
                  type: "section", 
                  text: "Human Solutions Review",
                  items: [
                    { 
                      type: "link", 
                      text: (
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                          <span>Review Queue</span>
                          {pendingReviewCount > 0 && (
                            <span style={{
                              backgroundColor: '#d13212',
                              color: 'white',
                              borderRadius: '50%',
                              minWidth: '20px',
                              height: '20px',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '12px',
                              fontWeight: 'bold'
                            }}>
                              {pendingReviewCount}
                            </span>
                          )}
                        </div>
                      ),
                      href: "/sa-review" 
                    },
                    { 
                      type: "link", 
                      text: (
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                          <span>My Reviews</span>
                          {inProgressReviewCount > 0 && (
                            <span style={{
                              backgroundColor: '#d13212',
                              color: 'white',
                              borderRadius: '50%',
                              minWidth: '20px',
                              height: '20px',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '12px',
                              fontWeight: 'bold'
                            }}>
                              {inProgressReviewCount}
                            </span>
                          )}
                        </div>
                      ),
                      href: "/my-reviews" 
                    }
                    // { type: "link", text: "SOW Review", href: "/sow-review" } // Disabled - not production ready
                  ]
                }, { type: "divider" }] : []),
                { 
                  type: "section", 
                  text: "Help",
                  items: [
                    { type: "link", text: "View Help", href: "/help" },
                    {
                      type: "link",
                      text: "Provide Feedback For SERA",
                      href: "",  // Set to your feedback form URL
                      external: true
                    }
                  ]
                },
                { type: "divider" },
                { 
                  type: "section", 
                  text: "Settings",
                  items: [
                    { type: "link", text: "Support Settings", href: "/settings" }
                  ]
                },
                { type: "divider" },
                { 
                  type: "section", 
                  text: "Logout",
                  items: [
                    { 
                      type: "link", 
                      text: "Sign Out", 
                      href: "/api/logout",
                      onClick: () => console.debug("Logout clicked")
                    }
                  ]
                }
              ]}
            />
          ) : null
        }
        navigationWidth={350}
        minNavigationWidth={300}
        content={
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/chats" element={
              <ProtectedRoute>
                <AllChatsPage />
              </ProtectedRoute>
            } />
            <Route path="/chat/:chatId" element={
              <ProtectedRoute>
                <ChatPage />
              </ProtectedRoute>
            } />
            <Route path="/sa-review" element={
              <ProtectedRoute>
                <SolutionsArchitectReviewPage />
              </ProtectedRoute>
            } />
            <Route path="/my-reviews" element={
              <ProtectedRoute>
                <MyReviewsPage />
              </ProtectedRoute>
            } />
            <Route path="/sow-review" element={
              <ProtectedRoute>
                <SOWReviewPage />
              </ProtectedRoute>
            } />
            <Route path="/settings" element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            } />
            <Route path="/help" element={<HelpPage />} />
            <Route path="/logged-out" element={<LoggedOutPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/health" element={<HealthPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        }
        toolsHide={true}
        navigationOpen={navigationOpen}
        onNavigationChange={({ detail }) => setNavigationOpen(detail.open)}
        ariaLabels={{
          navigation: "Side navigation",
          navigationToggle: "Open side navigation",
          navigationClose: "Close side navigation",
          content: "Main content",
        }}
      />

      {/* Edit Modal */}
      <Modal
        visible={editModalVisible}
        onDismiss={() => setEditModalVisible(false)}
        header="Edit Chat Name"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <div key="cancel-button">
                <Button variant="link" onClick={() => setEditModalVisible(false)}>
                  Cancel
                </Button>
              </div>
              <div key="save-button">
                <Button variant="primary" onClick={handleSave}>
                  Save
                </Button>
              </div>
            </SpaceBetween>
          </Box>
        }
      >
        <FormField
          label="Chat Name"
          errorText={nameError}
          description="Use letters, numbers, and hyphens only (no spaces)"
        >
          <Input
            value={newChatName}
            onChange={({ detail }) => setNewChatName(detail.value)}
            autoFocus
            maxLength={50}
          />
        </FormField>
        
        {updateError && (
          <Alert type="error" header="Error">
            {updateError}
          </Alert>
        )}
      </Modal>
    </>
  );
}

export default App;
