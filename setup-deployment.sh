#!/bin/bash

# Setup script for Firebase and Google Cloud deployment

echo ""
echo "============================================"
echo "Drag Drop Quiz - Deployment Setup Script"
echo "============================================"
echo ""

# Check if Node.js is installed
echo "Checking for Node.js..."
if ! command -v node &> /dev/null; then
    echo ""
    echo "ERROR: Node.js is not installed!"
    echo "Please download and install from: https://nodejs.org/"
    echo "After installation, run this script again."
    exit 1
else
    echo "✓ Node.js is installed: $(node --version)"
fi

# Check if Google Cloud SDK is installed
echo "Checking for Google Cloud SDK..."
if ! command -v gcloud &> /dev/null; then
    echo ""
    echo "ERROR: Google Cloud SDK is not installed!"
    echo "Please download from: https://cloud.google.com/sdk/docs/install"
    echo "After installation, run this script again."
    exit 1
else
    echo "✓ Google Cloud SDK is installed"
fi

# Install Firebase CLI
echo ""
echo "Installing Firebase CLI..."
npm install -g firebase-tools

# Authenticate with Firebase
echo ""
echo "Authenticating with Firebase..."
firebase login

# Authenticate with Google Cloud
echo ""
echo "Authenticating with Google Cloud..."
gcloud auth login

# Initialize Firebase
echo ""
echo "Initializing Firebase in your project..."
firebase init hosting

echo ""
echo "============================================"
echo "Setup Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Read DEPLOYMENT_GUIDE.md for detailed instructions"
echo "2. Update your backend URL in static/config.js"
echo "3. Deploy: firebase deploy --only hosting"
echo ""
