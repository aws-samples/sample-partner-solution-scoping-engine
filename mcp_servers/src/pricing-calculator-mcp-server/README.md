# AWS Pricing Calculator MCP Server

An MCP server that analyzes documents and generates AWS Pricing Calculator instructions with Nova Act automation.

## Features

- Analyzes documents (RFPs, architecture descriptions, etc.) to identify AWS services
- Generates Nova Act instructions for automatic AWS Pricing Calculator population
- Integrates with AWS Bedrock for intelligent service detection

## Tools

- `generate_pricing_calculator_from_document`: Analyze document content and generate pricing calculator instructions

## Usage

This MCP server is designed to be used within the SERA chatbot application to help generate pricing estimates from customer requirements and architecture documents.
