# Crypto Trading Automation System

Automated trading and customer service system for cryptocurrency exchanges.

## What It Does

- 🤖 **Automates cryptocurrency trading** across multiple exchanges (Binance, Bitso, Polymarket).
- 💬 **Handles customer service** with smart verification and multi-language support (English and Spanish).
- 🔍 **Detects fraud** and manages risk automatically.
- 📊 **Processes real-time market data** for informed trading decisions.

## Tech Stack

- **Python**
- **AsyncIO**
- **WebSockets**
- **SQLite**
- **REST APIs**

## Key Features

- **Multi-Exchange Integration**: Connects to Binance, Bitso, and Polymarket for comprehensive trading coverage.
- **Real-Time Data Processing**: Handles live market data for timely and accurate trades.
- **Automated Customer Verification**: Implements a smart system for verifying customer information and reducing fraud.
- **Risk Management**: Includes a built-in risk management system to protect against fraudulent activities.
- **Multi-Language Support**: Communicates with customers in both English and Spanish for a better user experience.

## Setup

1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/your-username/crypto-trading-system.git](https://github.com/your-username/crypto-trading-system.git)
    ```
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure API keys**:
    - Add your exchange API keys to a `.env` file.
4.  **Run the main application**:
    ```bash
    python main.py
    ```