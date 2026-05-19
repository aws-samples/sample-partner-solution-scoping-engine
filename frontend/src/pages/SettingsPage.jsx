import React, { useState, useEffect } from 'react';
import apiClient from '../services/apiClient';
import {
  Container,
  Header,
  SpaceBetween,
  Table,
  Button,
  Input,
  Select,
  Alert,
  Box
} from '@cloudscape-design/components';

const SettingsPage = () => {
  const [supportTeam, setSupportTeam] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [newMemberId, setNewMemberId] = useState('');
  const [newMemberRole, setNewMemberRole] = useState({ value: 'solution_architect', label: 'Solution Architect' });

  const roleOptions = [
    { value: 'solution_architect', label: 'Solution Architect' },
    { value: 'sales_manager', label: 'Sales Manager' },
    { value: 'overlay', label: 'Overlay' }
  ];

  useEffect(() => {
    loadSupportTeam();
  }, []);

  const loadSupportTeam = async () => {
    try {
      const response = await fetch('/api/support/team', {
        credentials: 'include'
      });
      const result = await response.json();
      
      console.log('Support team data:', result); // Debug log
      
      if (result.success) {
        setSupportTeam(result.support_team || []);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError('Failed to load support team');
    }
  };

  const addSupportMember = async () => {
    console.log('addSupportMember called');
    if (!newMemberId.trim()) {
      console.log('No member ID entered');
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      console.log('Making API call...');
      const result = await apiClient.post('/support/add', {
        support_member_id: newMemberId.trim(),
        support_member_role: newMemberRole.value
      });
      
      console.log('API result:', result);
      
      if (result.success) {
        setNewMemberId('');
        loadSupportTeam();
      } else {
        setError(result.error);
      }
    } catch (err) {
      console.error('Error:', err);
      setError('Failed to add support member');
    } finally {
      setLoading(false);
    }
  };

  const removeSupportMember = async (supportMemberId) => {
    setLoading(true);
    setError('');
    
    try {
      const result = await apiClient.post('/support/remove', {
        support_member_id: supportMemberId
      });
      
      if (result.success) {
        loadSupportTeam();
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError('Failed to remove support member');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container>
      <SpaceBetween direction="vertical" size="l">
        <React.Fragment key="header">
          <Header variant="h1">Settings</Header>
        </React.Fragment>
        
        {error && (
          <React.Fragment key="error">
            <Alert type="error">{error}</Alert>
          </React.Fragment>
        )}
        
        <React.Fragment key="support-container">
          <Container>
            <Header key="support-header" variant="h2">Support Team</Header>
            <SpaceBetween key="support-content" direction="vertical" size="m">
              <React.Fragment key="add-form">
                <div>
                  <SpaceBetween direction="horizontal" size="s">
                    <Input
                      key="member-input"
                      value={newMemberId}
                      onChange={({ detail }) => setNewMemberId(detail.value)}
                      placeholder="Enter email (e.g., user@example.com)"
                    />
                    <Select
                      key="role-select"
                      selectedOption={newMemberRole}
                      onChange={({ detail }) => setNewMemberRole(detail.selectedOption)}
                      options={roleOptions}
                    />
                    <Button
                      key="add-button"
                      variant="primary"
                      loading={loading}
                      onClick={addSupportMember}
                    >
                      Add Member
                    </Button>
                  </SpaceBetween>
                </div>
              </React.Fragment>

              <React.Fragment key="table">
                <div>
                  <Table
                    columnDefinitions={[
                      {
                        id: 'support_member_id',
                        header: 'Email',
                        cell: item => item.support_member_id
                      },
                      {
                        id: 'support_member_role',
                        header: 'Role',
                        cell: item => item.support_member_role?.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
                      },
                      {
                        id: 'actions',
                        header: 'Actions',
                        cell: item => (
                          <Button
                            variant="link"
                            loading={loading}
                            onClick={() => removeSupportMember(item.support_member_id)}
                          >
                            Remove
                          </Button>
                        )
                      }
                    ]}
                    items={supportTeam}
                    empty={
                      <Box textAlign="center" color="inherit">
                        <b>No support members</b>
                        <Box padding={{ bottom: 's' }} variant="p" color="inherit">
                          Add team members who can review and improve your chats.
                        </Box>
                      </Box>
                    }
                  />
                </div>
              </React.Fragment>
            </SpaceBetween>
          </Container>
        </React.Fragment>
      </SpaceBetween>
    </Container>
  );
};

export default SettingsPage;
