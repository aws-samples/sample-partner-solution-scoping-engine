import React from 'react';
import { Container, Header, Button, Box, SpaceBetween } from '@cloudscape-design/components';

const LoggedOutPage = () => {
    const handleLoginClick = () => {
        window.location.href = '/api/auth?provider=oauth2';
    };

    return (
        <Container>
            <Box textAlign="center" padding="xxl">
                <SpaceBetween direction="vertical" size="l">
                    <Header variant="h1">
                        You have been logged out
                    </Header>
                    
                    <Box variant="p" color="text-body-secondary">
                        You have been successfully logged out of SERA.
                    </Box>
                    
                    <Button 
                        variant="primary" 
                        onClick={handleLoginClick}
                        size="large"
                    >
                        Sign In Again
                    </Button>
                </SpaceBetween>
            </Box>
        </Container>
    );
};

export default LoggedOutPage;
